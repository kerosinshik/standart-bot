# RAG Chat-бот по нормативным документам

AI-powered чат-бот для поиска и ответов по PDF документам. Использует **RAG (Retrieval-Augmented Generation)** для точных ответов с ссылками на источники. MVP проекта, выполненного на заказ. Позволяет работать с локальными PDF, поддерживает несколько AI моделей, хранит контекст диалога и предоставляет простой веб-интерфейс.

**Возможности:**
- Семантический поиск по PDF
- AI модели: **Z.ai (GLM-4.6)** и **Claude 3.5**
- Локальная база ChromaDB
- Контекст последних 3 пар вопрос-ответ
- Режимы знаний: строгий (только документы) / расширенный (с AI общими знаниями)

**Быстрый старт:**
```bash
git clone <your-repo-url> standart_bot
cd standart_bot
python3.12 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # add your Z.ai / Claude API keys
mkdir -p documents
python init_db.py
python main.py
```

Открыть веб-интерфейс: http://localhost:8000

Структура проекта:
```bash
main.py          — FastAPI сервер
vector_db.py     — семантический поиск и ChromaDB
pdf_processor.py — обработка PDF в чанки
ai_client.py     — клиент для AI API
init_db.py       — инициализация базы
documents/       — PDF файлы
static/          — веб-интерфейс
```

Лицензия: MIT License

Проект архивный, MVP для работы с нормативными документами. Цель публикации — демонстрация работы RAG и семантического поиска.

---

# RAG Chatbot for PDF documents

AI-powered chatbot for searching and answering questions from PDF documents. MVP project developed on request.
Supports semantic search with RAG, multiple AI models, local ChromaDB storage, and a simple web interface.

**Quick start:**
```bash
git clone <your-repo-url> standart_bot
cd standart_bot
python3.12 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # add your Z.ai / Claude API keys
mkdir -p documents
python init_db.py
python main.py
```
Open web interface: http://localhost:8000



