# 🤖 Документация API Telegram Бота OvozPay

## 📋 Обзор

Telegram бот OvozPay предоставляет голосовой интерфейс для управления личными финансами. Пользователи могут записывать доходы и расходы через голосовые сообщения, просматривать баланс и управлять финансовыми данными.

## 🔗 Базовые URL

- **Webhook URL**: `https://your-domain.com/telegram/webhook/`
- **Auth API**: `https://your-domain.com/api/users/auth/`

## 🔐 Аутентификация

### POST `/api/users/auth/telegram-login/`

Аутентификация пользователя по Telegram Chat ID

**Запрос:**
```json
{
  "telegram_chat_id": 123456789,
  "phone_number": "+998901234567"  // опционально
}
```

**Ответ (200 OK):**
```json
{
  "access": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "refresh": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "user_id": "550e8400-e29b-41d4-a716-446655440000",
  "phone_number": "+998901234567",
  "is_new_user": true
}
```

**Ошибки:**
- `400 Bad Request` - Неверные данные
- `500 Internal Server Error` - Ошибка сервера

### POST `/api/users/auth/refresh-token/`

Обновление access токена

**Запрос:**
```json
{
  "refresh": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
}
```

**Ответ (200 OK):**
```json
{
  "access": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
}
```

## 🔄 Webhook

### POST `/telegram/webhook/`

Endpoint для получения обновлений от Telegram Bot API

**Headers:**
- `Content-Type: application/json`

**Тело запроса** - стандартный Update объект от Telegram Bot API

**Пример обновления с сообщением:**
```json
{
  "update_id": 123456789,
  "message": {
    "message_id": 123,
    "from": {
      "id": 123456789,
      "is_bot": false,
      "first_name": "John",
      "username": "john_doe"
    },
    "chat": {
      "id": 123456789,
      "first_name": "John",
      "username": "john_doe",
      "type": "private"
    },
    "date": 1640995200,
    "text": "/start"
  }
}
```

**Ответы:**
- `200 OK` - Обновление успешно обработано
- `400 Bad Request` - Ошибка парсинга JSON
- `405 Method Not Allowed` - Неподдерживаемый HTTP метод
- `500 Internal Server Error` - Ошибка обработки

## 🎮 Команды бота

### `/start`
**Описание**: Регистрация пользователя и приветствие

**Действия**:
- Создает нового пользователя или находит существующего
- Создает активную сессию
- Отправляет приветственное сообщение

**Пример ответа**:
```
🎉 Добро пожаловать в OvozPay!

Я ваш голосовой помощник по управлению финансами.

📱 Для полноценной работы, пожалуйста, укажите свой номер телефона:
/phone +998901234567

💡 Что я умею:
• 🎙 Обрабатывать голосовые команды
• 💰 Записывать доходы и расходы
• 📊 Показывать баланс и статистику
• 🎯 Помогать с целями

Используйте /help для списка всех команд.
```

### `/balance`
**Описание**: Показывает текущий баланс пользователя

**Требования**: Пользователь должен быть зарегистрирован

**Пример ответа**:
```
💰 Ваш баланс

💵 Доходы: 1,500,000.00 UZS
💸 Расходы: 800,000.00 UZS
📊 Итого: 700,000.00 UZS

📅 На 15.12.2023 14:30

📝 Последние операции:
💸 50,000.00 UZS - Продукты в магазине
💰 200,000.00 UZS - Зарплата
💸 25,000.00 UZS - Транспорт
```

### `/help`
**Описание**: Показывает справку по командам

**Пример ответа**:
```
🤖 OvozPay - Справка по командам

📋 Основные команды:
/start - Начать работу с ботом
/balance - Показать текущий баланс
/help - Показать эту справку
/phone +номер - Обновить номер телефона

🎙 Голосовые команды:
• Отправьте голосовое сообщение с описанием траты
• Пример: "Потратил 50000 сум на продукты"
• Пример: "Заработал 500 долларов"

💡 Советы:
• Говорите четко и указывайте сумму
• Можете использовать разные валюты
• Бот автоматически определит тип операции

❓ Вопросы? Напишите @support
```

### `/phone +номер`
**Описание**: Обновляет номер телефона пользователя

**Параметры**: Номер телефона в международном формате

**Примеры**:
- `/phone +998901234567`
- `/phone +79001234567`

**Ответы**:
- Успех: `✅ Номер телефона обновлен: +998901234567`
- Ошибка: `❌ Укажите номер телефона.\nПример: /phone +998901234567`

## 🎙 Голосовые сообщения

**Поддержка**: В разработке

**Текущее поведение**: Бот получает голосовые сообщения и отправляет информацию о них:

```
🎙 Получено голосовое сообщение!

⏱ Длительность: 5 сек.
📁 Размер: 24576 байт

🔄 Функция распознавания речи будет добавлена в следующих обновлениях.
📝 Пока используйте текстовые команды для управления финансами.
```

