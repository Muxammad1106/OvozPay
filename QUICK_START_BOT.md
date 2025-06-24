# 🚀 БЫСТРЫЙ ЗАПУСК TELEGRAM БОТА OVOZPAY

## 📋 **ПРЕДВАРИТЕЛЬНЫЕ ТРЕБОВАНИЯ**

### 1. **Настройки Django**
Создайте файл `backend/config/settings_dev.py` (без .example):

```python
DEBUG = True
SMS_CODE_ACTIVE = False
ESKIZ_TOKEN = ""

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'ovozpay',
        'USER': 'your_username',
        'PASSWORD': 'your_password',
        'HOST': 'localhost',
        'PORT': 5432,
    }
}

# Telegram Bot настройки (ОБЯЗАТЕЛЬНО!)
TELEGRAM_BOT_TOKEN = "your_bot_token_from_botfather"
TELEGRAM_WEBHOOK_URL = "https://yourdomain.com/telegram/webhook/"

# AI Services настройки
OPENAI_API_KEY = "your_openai_api_key_here"
DEEPSEEK_API_KEY = "your_deepseek_api_key_here"

# External APIs
CBU_API_URL = "https://cbu.uz/uz/arkhiv-kursov-valyut/json/"
```

### 2. **База данных**
Убедитесь, что PostgreSQL запущен и доступен.

---

## ⚡ **БЫСТРЫЙ ЗАПУСК (3 КОМАНДЫ)**

### 1. **Проверка AI сервисов**
```bash
python manage.py init_ai_services --check-only
```

### 2. **Настройка webhook**
```bash
python manage.py setup_bot_webhook --url https://yourdomain.com/telegram/webhook/
```

### 3. **Тестирование бота**
```bash
python manage.py test_bot --get-me
```

---

## 🔍 **ДЕТАЛЬНАЯ ПРОВЕРКА**

### **Проверка Django**
```bash
python manage.py check
python manage.py showmigrations bot
```

### **Проверка webhook**
```bash
python manage.py test_bot --check-webhook
```

### **Отправка тестового сообщения**
```bash
python manage.py test_bot --chat-id YOUR_TELEGRAM_ID
```

---

## 🌐 **ЗАПУСК СЕРВЕРА**

### **Development сервер**
```bash
python manage.py runserver 0.0.0.0:8000
```

### **Production (с Gunicorn)**
```bash
gunicorn config.wsgi:application --bind 0.0.0.0:8000
```

---

## 📊 **ДОСТУПНЫЕ ENDPOINTS**

- **Webhook:** `https://yourdomain.com/telegram/webhook/`
- **API Bot:** `https://yourdomain.com/api/bot/webhook/`
- **Status:** `https://yourdomain.com/api/bot/status/`
- **Admin:** `https://yourdomain.com/admin/`
- **Swagger:** `https://yourdomain.com/swagger/`

---

## 🎯 **ФУНКЦИИ БОТА**

### **Базовые команды:**
- `/start` - Начать работу с ботом
- `/help` - Помощь
- `/balance` - Текущий баланс
- `/settings` - Настройки
- `/language` - Смена языка
- `/currency` - Смена валюты

### **AI функции:**
- 🎤 **Голосовые сообщения** → Создание транзакций
- 📸 **Фото чеков** → OCR и создание операций
- 💬 **Текстовые команды** → Умный парсинг

---

## 🛠️ **УПРАВЛЕНИЕ**

### **Удаление webhook**
```bash
python manage.py setup_bot_webhook --delete
```

### **Просмотр зависимостей**
```bash
python manage.py init_ai_services --install-deps
```

### **Django админка**
Создайте суперпользователя:
```bash
python manage.py createsuperuser
```

---

## 🔧 **TROUBLESHOOTING**

### **Проблема 1: Bot token не работает**
```bash
python manage.py test_bot --get-me
```

### **Проблема 2: Webhook не отвечает**
```bash
python manage.py test_bot --check-webhook
```

### **Проблема 3: AI сервисы недоступны**
```bash
python manage.py init_ai_services --check-only
```

### **Проблема 4: Ошибки в базе данных**
```bash
python manage.py migrate
python manage.py check
```

---

## 📈 **МОНИТОРИНГ**

### **Логирование**
Все операции логируются в:
- Django стандартные логи
- Модель `MessageLog` (все сообщения)
- Модель `VoiceCommand` (голосовые команды)
- Модель `PhotoReceipt` (фото обработка)
- Модель `BotStatistics` (статистика)

### **Статистика в админке**
Перейдите в Django Admin → Bot → Bot Statistics

---

## 🎉 **ВСЁ ГОТОВО!**

После выполнения этих шагов ваш Telegram бот с AI интеграцией будет полностью готов к работе!

**Основные возможности:**
- ✅ Обработка голосовых команд
- ✅ OCR фотографий чеков  
- ✅ Умный парсинг транзакций
- ✅ Многоязычная поддержка
- ✅ Множественные валюты
- ✅ Полная аналитика и логирование

---

**💡 Если возникнут проблемы, проверьте:**
1. Настройки в settings_dev.py (особенно TELEGRAM_BOT_TOKEN)
2. Статус сервисов AI (init_ai_services --check-only)  
3. Webhook настройки (test_bot --check-webhook)
4. Логи Django и бота (bot_debug.log)

**📁 Структура настроек:**
- `settings_dev.py` - для локальной разработки
- `settings_prod.py` - для production сервера
- Копируйте из `.example` файлов и убирайте `.example`

</rewritten_file> 