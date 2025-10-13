# RAG Чат-бот по нормативным документам

AI-powered чат-бот для работы с нормативными документами в PDF формате. Использует RAG (Retrieval-Augmented Generation) для точных ответов со ссылками на источники.

## 📋 Содержание

- [Возможности](#возможности)
- [Архитектура системы](#архитектура-системы)
- [Технологии](#технологии)
- [Логика работы](#логика-работы)
- [Установка и запуск](#установка-и-запуск)
- [Развертывание на VPS](#развертывание-на-vps)
- [API Documentation](#api-documentation)
- [Конфигурация](#конфигурация)
- [Troubleshooting](#troubleshooting)

---

## 🚀 Возможности

- 📄 **Обработка PDF документов** с сохранением структуры и метаданных
- 🔍 **Векторный поиск** по семантическому содержимому (embedding-based)
- 🤖 **Поддержка нескольких AI моделей**: Z.ai (GLM-4.6) и Claude 3.5 Sonnet
- 📌 **Точные ссылки на источники** с указанием документа и страницы
- 💾 **Локальная векторная БД** (ChromaDB) - работает без облачных сервисов
- 💬 **Контекст диалога** - система помнит последние 3 пары вопрос-ответ
- 🌐 **Простой веб-интерфейс** с выбором AI модели и режима знаний
- 🔄 **Два режима знаний**:
  - **Строгий** - только информация из документов
  - **Расширенный** - может дополнить общими знаниями AI

---

## 🏗️ Архитектура системы

```
┌─────────────────────────────────────────────────────────────┐
│                      Пользователь                            │
│                     (Веб-браузер)                            │
└──────────────────────────┬──────────────────────────────────┘
                           │ HTTP/JSON
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                    FastAPI Server                            │
│                     (main.py)                                │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ Endpoints:                                            │  │
│  │  • POST /api/ask      - Обработка вопросов          │  │
│  │  • GET  /health       - Статус сервера              │  │
│  │  • GET  /api/stats    - Статистика БД               │  │
│  │  • GET  /             - Веб-интерфейс               │  │
│  └──────────────────────────────────────────────────────┘  │
└──────────────────────────┬──────────────────────────────────┘
                           │
        ┌──────────────────┼──────────────────┐
        ▼                  ▼                  ▼
┌──────────────┐  ┌─────────────────┐  ┌─────────────────┐
│  VectorDB    │  │   AI Client     │  │  PDF Processor  │
│ (vector_db)  │  │ (ai_client.py)  │  │(pdf_processor)  │
└──────────────┘  └─────────────────┘  └─────────────────┘
        │                  │                       │
        ▼                  ▼                       ▼
┌──────────────┐  ┌─────────────────┐  ┌─────────────────┐
│  ChromaDB    │  │  Z.ai / Claude  │  │  PyPDF2 +       │
│ (Persistent) │  │     API         │  │  pdfplumber     │
│              │  │                 │  │                 │
│ 17,120 chunks│  │  LLM Response   │  │  Text Extract   │
│ 7 documents  │  │                 │  │                 │
└──────────────┘  └─────────────────┘  └─────────────────┘
        │
        ▼
┌──────────────────────────────────────┐
│   Sentence Transformers              │
│   cointegrated/rubert-tiny2          │
│   (Embeddings для русского языка)    │
└──────────────────────────────────────┘
```

### Компоненты системы

#### 1. **Frontend** (`static/index.html`)
- Single-page веб-интерфейс
- Поддержка истории диалога (хранится в памяти браузера)
- Выбор AI провайдера (Z.ai / Claude)
- Выбор режима знаний (строгий / расширенный)
- Отображение метрик запроса (время, токены)

#### 2. **Backend** (`main.py`)
- FastAPI сервер на порту 8000
- Обработка HTTP запросов
- Управление контекстом диалога
- Роутинг между компонентами

#### 3. **Vector Database** (`vector_db.py`)
- ChromaDB для хранения векторов
- Sentence Transformers для создания embeddings
- Векторный поиск по семантической близости
- Персистентное хранилище в `data/chroma_db/`

#### 4. **AI Client** (`ai_client.py`)
- Универсальный клиент для Z.ai и Claude API
- Формирование промптов с контекстом
- Обработка ответов и извлечение источников
- Подсчет токенов

#### 5. **PDF Processor** (`pdf_processor.py`)
- Извлечение текста из PDF (pdfplumber + PyPDF2 fallback)
- Разбиение на чанки с перекрытием (800 символов, overlap 800)
- Извлечение табличных данных
- Очистка текста от артефактов

---

## 💻 Технологии

### Backend
- **Python 3.12** - основной язык
- **FastAPI** - веб-фреймворк
- **Uvicorn** - ASGI сервер
- **Pydantic** - валидация данных

### Vector Database & Embeddings
- **ChromaDB** - векторная база данных
- **Sentence Transformers** - embeddings модель
- **cointegrated/rubert-tiny2** - русскоязычная модель (29 МБ, CPU)

### AI Models
- **Z.ai API (GLM-4.6)** - основная модель
- **Claude 3.5 Sonnet** - альтернативная модель
- **httpx** - HTTP клиент для API

### PDF Processing
- **pdfplumber** - основной метод извлечения текста
- **PyPDF2** - fallback метод
- **regex** - обработка и очистка текста

### Frontend
- **Vanilla JavaScript** - без фреймворков
- **CSS Grid/Flexbox** - современная верстка
- **Markdown parser** - рендеринг форматированных ответов

---

## 🔄 Логика работы

### Процесс индексации (init_db.py)

```
1. Сканирование папки documents/
   └─> Находит все *.pdf файлы

2. Обработка каждого PDF
   ├─> Извлечение текста (pdfplumber)
   ├─> Очистка текста (удаление лишних пробелов)
   ├─> Разбиение на страницы с метаданными
   └─> Создание чанков:
       ├─> Таблицы (отдельные чанки)
       ├─> Глоссарий (если есть)
       └─> Обычный текст (chunk_size=800, overlap=800)

3. Создание эмбеддингов
   ├─> Загрузка модели rubert-tiny2
   ├─> Векторизация каждого чанка (384-мерные векторы)
   └─> Сохранение в ChromaDB

4. Сохранение в базу
   └─> Персистентное хранилище: data/chroma_db/
```

**Особенности индексации:**
- **100% overlap** между чанками - гарантирует захват длинных определений, разбитых водяными знаками
- **Приоритет таблицам** - табличные данные индексируются первыми
- **Глобальный счетчик ID** - уникальные ID для всех чанков из всех документов

### Процесс обработки запроса

```
1. Пользователь вводит вопрос
   └─> Frontend отправляет POST /api/ask

2. Backend получает запрос
   ├─> Добавляет в историю диалога (последние 3 пары)
   ├─> Формирует расширенный вопрос с контекстом
   └─> Определяет параметры:
       ├─> ai_provider (zai/claude)
       ├─> knowledge_mode (strict/expanded)
       └─> n_results (20 чанков)

3. Векторный поиск (vector_db.py)
   ├─> Создает embedding для вопроса
   ├─> Поиск по косинусному сходству в ChromaDB
   ├─> Возвращает топ-20 наиболее релевантных чанков
   └─> Формирует контекст для AI:
       [ДОКУМЕНТ: файл.pdf, стр. X]
       Текст чанка...

4. Генерация ответа (ai_client.py)
   ├─> Формирует промпт:
   │   ├─> Системный промпт (роль эксперта)
   │   ├─> Контекст из документов
   │   ├─> История диалога (если есть)
   │   └─> Вопрос пользователя
   ├─> Отправляет запрос в Z.ai/Claude API
   ├─> Получает ответ с источниками
   └─> Парсит источники (формат: [Документ, стр. X])

5. Возврат ответа пользователю
   ├─> Форматирование Markdown
   ├─> Добавление метрик:
   │   ├─> Время поиска (search_time_ms)
   │   ├─> Время AI (ai_time_ms)
   │   └─> Использованные токены
   └─> Отображение в интерфейсе
```

### Управление контекстом диалога

```javascript
conversationHistory = [
  { role: 'user', content: 'Что такое валидация?' },
  { role: 'assistant', content: 'Валидация - это...' },
  { role: 'user', content: 'Какие виды бывают?' },  // Текущий
]

// При каждом запросе:
1. Добавляется вопрос пользователя
2. История обрезается до последних 6 сообщений (3 пары)
3. Передается в enhanced_question для AI
4. После ответа добавляется ответ ассистента
```

---

## 📦 Структура проекта

```
standart_bot/
├── main.py                 # FastAPI сервер, основная логика
├── vector_db.py           # ChromaDB + embeddings, векторный поиск
├── ai_client.py           # Универсальный клиент для Z.ai и Claude
├── pdf_processor.py       # Обработка PDF → чанки
├── init_db.py             # Скрипт инициализации и индексации
├── requirements.txt       # Python зависимости
├── .env                   # Конфигурация (API ключи, НЕ в git)
├── .env.example           # Пример конфигурации
├── .gitignore            # Git игнорирование
├── README.md             # Эта документация
├── USER_GUIDE.md         # Руководство пользователя
├── DEPLOYMENT.md         # Инструкции по развертыванию
├── test_queries.sh       # Скрипт тестирования API
├── deploy.sh             # Скрипт деплоя на сервер
│
├── documents/            # PDF файлы для индексации
│   ├── Document_N_76.pdf
│   ├── Document_N_77.pdf
│   └── ... (7 документов)
│
├── data/                 # База данных и кэш
│   └── chroma_db/       # ChromaDB персистентное хранилище
│       ├── chroma.sqlite3
│       └── [векторы и метаданные]
│
├── static/              # Веб-интерфейс
│   └── index.html       # Single-page приложение
│
├── venv/                # Python виртуальное окружение (локально)
└── .venv/               # Альтернативное имя venv
```

---

## 🚀 Установка и запуск

### Требования

- **Python 3.12** (минимум 3.10)
- **2 ГБ RAM** (минимум для embeddings модели)
- **500 МБ** свободного места (для ChromaDB)
- **API ключи**: Z.ai и/или Anthropic Claude

### 1. Клонирование проекта

```bash
git clone <your-repo-url> standart_bot
cd standart_bot
```

### 2. Создание виртуального окружения

```bash
python3.12 -m venv venv
source venv/bin/activate  # Linux/Mac
# или
venv\Scripts\activate     # Windows
```

### 3. Установка зависимостей

```bash
pip install -r requirements.txt
```

**Файл requirements.txt:**
```txt
fastapi
uvicorn
python-dotenv
chromadb
sentence-transformers
PyPDF2
pdfplumber
openai
requests
pydantic
anthropic
httpx
```

### 4. Настройка .env файла

```bash
cp .env.example .env
nano .env
```

**Содержимое .env:**
```env
# Z.ai API (основная модель)
ZAI_API_KEY=your_z_ai_api_key_here
ZAI_API_URL=https://api.z.ai/v1/chat/completions

# Claude API (альтернативная модель, опционально)
ANTHROPIC_API_KEY=your_claude_api_key_here

# Настройки сервера
HOST=0.0.0.0
PORT=8000
```

### 5. Добавление документов

```bash
# Создайте папку (если нет)
mkdir -p documents

# Скопируйте PDF файлы
cp /path/to/your/*.pdf documents/
```

### 6. Индексация документов

```bash
python init_db.py
```

**Вывод:**
```
============================================================
Инициализация базы данных документов
============================================================

Найдено PDF файлов: 7
  - Document_N_76.pdf
  - Document_N_77.pdf
  ...

============================================================
ЭТАП 1: Обработка PDF файлов
============================================================

📄 Document_N_76.pdf
Извлечено 45 страниц
Создано 120 обычных чанков + 5 глоссарных + 2 табличных
✓ Готово: 127 чанков

... (для остальных документов)

✓ Всего обработано чанков: 17120

============================================================
ЭТАП 2: Создание эмбеддингов и индексация
============================================================

Создание эмбеддингов (это может занять несколько минут)...

============================================================
✓ ГОТОВО!
============================================================
Индексировано документов: 7
Всего чанков в базе: 17120

Теперь можно запустить сервер:
  python main.py
============================================================
```

### 7. Запуск сервера

```bash
python main.py
```

**Вывод:**
```
Инициализация сервера...
База данных загружена. PDF файлов: 7, чанков: 17120
✓ Клиент Z.ai инициализирован
✓ Клиент Claude инициализирован
Сервер готов к работе!
Запуск сервера на 0.0.0.0:8000
INFO:     Started server process
INFO:     Uvicorn running on http://0.0.0.0:8000
```

### 8. Открытие веб-интерфейса

Откройте в браузере: **http://localhost:8000**

---

## 🌐 Развертывание на VPS

### Предварительные требования

- **VPS сервер** с Ubuntu 20.04+ / Debian 11+
- **2 ГБ RAM** (минимум)
- **2 ГБ свободного места**
- **Python 3.12** (компилируется из исходников, если нет)
- **SSH доступ** к серверу

### Пошаговая инструкция

#### 1. Подключение к серверу

```bash
ssh user@your-server-ip
```

#### 2. Установка зависимостей системы

```bash
# Обновление системы
sudo apt update && sudo apt upgrade -y

# Установка Python 3.12 (если нет)
sudo apt install -y build-essential libssl-dev libffi-dev python3-dev wget

# Скачивание и компиляция Python 3.12
cd /tmp
wget https://www.python.org/ftp/python/3.12.0/Python-3.12.0.tgz
tar -xzf Python-3.12.0.tgz
cd Python-3.12.0
./configure --enable-optimizations --with-ssl
make -j$(nproc)
sudo make altinstall

# Проверка
python3.12 --version  # Python 3.12.0
```

#### 3. Копирование проекта на сервер

**Вариант A: Через git**
```bash
cd /home/user-bot/
git clone <your-repo-url> standard_bot
cd standard_bot
```

**Вариант B: Через scp (с вашего компьютера)**
```bash
# Скопировать код
scp -r /path/to/standart_bot user@server:/home/user-bot/standard_bot

# Скопировать базу данных (если уже проиндексирована)
scp -r /path/to/standart_bot/data user@server:/home/user-bot/standard_bot/
```

#### 4. Настройка виртуального окружения

```bash
cd /home/user-bot/standard_bot
python3.12 -m venv venv
source venv/bin/activate

# Установка зависимостей
pip install --upgrade pip
pip install -r requirements.txt

# Для старых систем с SQLite < 3.35.0
pip install pysqlite3-binary
```

#### 5. Настройка .env файла

```bash
nano .env
```

Добавьте ваши API ключи:
```env
ZAI_API_KEY=your_actual_key
ANTHROPIC_API_KEY=your_actual_key
HOST=0.0.0.0
PORT=8000
```

#### 6. Индексация документов (если не скопирована БД)

```bash
# Убедитесь, что PDF файлы в documents/
ls documents/

# Запустите индексацию
python init_db.py --yes  # --yes для автоматического подтверждения
```

#### 7. Создание systemd службы

```bash
sudo nano /etc/systemd/system/standard_bot.service
```

**Содержимое файла:**
```ini
[Unit]
Description=Standard Bot RAG Chatbot
After=network.target

[Service]
Type=simple
User=user-bot
WorkingDirectory=/home/user-bot/standard_bot
Environment="PATH=/home/user-bot/standard_bot/venv/bin"
ExecStart=/home/user-bot/standard_bot/venv/bin/python main.py
Restart=always
RestartSec=10

# Логирование
StandardOutput=append:/home/user-bot/standard_bot/logs/bot.log
StandardError=append:/home/user-bot/standard_bot/logs/bot_error.log

[Install]
WantedBy=multi-user.target
```

**Создание папки для логов:**
```bash
mkdir -p /home/user-bot/standard_bot/logs
```

#### 8. Запуск службы

```bash
# Перезагрузить systemd
sudo systemctl daemon-reload

# Включить автозапуск
sudo systemctl enable standard_bot

# Запустить службу
sudo systemctl start standard_bot

# Проверить статус
sudo systemctl status standard_bot
```

**Ожидаемый вывод:**
```
● standard_bot.service - Standard Bot RAG Chatbot
   Loaded: loaded (/etc/systemd/system/standard_bot.service; enabled)
   Active: active (running) since Mon 2025-10-13 22:48:15 UTC; 5s ago
 Main PID: 12345 (python)
   CGroup: /system.slice/standard_bot.service
           └─12345 /home/user-bot/standard_bot/venv/bin/python main.py
```

#### 9. Открытие порта в фаерволе

```bash
# Если используется UFW
sudo ufw allow 8000/tcp
sudo ufw status

# Если используется firewalld
sudo firewall-cmd --permanent --add-port=8000/tcp
sudo firewall-cmd --reload
```

#### 10. Проверка работы

```bash
# Локально на сервере
curl http://localhost:8000/health

# С вашего компьютера
curl http://your-server-ip:8000/health
```

**Ожидаемый ответ:**
```json
{
  "status": "ok",
  "documents_count": 7,
  "chunks_count": 17120,
  "ai_providers": ["zai", "claude"]
}
```

#### 11. (Опционально) Настройка Nginx

Если хотите использовать доменное имя:

```bash
sudo apt install nginx

sudo nano /etc/nginx/sites-available/standard_bot
```

**Конфигурация Nginx:**
```nginx
server {
    listen 80;
    server_name yourdomain.com;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
}
```

```bash
sudo ln -s /etc/nginx/sites-available/standard_bot /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

---

## 📡 API Documentation

### POST /api/ask

Отправка вопроса боту.

**Request:**
```json
{
  "question": "Что такое валидация процессов?",
  "n_results": 20,
  "conversation_history": [
    {"role": "user", "content": "Что такое GMP?"},
    {"role": "assistant", "content": "GMP - это..."}
  ],
  "ai_provider": "zai",
  "knowledge_mode": "strict"
}
```

**Parameters:**
- `question` (string, required) - вопрос пользователя
- `n_results` (int, optional, default=20) - количество чанков для контекста
- `conversation_history` (array, optional) - история последних сообщений
- `ai_provider` (string, optional, default="zai") - "zai" или "claude"
- `knowledge_mode` (string, optional, default="strict") - "strict" или "expanded"

**Response:**
```json
{
  "answer": "Валидация процессов - это документированное подтверждение...",
  "sources": [
    "Document_N_77.pdf, стр. 12",
    "Document_N_77.pdf, стр. 45"
  ],
  "success": true,
  "metrics": {
    "ai_provider": "zai",
    "search_time_ms": 125.5,
    "ai_time_ms": 1500.2,
    "total_time_ms": 1625.7,
    "context_length": 12450,
    "sources_count": 20,
    "tokens": {
      "prompt_tokens": 3200,
      "completion_tokens": 450,
      "total_tokens": 3650
    },
    "has_history": true
  }
}
```

### GET /health

Проверка статуса сервера.

**Response:**
```json
{
  "status": "ok",
  "documents_count": 7,
  "chunks_count": 17120,
  "ai_providers": ["zai", "claude"]
}
```

### GET /api/stats

Статистика базы данных.

**Response:**
```json
{
  "total_chunks": 17120,
  "collection_name": "documents",
  "db_path": "./data/chroma_db"
}
```

---

## ⚙️ Конфигурация

### Размер чанков

**Файл:** `init_db.py` или `pdf_processor.py`

```python
processor = PDFProcessor(
    chunk_size=800,      # Размер чанка в символах
    chunk_overlap=800    # Перекрытие между чанками (100%)
)
```

**Рекомендации:**
- **Малые документы** (< 50 страниц): 500-800 символов
- **Большие документы** (> 100 страниц): 800-1200 символов
- **Overlap**: 50-100% от chunk_size (для документов с водяными знаками)

### Количество результатов поиска

**Файл:** `main.py`

```python
n_results = request.n_results if request.n_results else 20
```

**Влияние:**
- **Больше результатов** (25-30) = больше контекста, но медленнее и дороже
- **Меньше результатов** (10-15) = быстрее, но может пропустить информацию

**Текущая настройка:** 20 результатов (оптимально для 17k чанков)

### Модель эмбеддингов

**Файл:** `vector_db.py`

```python
self.embedding_model = SentenceTransformer('cointegrated/rubert-tiny2')
```

**Альтернативы:**
- `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` (средняя)
- `intfloat/multilingual-e5-large` (лучшая, но медленная)
- `BAAI/bge-m3` (новая, хорошая для русского)

**Примечание:** Смена модели требует полной переиндексации!

### AI промпты

**Файл:** `ai_client.py`

```python
system_prompt = """Ты эксперт по нормативным документам.
Твоя задача - давать точные ответы на основе предоставленного контекста.
...
"""
```

Можно настроить:
- Тон ответов (формальный / неформальный)
- Стиль (краткий / развернутый)
- Требования к цитированию источников

---

## 🔧 Troubleshooting

### База данных пуста

**Симптомы:**
```
⚠️ ВНИМАНИЕ: База данных пуста!
Запустите init_db.py для индексации PDF файлов
```

**Решение:**
```bash
# Проверьте наличие PDF
ls documents/

# Запустите индексацию
python init_db.py
```

### Ошибка API ключа

**Симптомы:**
```
⚠️ Z.ai недоступен: No API key provided
```

**Решение:**
```bash
# Проверьте .env файл
cat .env | grep ZAI_API_KEY

# Убедитесь, что ключ правильный
# Проверьте баланс на аккаунте Z.ai
```

### Ошибка SQLite версии

**Симптомы:**
```
RuntimeError: Your system has an unsupported version of sqlite3.
Chroma requires sqlite3 >= 3.35.0
```

**Решение:**
```bash
pip install pysqlite3-binary
```

Добавьте в начало `vector_db.py`:
```python
__import__('pysqlite3')
import sys
sys.modules['sqlite3'] = sys.modules.pop('pysqlite3')
```

### Плохое качество ответов

**Возможные причины и решения:**

1. **Недостаточно контекста**
   ```python
   # Увеличьте n_results в main.py
   n_results = 25  # было 20
   ```

2. **Неоптимальный размер чанков**
   ```python
   # Увеличьте chunk_size
   processor = PDFProcessor(chunk_size=1200, chunk_overlap=600)
   # Требует переиндексации!
   ```

3. **Слабая модель эмбеддингов**
   ```python
   # Смените на более мощную
   self.embedding_model = SentenceTransformer('intfloat/multilingual-e5-large')
   # Требует переиндексации!
   ```

4. **Промпт не настроен**
   - Отредактируйте `system_prompt` в `ai_client.py`
   - Добавьте примеры желаемых ответов

### Медленная работа

**Оптимизации:**

1. **Уменьшите n_results**
   ```python
   n_results = 15  # было 20
   ```

2. **Используйте более легкую модель**
   ```python
   # Текущая rubert-tiny2 уже самая легкая (29 МБ)
   ```

3. **Увеличьте chunk_size** (меньше чанков = быстрее поиск)
   ```python
   chunk_size = 1500  # было 800
   # Но требует переиндексации!
   ```

### Служба не запускается

**Проверка логов:**
```bash
# Логи systemd
sudo journalctl -u standard_bot -n 50

# Логи файлов
tail -f /home/user-bot/standard_bot/logs/bot.log
tail -f /home/user-bot/standard_bot/logs/bot_error.log
```

**Частые проблемы:**
- Неправильный путь к Python в ExecStart
- Не хватает прав на папку
- Порт 8000 занят другим процессом

**Решение:**
```bash
# Проверить путь
which python  # внутри venv

# Проверить порт
ss -tlnp | grep 8000

# Убить процесс на порту
lsof -ti:8000 | xargs kill -9
```

---

## 📊 Управление службой

```bash
# Запуск
sudo systemctl start standard_bot

# Остановка
sudo systemctl stop standard_bot

# Перезапуск
sudo systemctl restart standard_bot

# Статус
sudo systemctl status standard_bot

# Логи в реальном времени
sudo journalctl -u standard_bot -f

# Последние 100 строк
sudo journalctl -u standard_bot -n 100

# Включить автозапуск
sudo systemctl enable standard_bot

# Отключить автозапуск
sudo systemctl disable standard_bot
```

---

## 📈 Метрики и мониторинг

### Метрики запроса

Каждый ответ содержит метрики:

```json
{
  "metrics": {
    "ai_provider": "zai",
    "search_time_ms": 125.5,      // Время векторного поиска
    "ai_time_ms": 1500.2,         // Время генерации ответа AI
    "total_time_ms": 1625.7,      // Общее время
    "context_length": 12450,      // Размер контекста в символах
    "sources_count": 20,          // Количество найденных источников
    "tokens": {
      "prompt_tokens": 3200,      // Токены промпта
      "completion_tokens": 450,   // Токены ответа
      "total_tokens": 3650        // Всего токенов
    },
    "has_history": true           // Использован ли контекст диалога
  }
}
```

### Мониторинг сервера

```bash
# CPU и память процесса
top -p $(pgrep -f "python main.py")

# Размер базы данных
du -sh data/chroma_db/

# Количество запросов (из логов)
grep "POST /api/ask" logs/bot.log | wc -l

# Средний response time (из логов)
grep "total_time_ms" logs/bot.log | tail -100
```

---

## 🔄 Обновление системы

### Добавление новых документов

```bash
# 1. Добавьте PDF в documents/
cp new_document.pdf documents/

# 2. Остановите службу
sudo systemctl stop standard_bot

# 3. Переиндексируйте базу
python init_db.py --yes

# 4. Запустите службу
sudo systemctl start standard_bot
```

### Обновление кода

```bash
# 1. Остановите службу
sudo systemctl stop standard_bot

# 2. Обновите код
git pull origin main
# или
scp -r updated_files/* user@server:/home/user-bot/standard_bot/

# 3. Обновите зависимости (если изменились)
source venv/bin/activate
pip install -r requirements.txt

# 4. Запустите службу
sudo systemctl start standard_bot
```

---

## 📝 Лицензия

MIT License

---

## 👤 Автор

Проект создан для работы с нормативными документами фармацевтической отрасли.

## 🤝 Поддержка

По вопросам и предложениям создавайте issues в репозитории проекта.

---

**Версия:** 1.0.0
**Дата обновления:** 13 октября 2025
