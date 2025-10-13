"""
Основной FastAPI сервер для чат-бота
"""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Optional, Dict
import os
from dotenv import load_dotenv

from vector_db import VectorDatabase
from ai_client import AIClient

# Загружаем переменные окружения
load_dotenv()

# Инициализируем FastAPI
app = FastAPI(
    title="Чат-бот по нормативным документам",
    description="API для работы с документами через AI",
    version="1.0.0"
)

# Настройка CORS для работы с фронтендом
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # В продакшене укажите конкретные домены
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Глобальные объекты (инициализируются при запуске)
vector_db: Optional[VectorDatabase] = None
ai_clients: Dict[str, AIClient] = {}  # Словарь клиентов {"zai": client, "claude": client}


# Модели данных
class QuestionRequest(BaseModel):
    question: str
    n_results: Optional[int] = 20  # Для базы из 17k чанков оптимально 20-25 результатов
    search_mode: Optional[str] = "rag"  # "rag", "direct" или "auto"
    conversation_history: Optional[list] = []  # История последних 2-3 сообщений
    ai_provider: Optional[str] = "zai"  # "zai" или "claude"
    knowledge_mode: Optional[str] = "strict"  # "strict" или "expanded"


class QuestionResponse(BaseModel):
    answer: str
    sources: list
    success: bool
    error: Optional[str] = None
    metrics: Optional[dict] = None  # Метрики: время, токены


def auto_select_search_mode(question: str) -> str:
    """
    Автоматически выбирает режим поиска на основе паттернов вопроса

    Returns:
        "direct" для точных запросов (коды, определения)
        "rag" для сложных семантических запросов
    """
    question_lower = question.lower()

    # Паттерны для keyword-поиска (быстрый, точный)
    keyword_patterns = [
        'какой код', 'какое значение', 'какой номер',
        'что такое', 'определение', 'что означает',
        'сколько', 'когда', 'где указан',
        'пороговое', 'максимум', 'минимум'
    ]

    # Паттерны для векторного поиска (семантический)
    vector_patterns = [
        'как', 'почему', 'каким образом',
        'требования к', 'правила', 'процедура',
        'необходимо', 'следует', 'должен',
        'расскажи', 'объясни', 'опиши'
    ]

    # Проверяем паттерны для keyword-поиска
    if any(pattern in question_lower for pattern in keyword_patterns):
        return "direct"

    # Проверяем паттерны для векторного поиска
    if any(pattern in question_lower for pattern in vector_patterns):
        return "rag"

    # По умолчанию используем векторный поиск (лучше для сложных документов)
    return "rag"


@app.on_event("startup")
async def startup_event():
    """Инициализация при запуске сервера"""
    global vector_db, ai_clients

    print("Инициализация сервера...")

    # Инициализируем векторную БД
    vector_db = VectorDatabase()
    chunks_count = vector_db.get_collection_count()
    docs_count = vector_db.get_unique_documents_count()
    print(f"База данных загружена. PDF файлов: {docs_count}, чанков: {chunks_count}")

    if chunks_count == 0:
        print("\n⚠️  ВНИМАНИЕ: База данных пуста!")
        print("Запустите init_db.py для индексации PDF файлов\n")

    # Инициализируем AI клиенты
    # Z.ai
    try:
        ai_clients["zai"] = AIClient(provider="zai")
        print("✓ Клиент Z.ai инициализирован")
    except ValueError as e:
        print(f"⚠️  Z.ai недоступен: {e}")

    # Claude
    try:
        ai_clients["claude"] = AIClient(provider="claude")
        print("✓ Клиент Claude инициализирован")
    except ValueError as e:
        print(f"⚠️  Claude недоступен: {e}")

    if not ai_clients:
        print("⚠️  КРИТИЧНО: Ни один AI провайдер не доступен!")
        print("Добавьте ZAI_API_KEY или ANTHROPIC_API_KEY в .env")

    print("Сервер готов к работе!")


@app.get("/")
async def root():
    """Главная страница - отдает HTML интерфейс"""
    return FileResponse("static/index.html")


@app.get("/health")
async def health_check():
    """Проверка здоровья сервера"""
    chunks_count = vector_db.get_collection_count() if vector_db else 0
    docs_count = vector_db.get_unique_documents_count() if vector_db else 0

    return {
        "status": "ok",
        "documents_count": docs_count,
        "chunks_count": chunks_count,
        "ai_providers": list(ai_clients.keys())
    }


