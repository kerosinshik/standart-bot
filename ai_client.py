"""
Универсальный клиент для работы с разными AI моделями (Z.ai, Claude)
"""
import requests
import os
from typing import List, Dict, Optional
from dotenv import load_dotenv
from anthropic import Anthropic

load_dotenv()


class AIClient:
    """Универсальный клиент для работы с AI"""

    def __init__(self, provider: str = "zai"):
        """
        Инициализация AI клиента

        Args:
            provider: "zai" или "claude"
        """
        self.provider = provider

        if provider == "zai":
            self.api_key = os.getenv('ZAI_API_KEY')
            self.api_url = os.getenv('ZAI_API_URL', 'https://api.z.ai/api/paas/v4/chat/completions')
            if not self.api_key:
                raise ValueError("ZAI_API_KEY не найден в .env")
            self.headers = {
                'Authorization': f'Bearer {self.api_key}',
                'Content-Type': 'application/json'
            }
        elif provider == "claude":
            self.api_key = os.getenv('ANTHROPIC_API_KEY')
            if not self.api_key:
                raise ValueError("ANTHROPIC_API_KEY не найден в .env")

            # Прокси для обхода блокировки IP (используем CLAUDE_PROXY вместо HTTPS_PROXY)
            proxy_url = os.getenv('CLAUDE_PROXY')
            if proxy_url:
                import httpx
                http_client = httpx.Client(proxy=proxy_url)
                self.client = Anthropic(api_key=self.api_key, http_client=http_client)
                print(f"✓ Клиент Claude инициализирован с прокси: {proxy_url}")
            else:
                self.client = Anthropic(api_key=self.api_key)
                print("✓ Клиент Claude инициализирован")
        else:
            raise ValueError(f"Неизвестный провайдер: {provider}")

    def create_system_prompt(self, all_documents: Optional[List[str]] = None, use_general_knowledge: bool = False) -> str:
        """Создает системный промпт для AI"""
        docs_info = ""
        if all_documents:
            docs_list = "\n".join([f"- {doc}" for doc in all_documents])
            docs_info = f"\n\nДОКУМЕНТЫ В БАЗЕ:\n{docs_list}\n"

        if use_general_knowledge:
            # Расширенный режим: может использовать общие знания
            return f"""Ты помощник по нормативным документам. Отвечай кратко и точно.{docs_info}
ПРАВИЛА:
1. Используй информацию из предоставленного контекста
2. Можешь дополнить ответ своими общими знаниями, если они релевантны
3. ОБЯЗАТЕЛЬНО указывай источник информации: из документов или общие знания
4. Если есть определение термина - начни с него
5. Отвечай коротко, по существу
6. Используй Markdown (списки, жирный текст)

ФОРМАТ:
**Краткий ответ**

Детали:
- Пункт 1
- Пункт 2

**Источники:** [Документ, стр. X] или [Общие знания AI]"""
        else:
            # Строгий режим: только документы
            return f"""Ты помощник по нормативным документам. Отвечай кратко и точно.{docs_info}
ПРАВИЛА:
1. Отвечай ТОЛЬКО на основе предоставленного контекста из документов
2. Если в контексте нет ответа, но вопрос относится к другому документу из базы - скажи об этом
3. Если есть определение термина - начни с него
4. Отвечай коротко, по существу
5. Используй Markdown (списки, жирный текст)
6. В конце укажи источники

ФОРМАТ:
**Краткий ответ**

Детали:
- Пункт 1
- Пункт 2

**Источники:** [Документ, стр. X]"""

    def create_user_prompt(self, question: str, context: str) -> str:
        """Создает промпт пользователя с вопросом и контекстом"""
        return f"""КОНТЕКСТ ИЗ ДОКУМЕНТОВ:
{context}

ВОПРОС ПОЛЬЗОВАТЕЛЯ:
{question}

Ответь на вопрос, используя информацию из контекста выше. Обязательно укажи источники."""

    def chat_zai(self, question: str, context: str, all_documents: Optional[List[str]] = None, use_general_knowledge: bool = False) -> Dict:
        """Отправляет запрос в Z.ai API"""
        messages = [
            {"role": "system", "content": self.create_system_prompt(all_documents, use_general_knowledge)},
            {"role": "user", "content": self.create_user_prompt(question, context)}
        ]

        payload = {
            "model": "glm-4.6",
            "messages": messages,
            "temperature": 0.3,
            "max_tokens": 2500
        }

        max_retries = 2
        for attempt in range(max_retries):
            try:
                # Явно отключаем прокси для Z.ai (прокси нужен только для Claude)
                session = requests.Session()
                session.trust_env = False  # Игнорировать переменные окружения HTTPS_PROXY
                response = session.post(
                    self.api_url,
                    headers=self.headers,
                    json=payload,
                    timeout=60
                )
                response.raise_for_status()
                return response.json()
            except requests.exceptions.Timeout:
                if attempt < max_retries - 1:
                    print(f"Timeout, повторная попытка {attempt + 2}/{max_retries}...")
                    continue
                else:
                    return {
                        "error": "Timeout",
                        "message": "AI не ответил вовремя. Попробуйте упростить вопрос."
                    }
            except requests.exceptions.RequestException as e:
                print(f"Ошибка при запросе к Z.ai API: {e}")
                return {
                    "error": str(e),
                    "message": "Не удалось получить ответ от AI."
                }

    def chat_claude(self, question: str, context: str, all_documents: Optional[List[str]] = None, use_general_knowledge: bool = False) -> Dict:
        """Отправляет запрос в Claude API"""
        try:
            message = self.client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=2500,
                temperature=0.3,
                system=self.create_system_prompt(all_documents, use_general_knowledge),
                messages=[
                    {"role": "user", "content": self.create_user_prompt(question, context)}
                ]
            )

            # Форматируем ответ в стиле Z.ai для совместимости
            return {
                "choices": [{
                    "message": {
                        "content": message.content[0].text
                    }
                }],
                "usage": {
                    "prompt_tokens": message.usage.input_tokens,
                    "completion_tokens": message.usage.output_tokens,
                    "total_tokens": message.usage.input_tokens + message.usage.output_tokens
                }
            }
        except Exception as e:
            print(f"Ошибка при запросе к Claude API: {e}")
            return {
                "error": str(e),
                "message": "Не удалось получить ответ от Claude."
            }

    def chat(self, question: str, context: str, all_documents: Optional[List[str]] = None, use_general_knowledge: bool = False) -> Dict:
        """Отправляет запрос в выбранный AI"""
        if self.provider == "zai":
            return self.chat_zai(question, context, all_documents, use_general_knowledge)
        elif self.provider == "claude":
            return self.chat_claude(question, context, all_documents, use_general_knowledge)
        else:
            return {"error": "Unknown provider", "message": "Неизвестный провайдер AI"}

    def get_answer(self, question: str, context: str, sources: List[str], all_documents: Optional[List[str]] = None, use_general_knowledge: bool = False) -> Dict:
        """
        Получает ответ от AI и форматирует его

        Args:
            question: вопрос пользователя
            context: контекст из документов
            sources: список источников

        Returns:
            Dict: отформатированный ответ
        """
        if not context:
            return {
                "answer": "К сожалению, я не нашел релевантной информации в загруженных документах по вашему вопросу.",
                "sources": [],
                "success": False
            }

        # Получаем ответ от AI
        ai_response = self.chat(question, context, all_documents, use_general_knowledge)

        # Обрабатываем ответ
        if "error" in ai_response:
            return {
                "answer": ai_response.get("message", "Произошла ошибка при обработке запроса"),
                "sources": [],
                "success": False,
                "error": ai_response["error"]
            }

        try:
            answer_text = ai_response['choices'][0]['message']['content']

            # Извлекаем информацию о токенах
            usage = ai_response.get('usage', {})
            tokens_info = {
                'prompt_tokens': usage.get('prompt_tokens', 0),
                'completion_tokens': usage.get('completion_tokens', 0),
                'total_tokens': usage.get('total_tokens', 0)
            }

            return {
                "answer": answer_text,
                "sources": sources,
                "success": True,
                "tokens": tokens_info
            }

        except (KeyError, IndexError) as e:
            print(f"Ошибка при разборе ответа AI: {e}")
            return {
                "answer": "Не удалось обработать ответ от AI",
                "sources": [],
                "success": False,
                "error": str(e)
            }
