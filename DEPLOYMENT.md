# Инструкция по развертыванию на VPS

## Предварительные требования

- VPS с Ubuntu/Debian
- Python 3.8+
- Доступ по SSH
- Nginx (опционально, для прокси)

## Шаг 1: Подготовка на локальной машине

### 1.1 Создайте архив проекта

```bash
# Перейдите в папку проекта
cd /Users/kerosinshik/Documents/Programming/ToOrder/standart_bot

# Исключаем ненужное и создаем архив
tar -czf ragbot.tar.gz \
  --exclude='venv' \
  --exclude='__pycache__' \
  --exclude='*.pyc' \
  --exclude='.git' \
  --exclude='data/chroma_db' \
  .
```

### 1.2 Скопируйте на сервер

```bash
# Замените YOUR_USER и YOUR_SERVER
scp ragbot.tar.gz YOUR_USER@YOUR_SERVER:/home/YOUR_USER/
```

## Шаг 2: Установка на сервере (под обычным пользователем)

### 2.1 Подключитесь к серверу

```bash
ssh YOUR_USER@YOUR_SERVER
```

### 2.2 Распакуйте проект

```bash
cd ~
mkdir -p standart_bot
tar -xzf ragbot.tar.gz -C standart_bot
cd standart_bot
```

### 2.3 Настройте окружение

```bash
# Установите Python 3 и venv если нет
sudo apt update
sudo apt install python3 python3-venv python3-pip -y

# Сделайте скрипт деплоя исполняемым
chmod +x deploy.sh

# Запустите деплой
./deploy.sh
```

### 2.4 Настройте .env файл

```bash
# Скопируйте пример
cp .env.example .env

# Отредактируйте и добавьте API ключи
nano .env
```

**Обязательно добавьте:**
- `ZAI_API_KEY=ваш_ключ` (или/и)
- `ANTHROPIC_API_KEY=ваш_ключ`

### 2.5 Добавьте PDF файлы

```bash
# Создайте папку для PDF
mkdir -p pdfs

# Скопируйте ваши PDF файлы в эту папку
# Например, через scp с локальной машины:
# scp /path/to/your/pdfs/*.pdf YOUR_USER@YOUR_SERVER:~/standart_bot/pdfs/
```

### 2.6 Проиндексируйте документы

```bash
./venv/bin/python init_db.py --yes
```

## Шаг 3: Настройка systemd службы (под админом)

### 3.1 Отредактируйте ragbot.service

```bash
# Откройте файл службы
nano ragbot.service
```

**Замените:**
- `YOUR_USERNAME` → ваше имя пользователя (например, `botuser`)
- `/home/YOUR_USERNAME/standart_bot` → полный путь к проекту

### 3.2 Установите службу (требуется sudo)

```bash
# Скопируйте файл службы в systemd
sudo cp ragbot.service /etc/systemd/system/

# Перезагрузите systemd
sudo systemctl daemon-reload

# Включите автозапуск
sudo systemctl enable ragbot

# Запустите службу
sudo systemctl start ragbot

# Проверьте статус
sudo systemctl status ragbot
```

## Шаг 4: Проверка работы

### 4.1 Проверьте логи

```bash
# Просмотр логов в реальном времени
sudo journalctl -u ragbot -f

# Последние 100 строк
sudo journalctl -u ragbot -n 100
```

### 4.2 Проверьте доступность API

```bash
curl http://localhost:8000/health
```

Должно вернуть:
```json
{
  "status": "ok",
  "documents_count": 2,
  "chunks_count": 220,
  "ai_providers": ["zai", "claude"]
}
```

## Шаг 5: Настройка Nginx (опционально)

Если хотите доступ извне через домен:

```bash
sudo nano /etc/nginx/sites-available/ragbot
```

Добавьте конфигурацию:

```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

Активируйте конфигурацию:

```bash
sudo ln -s /etc/nginx/sites-available/ragbot /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

## Управление службой

### Команды systemctl

```bash
# Запуск
sudo systemctl start ragbot

# Остановка
sudo systemctl stop ragbot

# Перезапуск
sudo systemctl restart ragbot

# Статус
sudo systemctl status ragbot

# Отключить автозапуск
sudo systemctl disable ragbot

# Включить автозапуск
sudo systemctl enable ragbot
```

### Просмотр логов

```bash
# В реальном времени
sudo journalctl -u ragbot -f

# Последние N строк
sudo journalctl -u ragbot -n 100

# За определенный период
sudo journalctl -u ragbot --since "1 hour ago"
```

## Обновление приложения

```bash
# 1. Остановите службу
sudo systemctl stop ragbot

# 2. Перейдите в папку проекта
cd ~/standart_bot

# 3. Сделайте бэкап (опционально)
cp -r data/chroma_db data/chroma_db.backup

# 4. Загрузите новый код (через git или scp)
# Вариант 1: Git
git pull

# Вариант 2: Архив
# На локальной машине:
# tar -czf ragbot.tar.gz --exclude='venv' --exclude='data' .
# scp ragbot.tar.gz YOUR_USER@YOUR_SERVER:~/
# На сервере:
# tar -xzf ~/ragbot.tar.gz -C ~/standart_bot

# 5. Обновите зависимости
./venv/bin/pip install -r requirements.txt

# 6. Перезапустите службу
sudo systemctl start ragbot

# 7. Проверьте статус
sudo systemctl status ragbot
```

## Переиндексация документов

Если добавили/изменили PDF файлы:

```bash
# Остановите службу
sudo systemctl stop ragbot

# Переиндексируйте
cd ~/standart_bot
./venv/bin/python init_db.py --yes

# Запустите службу
sudo systemctl start ragbot
```

## Troubleshooting

### Служба не запускается

```bash
# Проверьте логи
sudo journalctl -u ragbot -n 50

# Проверьте права доступа
ls -la ~/standart_bot

# Проверьте .env файл
cat ~/standart_bot/.env
```

### Ошибка "Permission denied"

```bash
# Убедитесь что пользователь в ragbot.service правильный
sudo nano /etc/systemd/system/ragbot.service

# Исправьте владельца файлов
sudo chown -R YOUR_USERNAME:YOUR_USERNAME ~/standart_bot
```

### База данных не инициализирована

```bash
cd ~/standart_bot
./venv/bin/python init_db.py --yes
```

### API ключи не работают

```bash
# Проверьте .env
cat .env

# Убедитесь что нет пробелов
# Правильно: ZAI_API_KEY=abc123
# Неправильно: ZAI_API_KEY = abc123
```

## Безопасность

### Firewall

Если используете только локально:
```bash
# Разрешите только localhost
sudo ufw deny 8000
```

Если через Nginx:
```bash
# Разрешите HTTP/HTTPS
sudo ufw allow 80
sudo ufw allow 443
sudo ufw deny 8000  # Блокируем прямой доступ
```

### SSL/TLS (для продакшна)

```bash
# Установите certbot
sudo apt install certbot python3-certbot-nginx

# Получите сертификат
sudo certbot --nginx -d your-domain.com
```

## Мониторинг

### Использование ресурсов

```bash
# CPU и память
top -p $(pgrep -f "python main.py")

# Логи в реальном времени
sudo journalctl -u ragbot -f
```

### Алерты при падении

Systemd автоматически перезапустит службу при падении (настроено через `Restart=always`).
