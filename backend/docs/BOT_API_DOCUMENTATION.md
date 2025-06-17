# 🤖 OvozPay Telegram Bot API Documentation

## 🚀 Обзор

**Telegram Bot:** @OvozPayBot  
**Webhook URL:** `/telegram/webhook/`  
**API Base URL:** `http://localhost:8000/api/`

## 🔗 Аутентификация через Telegram

### 1. Регистрация через Telegram
**POST** `/api/auth/telegram-register/`

```json
{
    "telegram_chat_id": "123456789",
    "phone_number": "+998901234567",
    "language": "ru"
}
```

**Ответ:**
```json
{
    "access": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
    "refresh": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
    "user": {
        "id": "550e8400-e29b-41d4-a716-446655440000",
        "phone_number": "+998901234567",
        "language": "ru",
        "is_active": true
    }
}
```

### 2. Логин через Telegram ID
**POST** `/api/auth/telegram-login/`

```json
{
    "telegram_chat_id": "123456789",
    "phone_number": "+998901234567"  // опционально
}
```

**Ответ:**
```json
{
    "access": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
    "refresh": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
    "user": {
        "id": "550e8400-e29b-41d4-a716-446655440000",
        "phone_number": "+998901234567",
        "language": "ru",
        "is_active": true
    }
}
```

### 3. Проверка авторизации
**POST** `/api/auth/telegram-auth/`

```json
{
    "telegram_chat_id": "123456789"
}
```

## 🤖 Команды бота

### Основные команды
- `/start` - Приветствие и регистрация
- `/balance` - Показать текущий баланс
- `/help` - Справка по командам

### Примеры взаимодействия

#### Команда /start
**Пользователь:** `/start`

**Бот ответ:**
```
🎉 Добро пожаловать в OvozPay!

Привет, Имя! 👋

Я ваш голосовой помощник для управления финансами. 
С моей помощью вы можете:

💰 Отслеживать доходы и расходы
🎯 Управлять целями накопления  
📊 Получать аналитику по тратам
💳 Контролировать долги

Основные команды:
/balance - показать баланс
/help - справка по командам

Для полного функционала зарегистрируйтесь через наше приложение!
```

#### Команда /balance
**Пользователь:** `/balance`

**Бот ответ:**
```
💰 Ваш баланс

Текущий баланс: 1,500,000 UZS

📱 Для просмотра подробной статистики используйте наше приложение.
```

#### Команда /help
**Пользователь:** `/help`

**Бот ответ:**
```
🤖 Справка по командам OvozPay

Основные команды:
/start - начать работу с ботом
/balance - показать текущий баланс
/help - показать эту справку

Голосовые команды:
🎤 Отправьте голосовое сообщение для:
• Добавления трат: "Потратил 50000 на продукты"
• Добавления доходов: "Получил зарплату 2000000"
• Создания целей: "Хочу накопить на телефон 5000000"

Дополнительные функции:
📊 Детальная аналитика в приложении
🎯 Управление целями накопления
💳 Отслеживание долгов

Для полного доступа к функциям зарегистрируйтесь в приложении!
```

## 🎤 Голосовые сообщения

Бот распознает голосовые сообщения и создает записи в `VoiceCommandLog`.

**Поддерживаемые фразы:**
- **Расходы:** "потратил", "купил", "заплатил"
- **Доходы:** "получил", "заработал", "зарплата"
- **Цели:** "накопить", "цель", "копить"

## 📡 Webhook

### Настройка webhook
**URL:** `https://your-domain.com/telegram/webhook/`  
**Метод:** POST  
**Content-Type:** application/json

### Структура webhook запроса
```json
{
    "update_id": 123456789,
    "message": {
        "message_id": 123,
        "from": {
            "id": 123456789,
            "is_bot": false,
            "first_name": "Имя",
            "username": "username"
        },
        "chat": {
            "id": 123456789,
            "first_name": "Имя",
            "username": "username",
            "type": "private"
        },
        "date": 1640995200,
        "text": "/start"
    }
}
```

### Ответ webhook
```json
200 OK
"OK"
```

