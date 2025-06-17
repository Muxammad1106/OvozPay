# Инструкция по установке OvozPay

## Системные зависимости

### macOS
```bash
# Homebrew (если не установлен)
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Основные зависимости
brew install tesseract
brew install ffmpeg
brew install python@3.11
brew install postgresql

# Языки для Tesseract
brew install tesseract-lang

# Whisper (опционально, можно использовать OpenAI Whisper)
brew install whisper-cpp
```

### Ubuntu/Debian
```bash
# Обновляем систему
sudo apt update && sudo apt upgrade -y

# Python и основные инструменты
sudo apt install python3.11 python3.11-pip python3.11-venv python3.11-dev

# Tesseract OCR
sudo apt install tesseract-ocr tesseract-ocr-rus tesseract-ocr-eng
sudo apt install libtesseract-dev

# FFmpeg для аудио
sudo apt install ffmpeg

# Дополнительные библиотеки
sudo apt install libgl1-mesa-glx libglib2.0-0 libsm6 libxext6 libxrender-dev libgomp1

# PostgreSQL
sudo apt install postgresql postgresql-contrib
```

### Windows
```powershell
# Используйте Chocolatey или установите вручную:
# 1. Python 3.11 - https://www.python.org/downloads/
# 2. Tesseract - https://github.com/UB-Mannheim/tesseract/wiki
# 3. FFmpeg - https://ffmpeg.org/download.html
# 4. PostgreSQL - https://www.postgresql.org/download/windows/

# Через Chocolatey:
choco install python311 tesseract ffmpeg postgresql
```

## Установка Python зависимостей

```bash
# Переходим в директорию проекта
cd backend

# Создаем виртуальное окружение
python3.11 -m venv venv

# Активируем виртуальное окружение
# macOS/Linux:
source venv/bin/activate
# Windows:
# venv\Scripts\activate

# Обновляем pip
pip install --upgrade pip

# Устанавливаем зависимости
pip install -r requirements.txt
```

## Настройка базы данных PostgreSQL

```bash
# Создаем пользователя и базу данных
sudo -u postgres psql

# В psql:
CREATE USER ovozpay_user WITH PASSWORD 'ovozpay_password';
CREATE DATABASE ovozpay_db OWNER ovozpay_user;
GRANT ALL PRIVILEGES ON DATABASE ovozpay_db TO ovozpay_user;
\q
```

## Настройка переменных окружения

Создайте файл `.env` в директории `backend/`:

```env
# Django
DEBUG=True
SECRET_KEY=your-very-secret-key-here-change-in-production
ALLOWED_HOSTS=localhost,127.0.0.1

# Database
DATABASE_URL=postgres://ovozpay_user:ovozpay_password@localhost:5432/ovozpay_db

# Telegram Bot
TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here

# AI Settings
WHISPER_MODEL_PATH=models/whisper/
TESSERACT_LANG=rus+eng+uzb
```

## Инициализация проекта

```bash
# Применяем миграции
python manage.py migrate

# Создаем суперпользователя
python manage.py createsuperuser

# Собираем статические файлы
python manage.py collectstatic --noinput

# Проверяем настройки
python manage.py check
```

## Установка Whisper моделей

```bash
# Создаем директорию для моделей
mkdir -p models/whisper

# Скачиваем модели Whisper (выберите одну)
# Маленькая модель (быстрая, менее точная):
wget https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-base.bin -O models/whisper/ggml-base.bin

# Средняя модель (рекомендуется):
wget https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-small.bin -O models/whisper/ggml-small.bin

# Или используйте OpenAI Whisper (устанавливается автоматически через pip)
```

## Проверка установки

```bash
# Проверяем Tesseract
tesseract --version

# Проверяем FFmpeg
ffmpeg -version

# Проверяем Python зависимости
python -c "import cv2, nltk, pytesseract; print('All AI dependencies OK')"

# Проверяем Django
python manage.py check

# Тестируем Telegram бота
python manage.py test_bot
```

## Запуск проекта

```bash
# Запуск Django сервера
python manage.py runserver

# В отдельном терминале - запуск Telegram бота
python manage.py run_bot
```

## Проверка функциональности

1. **Веб-интерфейс**: http://localhost:8000/
2. **API документация**: http://localhost:8000/api/docs/
3. **Админка**: http://localhost:8000/admin/

4. **Telegram бот**:
   - Отправьте `/start` боту
   - Попробуйте голосовое сообщение: "Покажи баланс"
   - Отправьте фото чека для тестирования OCR

## Решение проблем

### Ошибки Tesseract
```bash
# Проверьте установку языков
tesseract --list-langs

# Если нет русского языка:
# Ubuntu: sudo apt install tesseract-ocr-rus
# macOS: уже включен в tesseract-lang
```

### Ошибки FFmpeg
```bash
# Проверьте PATH
which ffmpeg

# Если не найден, добавьте в PATH или переустановите
```

### Ошибки Whisper
```bash
# Если проблемы с моделями, используйте OpenAI Whisper:
pip install openai-whisper

# Скачайте модель:
python -c "import whisper; whisper.load_model('base')"
```

### Ошибки базы данных
```bash
# Перезапуск PostgreSQL:
# macOS: brew services restart postgresql
# Ubuntu: sudo systemctl restart postgresql

# Проверка подключения:
python manage.py dbshell
```

## Производственное развертывание

Для продакшена выполните дополнительные настройки:

1. Измените `DEBUG=False` в `.env`
2. Сгенерируйте новый `SECRET_KEY`
3. Настройте `ALLOWED_HOSTS`
4. Используйте внешнюю базу данных
5. Настройте NGINX/Apache
6. Используйте Gunicorn
7. Настройте SSL сертификаты
8. Настройте резервное копирование

```bash
# Установка Gunicorn
pip install gunicorn

# Запуск в продакшене
gunicorn ovozpay.wsgi:application --bind 0.0.0.0:8000
``` 