## 🔧 Настройка Webhook

### Установка Webhook

**URL**: `https://api.telegram.org/bot<TOKEN>/setWebhook`

**Параметры**:
```json
{
  "url": "https://your-domain.com/telegram/webhook/",
  "allowed_updates": ["message", "callback_query"]
}
```

### Проверка Webhook

**URL**: `https://api.telegram.org/bot<TOKEN>/getWebhookInfo`

**Ответ**:
```json
{
  "ok": true,
  "result": {
    "url": "https://your-domain.com/telegram/webhook/",
    "has_custom_certificate": false,
    "pending_update_count": 0,
    "allowed_updates": ["message", "callback_query"]
  }
}
```

### Удаление Webhook

**URL**: `https://api.telegram.org/bot<TOKEN>/deleteWebhook`

## 📊 Логирование

Все взаимодействия с ботом логируются:

**Уровни логирования**:
- `INFO`: Успешные операции
- `WARNING`: Предупреждения (неверные токены и т.д.)
- `ERROR`: Ошибки обработки

**Примеры логов**:
```
INFO: Обработана команда /start для пользователя 123456789
INFO: Telegram аутентификация: chat_id=123456789, user_id=550e8400-e29b-41d4-a716-446655440000, new_user=True
ERROR: Ошибка обработки webhook: Connection timeout
```

## 🔒 Безопасность

### JWT Токены

**Access Token**:
- Время жизни: 60 минут
- Используется для авторизации API запросов

**Refresh Token**:
- Время жизни: 7 дней
- Используется для обновления access токенов
- Ротируется при каждом обновлении

### Валидация данных

- Все входящие данные валидируются
- Telegram Chat ID должен быть положительным числом
- Номера телефонов должны начинаться с "+"

## 🚀 Развертывание

### Переменные окружения

```env
TELEGRAM_BOT_TOKEN=8115661165:AAHWkrF_VVfppRcGjxu5ATlt0uOs5qWLJSw
TELEGRAM_WEBHOOK_URL=https://your-domain.com/telegram/webhook/
SECRET_KEY=your-django-secret-key
DEBUG=False
```

### Требования

- Python 3.8+
- Django 5.0+
- aiohttp 3.9+
- aiogram 3.4+ (для расширенной функциональности)
- djangorestframework-simplejwt 5.3+

### Установка зависимостей

```bash
pip install -r requirements.txt
```

### Применение миграций

```bash
python manage.py makemigrations
python manage.py migrate
```

### Установка webhook

```bash
curl -X POST https://api.telegram.org/bot<TOKEN>/setWebhook \
  -H "Content-Type: application/json" \
  -d '{"url": "https://your-domain.com/telegram/webhook/"}'
```

## 🧪 Тестирование

### Тестирование webhook локально с ngrok

1. Установите ngrok:
```bash
npm install -g ngrok
```

2. Запустите Django сервер:
```bash
python manage.py runserver 8000
```

3. Создайте туннель:
```bash
ngrok http 8000
```

4. Установите webhook:
```bash
curl -X POST https://api.telegram.org/bot<TOKEN>/setWebhook \
  -H "Content-Type: application/json" \
  -d '{"url": "https://abc123.ngrok.io/telegram/webhook/"}'
```

### Тестирование команд

1. Найдите бота в Telegram: `@your_bot_name`
2. Отправьте `/start`
3. Проверьте авторизацию через API
4. Протестируйте все команды

## 📝 Примеры использования

### Получение токена для клиента

```python
import requests

response = requests.post(
    'https://your-domain.com/api/users/auth/telegram-login/',
    json={
        'telegram_chat_id': 123456789,
        'phone_number': '+998901234567'
    }
)

data = response.json()
access_token = data['access']
```

### Использование токена для API запросов

```python
headers = {
    'Authorization': f'Bearer {access_token}',
    'Content-Type': 'application/json'
}

response = requests.get(
    'https://your-domain.com/api/transactions/',
    headers=headers
)
```

## 🐛 Troubleshooting

### Проблема: Webhook не получает обновления

**Решение**:
1. Проверьте URL webhook
2. Убедитесь что сервер доступен по HTTPS
3. Проверьте логи Django

### Проблема: Ошибка 401 при API запросах

**Решение**:
1. Проверьте токен в заголовке Authorization
2. Убедитесь что токен не истек
3. Обновите токен через refresh endpoint

### Проблема: Бот не отвечает на команды

**Решение**:
1. Проверьте что webhook установлен
2. Проверьте логи обработки сообщений
3. Убедитесь что команды правильно маршрутизируются

## 📞 Поддержка

- Email: admin@ovozpay.uz
- Telegram: @ovozpay_support
- GitHub Issues: [ссылка на репозиторий]

---

*Документация актуальна на: 15.12.2023* 