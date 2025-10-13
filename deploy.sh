#!/bin/bash
# Скрипт деплоя на VPS сервер

set -e  # Остановка при ошибке

echo "=== Деплой RAG чат-бота на VPS ==="

# Переход в директорию проекта
cd "$(dirname "$0")"

# Создание виртуального окружения если его нет
if [ ! -d "venv" ]; then
    echo "Создание виртуального окружения..."
    python3 -m venv venv
fi

# Активация виртуального окружения
source venv/bin/activate

# Обновление pip
echo "Обновление pip..."
pip install --upgrade pip

# Установка зависимостей
echo "Установка зависимостей..."
pip install -r requirements.txt

# Проверка наличия .env файла
if [ ! -f ".env" ]; then
    echo "⚠️  ВНИМАНИЕ: Файл .env не найден!"
    echo "Скопируйте .env.example в .env и добавьте API ключи:"
    echo "  cp .env.example .env"
    echo "  nano .env"
    exit 1
fi

# Проверка наличия PDF файлов
if [ ! -d "pdfs" ] || [ -z "$(ls -A pdfs 2>/dev/null)" ]; then
    echo "⚠️  ВНИМАНИЕ: Папка pdfs пуста!"
    echo "Добавьте PDF файлы в папку pdfs/"
fi

# Проверка индексации документов
if [ ! -d "data/chroma_db" ]; then
    echo "Индексация документов..."
    python init_db.py --yes
else
    echo "База данных уже существует. Пропуск индексации."
    echo "Для переиндексации запустите: python init_db.py --yes"
fi

echo ""
echo "=== Деплой завершен! ==="
echo ""
echo "Для запуска сервера:"
echo "  sudo systemctl start ragbot"
echo ""
echo "Для просмотра логов:"
echo "  sudo journalctl -u ragbot -f"
