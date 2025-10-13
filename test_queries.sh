#!/bin/bash

# Скрипт для тестирования различных запросов к RAG системе

echo "========================================"
echo "ТЕСТИРОВАНИЕ RAG СИСТЕМЫ"
echo "========================================"
echo ""

# Функция для отправки запроса и вывода результата
test_query() {
    local question="$1"
    local n_results="${2:-10}"

    echo "Вопрос: $question"
    echo "----------------------------------------"

    response=$(curl -s 'http://localhost:8000/api/ask' \
        -H 'Content-Type: application/json' \
        -d "{\"question\": \"$question\", \"search_mode\": \"rag\", \"n_results\": $n_results}")

    # Извлекаем ответ и источники
    answer=$(echo "$response" | python3 -c "import sys, json; data=json.load(sys.stdin); print(data.get('answer', 'ERROR')[:400])")
    sources=$(echo "$response" | python3 -c "import sys, json; data=json.load(sys.stdin); srcs = data.get('sources', []); print('\n'.join(['  - ' + s for s in srcs[:3]]))")
    search_time=$(echo "$response" | python3 -c "import sys, json; data=json.load(sys.stdin); print(data.get('metrics', {}).get('search_time_ms', 0))")

    echo "Ответ: $answer..."
    echo ""
    echo "Источники (первые 3):"
    echo "$sources"
    echo ""
    echo "Время поиска: ${search_time}мс"
    echo ""
    echo "========================================"
    echo ""
}

# Тест 1: Список документов
test_query "какие документы у тебя есть" 5

# Тест 2: Определение термина из N_79
test_query "что такое аудит" 10

# Тест 3: Термин из глоссария
test_query "что такое благополучие субъекта исследования" 10

# Тест 4: Термин "протокол"
test_query "что такое протокол исследования" 10

# Тест 5: Вопрос о мониторинге
test_query "что такое мониторинг клинического исследования" 10

# Тест 6: Вопрос о процедурах
test_query "какие требования к информированному согласию" 10

echo "ТЕСТИРОВАНИЕ ЗАВЕРШЕНО"
