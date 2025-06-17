# AI Модуль OvozPay

Модуль искусственного интеллекта для автоматизации финансовых операций с использованием OCR (распознавание чеков) и голосового управления.

## 🎯 Основные возможности

### OCR (Оптическое распознавание символов)
- **Распознавание чеков** на русском, узбекском и английском языках
- **Извлечение данных**: название магазина, сумма, товары, дата
- **Автоматическая категоризация** товаров и трат
- **Предобработка изображений** для улучшения качества распознавания

### Голосовое управление
- **Распознавание речи** с помощью Whisper.cpp
- **Голосовые команды**: создание категорий, добавление трат, проверка баланса
- **Многоязычность**: русский, узбекский, английский
- **Обработка команд** с автоматическим выполнением действий

### NLP и анализ
- **Определение категорий** по ключевым словам
- **Анализ текста** для извлечения финансовых данных
- **Обработка команд** на естественном языке

## 🚀 Установка

### 1. Системные зависимости

#### macOS (Homebrew)
```bash
# Tesseract OCR
brew install tesseract tesseract-lang

# FFmpeg для аудио
brew install ffmpeg

# Whisper.cpp (опционально)
git clone https://github.com/ggerganov/whisper.cpp.git
cd whisper.cpp
make
```

#### Ubuntu/Debian
```bash
# Tesseract OCR
sudo apt-get install tesseract-ocr tesseract-ocr-rus tesseract-ocr-eng

# FFmpeg
sudo apt-get install ffmpeg

# Дополнительные библиотеки
sudo apt-get install libsndfile1 portaudio19-dev
```

### 2. Python зависимости
```bash
# Установка AI зависимостей
pip install -r requirements-ai.txt

# Или поэтапно:
pip install pytesseract Pillow opencv-python
pip install pydub librosa soundfile
pip install nltk textdistance langdetect
```

### 3. Настройка моделей

#### Tesseract языковые пакеты
```bash
# Проверка установленных языков
tesseract --list-langs

# Скачивание дополнительных языков (если нужно)
# Для узбекского языка может потребоваться дополнительная настройка
```

#### Whisper модели
```bash
# Создание директории для моделей
mkdir -p models/whisper

# Скачивание моделей (примеры)
wget https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-small.bin -O models/whisper/ggml-small.bin
wget https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-base.bin -O models/whisper/ggml-base.bin
```

## 📊 API Endpoints

### OCR Endpoints
```
GET    /api/ai/ocr/                    # Список результатов OCR
POST   /api/ai/ocr/                    # Загрузка и обработка изображения
GET    /api/ai/ocr/{id}/               # Детали результата OCR
POST   /api/ai/ocr/{id}/reprocess/     # Повторная обработка
POST   /api/ai/ocr/bulk_process/       # Массовая обработка
GET    /api/ai/ocr/statistics/         # Статистика OCR
```

### Voice Endpoints
```
GET    /api/ai/voice/                  # Список голосовых результатов
POST   /api/ai/voice/                  # Загрузка и распознавание аудио
GET    /api/ai/voice/{id}/             # Детали результата
POST   /api/ai/voice/{id}/reprocess/   # Повторное распознавание
```

### Command Endpoints
```
GET    /api/ai/commands/               # Список команд
POST   /api/ai/commands/               # Создание команды
POST   /api/ai/commands/{id}/execute/  # Выполнение команды
```

### Service Endpoints
```
GET    /api/ai/service/status/         # Статус сервисов
GET    /api/ai/service/commands/       # Поддерживаемые команды
POST   /api/ai/service/match_receipt/  # Сопоставление чека и голоса
```

## 🎤 Голосовые команды

### Поддерживаемые команды

#### Создание категории
- "Создай категорию продукты"
- "Добавь новую категорию транспорт"

#### Добавление трат
- "Добавь трату 5000 сум на продукты"
- "Запиши расход 100 долларов на такси"

#### Проверка баланса
- "Покажи мой баланс"
- "Сколько у меня денег?"

#### Управление долгами
- "Добавь долг Ахмаду 50000 сум"
- "Верни долг Фариде"

#### Удаление категорий
- "Удали категорию развлечения"

## 🔧 Конфигурация

### Настройки Django
```python
# settings.py

# Tesseract путь (если не в PATH)
TESSERACT_CMD = '/usr/local/bin/tesseract'  # macOS Homebrew
# TESSERACT_CMD = '/usr/bin/tesseract'      # Linux

# Whisper настройки
WHISPER_MODEL_PATH = 'models/whisper/ggml-small.bin'
WHISPER_EXECUTABLE = '/path/to/whisper/main'

# Поддерживаемые языки
AI_SUPPORTED_LANGUAGES = ['ru', 'uz', 'en']

# Максимальные размеры файлов
MAX_IMAGE_SIZE = 10 * 1024 * 1024  # 10MB
MAX_AUDIO_SIZE = 25 * 1024 * 1024  # 25MB
```

## 📝 Примеры использования

### OCR обработка
```python
from apps.ai.services.ocr.tesseract_service import TesseractOCRService
from django.core.files.uploadedfile import SimpleUploadedFile

# Инициализация сервиса
ocr_service = TesseractOCRService()

# Обработка изображения
with open('receipt.jpg', 'rb') as f:
    image_file = SimpleUploadedFile('receipt.jpg', f.read())
    result = ocr_service.process_receipt_image(user, image_file)

print(f"Распознанный текст: {result.recognized_text}")
print(f"Магазин: {result.shop_name}")
print(f"Сумма: {result.total_amount}")
```

### Голосовое распознавание
```python
from apps.ai.services.voice.whisper_service import WhisperVoiceService

# Инициализация сервиса
voice_service = WhisperVoiceService()

# Обработка аудио
with open('voice_command.mp3', 'rb') as f:
    audio_file = SimpleUploadedFile('command.mp3', f.read())
    result = voice_service.process_voice_message(user, audio_file, 'voice_command')

print(f"Распознанный текст: {result.recognized_text}")
print(f"Язык: {result.language_detected}")
```

## 🔍 Мониторинг и логирование

### Просмотр логов
```python
from apps.ai.models import AIProcessingLog

# Последние операции
recent_logs = AIProcessingLog.objects.filter(
    user=user,
    operation_type='ocr_processing'
).order_by('-created_at')[:10]

# Статистика по пользователю
user_stats = AIProcessingLog.objects.filter(user=user).values(
    'operation_type'
).annotate(count=models.Count('id'))
```

### Django Admin
- Перейдите в `/admin/ai/` для управления результатами
- Просмотр изображений и аудио файлов
- Мониторинг статистики обработки

## ⚠️ Известные ограничения

1. **Tesseract** может требовать дополнительной настройки для узбекского языка
2. **Whisper.cpp** требует компиляции из исходников
3. **Большие аудио файлы** (>5 минут) могут обрабатываться медленно
4. **Качество OCR** зависит от качества изображения чека

## 🛠 Разработка и тестирование

### Запуск тестов
```bash
python manage.py test apps.ai
```

### Проверка сервисов
```bash
python manage.py shell
>>> from apps.ai.services.ocr.tesseract_service import TesseractOCRService
>>> service = TesseractOCRService()
>>> service.get_processing_status()
```

## 📞 Поддержка

При возникновении проблем:
1. Проверьте установку системных зависимостей
2. Убедитесь в корректности путей к исполняемым файлам
3. Проверьте логи в Django Admin
4. Обратитесь к документации Tesseract и Whisper.cpp 