## 🔧 Настройка локального тестирования

### 1. Установка ngrok
```bash
# macOS
brew install ngrok

# или скачать с https://ngrok.com/download
```

### 2. Запуск ngrok
```bash
ngrok http 8000
```

**Результат:**
```
Forwarding    https://abc123.ngrok.io -> http://localhost:8000
```

### 3. Установка webhook
```bash
curl -X POST \
  "https://api.telegram.org/bot8115661165:AAHWkrF_VVfppRcGjxu5ATlt0uOs5qWLJSw/setWebhook" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://abc123.ngrok.io/telegram/webhook/"
  }'
```

### 4. Проверка webhook
```bash
curl -X GET \
  "https://api.telegram.org/bot8115661165:AAHWkrF_VVfppRcGjxu5ATlt0uOs5qWLJSw/getWebhookInfo"
```

## 🛠 API Сервисы

### TelegramAPIService методы

#### Отправка сообщения
```python
from apps.bot.telegram.services import TelegramAPIService

service = TelegramAPIService()

# Синхронная отправка
service.send_message(
    chat_id=123456789,
    text="Привет! 👋",
    parse_mode="HTML"
)

# Асинхронная отправка
await service.send_message_async(
    chat_id=123456789,
    text="Привет! 👋",
    parse_mode="HTML"
)
```

#### Отправка в группу
```python
service.send_message_to_group(
    group_chat_id="-100123456789",
    text="Сообщение для группы"
)
```

#### Управление webhook
```python
# Установка webhook
await service.set_webhook("https://your-domain.com/telegram/webhook/")

# Получение информации о webhook
webhook_info = await service.get_webhook_info()
```

## 📊 Мониторинг и логи

### BotSession модель
Отслеживает сессии пользователей в боте:
- `telegram_chat_id` - ID чата Telegram
- `user` - связанный пользователь
- `is_active` - активность сессии
- `messages_count` - количество сообщений
- `voice_messages_count` - количество голосовых
- `commands_executed` - выполненных команд

### VoiceCommandLog модель
Логирует голосовые команды:
- `user` - пользователь
- `text` - распознанный текст
- `status` - статус обработки
- `original_audio_duration` - длительность аудио
- `confidence_score` - уверенность распознавания

## 🔒 Безопасность

### JWT токены
- **Access Token:** 60 минут
- **Refresh Token:** 7 дней  
- **Автоматическая ротация** refresh токенов
- **Blacklist** после ротации

### Заголовки авторизации
```http
Authorization: Bearer <access_token>
```

### Примеры запросов с токенами
```bash
# Получение пользователей
curl -X GET \
  "http://localhost:8000/api/users/api/users/" \
  -H "Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."

# Создание транзакции
curl -X POST \
  "http://localhost:8000/api/transactions/api/transactions/" \
  -H "Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..." \
  -H "Content-Type: application/json" \
  -d '{
    "amount": "1000.00",
    "type": "expense",
    "description": "Покупка продуктов",
    "date": "2024-01-01T12:00:00Z"
  }'
```

## 🚨 Обработка ошибок

### Типичные ошибки и решения

#### 1. Webhook не отвечает
```bash
# Проверка статуса webhook
curl https://your-domain.com/telegram/webhook/
```

#### 2. Токен бота неверный
```bash
# Проверка бота
curl "https://api.telegram.org/bot8115661165:AAHWkrF_VVfppRcGjxu5ATlt0uOs5qWLJSw/getMe"
```

#### 3. Пользователь не найден
- Убедитесь что пользователь использовал `/start`
- Проверьте наличие `BotSession` для `telegram_chat_id`

#### 4. JWT токен истек
```json
{
    "detail": "Given token not valid for any token type",
    "code": "token_not_valid",
    "messages": [
        {
            "token_class": "AccessToken",
            "token_type": "access",
            "message": "Token is invalid or expired"
        }
    ]
}
```

**Решение:** Обновить токен через refresh token

## 🔄 Обновление токенов
**POST** `/api/token/refresh/`

```json
{
    "refresh": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
}
```

**Ответ:**
```json
{
    "access": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
}
``` 