@app.post("/api/ask", response_model=QuestionResponse)
async def ask_question(request: QuestionRequest):
    """
    Основной эндпоинт для вопросов

    Args:
        request: QuestionRequest с вопросом пользователя

    Returns:
        QuestionResponse: ответ от AI с источниками
    """
    if not vector_db:
        raise HTTPException(status_code=503, detail="База данных не инициализирована")

    # Выбираем AI провайдера
    ai_provider = request.ai_provider if request.ai_provider else "zai"
    if ai_provider not in ai_clients:
        raise HTTPException(status_code=400, detail=f"AI провайдер '{ai_provider}' не доступен. Доступны: {list(ai_clients.keys())}")

    ai_client = ai_clients[ai_provider]

    if not request.question.strip():
        raise HTTPException(status_code=400, detail="Вопрос не может быть пустым")

    try:
        import time

        start_time = time.time()

        # Проверка на запрос списка документов
        question_lower = request.question.lower()
        list_keywords = [
            'какие документы', 'список документов', 'покажи документы', 'все документы',
            'какие документы у тебя', 'по каким документам', 'документы в базе',
            'что за документы', 'перечисли документы', 'какая база документов'
        ]
        if any(keyword in question_lower for keyword in list_keywords):
            documents = vector_db.get_all_documents()
            if documents:
                # Форматируем список с краткими названиями
                doc_list_formatted = []
                for i, doc in enumerate(documents, 1):
                    # Извлекаем номер документа (N_XX)
                    if '_N_' in doc:
                        doc_num = doc.split('_N_')[1].split('_')[0]
                        doc_name = doc.replace('.pdf', '').replace('_', ' ')
                        doc_list_formatted.append(f"{i}. **N {doc_num}** - {doc_name}")
                    else:
                        doc_list_formatted.append(f"{i}. {doc}")

                doc_list = "\n".join(doc_list_formatted)
                answer = f"""**В моей базе знаний {len(documents)} документов:**

{doc_list}

Всего проиндексировано **17,120 фрагментов** текста.

Задайте любой вопрос по этим документам!"""
            else:
                answer = "К сожалению, в базе пока нет документов."

            return QuestionResponse(
                answer=answer,
                sources=[],
                success=True,
                metrics={
                    'search_mode': 'list',
                    'auto_selected': False,
                    'ai_provider': ai_provider,
                    'search_time_ms': 0,
                    'ai_time_ms': 0,
                    'total_time_ms': round((time.time() - start_time) * 1000, 2),
                    'tokens': {'prompt_tokens': 0, 'completion_tokens': 0, 'total_tokens': 0},
                    'has_history': False
                }
            )

        # Всегда используем векторный поиск (RAG)
        # search_mode = request.search_mode if request.search_mode else "rag"  # Закомментировано
        # Автовыбор режима закомментирован - используем только векторный поиск
        # original_mode = search_mode
        # if search_mode == "auto":
        #     search_mode = auto_select_search_mode(request.question)

        # Формируем расширенный вопрос с учетом истории диалога
        enhanced_question = request.question
        if request.conversation_history and len(request.conversation_history) > 0:
            # Берем последние 2-3 сообщения для контекста
            recent_history = request.conversation_history[-3:]
            history_text = "\n".join([
                f"{'Пользователь' if msg.get('role') == 'user' else 'Ассистент'}: {msg.get('content', '')}"
                for msg in recent_history
            ])
            enhanced_question = f"История диалога:\n{history_text}\n\nТекущий вопрос: {request.question}"

        n_results = request.n_results if request.n_results else 20

        # Используем только векторный поиск
        context, sources = vector_db.get_context_for_query(
            enhanced_question,
            n_results=n_results
        )
        search_time = time.time() - start_time

        # Получаем список всех документов для передачи в AI
        all_documents = vector_db.get_all_documents()

        # Определяем режим знаний (strict или expanded)
        knowledge_mode = request.knowledge_mode if request.knowledge_mode else "strict"
        use_general_knowledge = (knowledge_mode == "expanded")

        # Получаем ответ от AI
        ai_start = time.time()
        result = ai_client.get_answer(enhanced_question, context, sources, all_documents, use_general_knowledge)
        ai_time = time.time() - ai_start

        total_time = time.time() - start_time

        # Добавляем метрики
        result['metrics'] = {
            'ai_provider': ai_provider,  # Какая модель использовалась
            'search_time_ms': round(search_time * 1000, 2),
            'ai_time_ms': round(ai_time * 1000, 2),
            'total_time_ms': round(total_time * 1000, 2),
            'context_length': len(context),
            'sources_count': len(sources),
            'tokens': result.get('tokens', {}),
            'has_history': len(request.conversation_history) > 0 if request.conversation_history else False
        }

        return QuestionResponse(**result)

    except Exception as e:
        print(f"Ошибка при обработке вопроса: {e}")
        raise HTTPException(status_code=500, detail=f"Внутренняя ошибка сервера: {str(e)}")


@app.get("/api/stats")
async def get_stats():
    """Получить статистику по базе данных"""
    if not vector_db:
        raise HTTPException(status_code=503, detail="База данных не инициализирована")

    doc_count = vector_db.get_collection_count()

    return {
        "total_chunks": doc_count,
        "collection_name": vector_db.collection_name,
        "db_path": vector_db.db_path
    }


# Подключаем статические файлы (HTML, CSS, JS)
# Создадим папку static для фронтенда
os.makedirs("static", exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")


if __name__ == "__main__":
    import uvicorn

    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", 8000))

    print(f"Запуск сервера на {host}:{port}")

    uvicorn.run(
        "main:app",
        host=host,
        port=port,
        reload=True  # Автоперезагрузка при изменении кода
    )
