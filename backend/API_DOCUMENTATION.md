# 📑 OvozPay API Documentation

## 🚀 Базовая информация

**Сервер разработки:** http://localhost:8000  
**Swagger UI:** http://localhost:8000/swagger/  
**ReDoc:** http://localhost:8000/redoc/  

## 🔗 API Endpoints

### 👤 Users API (`/api/users/`)
- **GET/POST** `/api/users/api/users/` - Список и создание пользователей
- **GET/PUT/DELETE** `/api/users/api/users/{id}/` - Детали пользователя
- **POST** `/api/users/api/users/{id}/activate/` - Активация пользователя
- **POST** `/api/users/api/users/{id}/deactivate/` - Деактивация пользователя
- **GET/POST** `/api/users/api/referrals/` - Рефералы
- **GET/POST** `/api/users/api/user-settings/` - Настройки пользователей

### 💰 Transactions API (`/api/transactions/`)
- **GET/POST** `/api/transactions/api/transactions/` - Транзакции
- **GET** `/api/transactions/api/transactions/statistics/` - Статистика транзакций
- **GET/POST** `/api/transactions/api/debts/` - Долги
- **POST** `/api/transactions/api/debts/{id}/close_debt/` - Закрытие долга
- **GET** `/api/transactions/api/debts/overdue/` - Просроченные долги

### 📂 Categories API (`/api/categories/`)
- **GET/POST** `/api/categories/api/categories/` - Категории
- **POST** `/api/categories/api/categories/create_defaults/` - Создание дефолтных категорий
- **GET** `/api/categories/api/categories/defaults/` - Системные категории

### 🎯 Goals API (`/api/goals/`)
- **GET/POST** `/api/goals/api/goals/` - Цели
- **POST** `/api/goals/api/goals/{id}/add_progress/` - Добавить прогресс к цели
- **POST** `/api/goals/api/goals/{id}/complete/` - Завершить цель
- **POST** `/api/goals/api/goals/{id}/reset/` - Сбросить прогресс цели
- **GET** `/api/goals/api/goals/overdue/` - Просроченные цели

### 📊 Analytics API (`/api/analytics/`)
- **GET/POST** `/api/analytics/api/reports/` - Отчеты
- **POST** `/api/analytics/api/reports/generate/` - Генерация отчета
- **GET/POST** `/api/analytics/api/balances/` - Балансы
- **POST** `/api/analytics/api/balances/{id}/update_balance/` - Обновление баланса
- **POST** `/api/analytics/api/balances/get_or_create/` - Получить или создать баланс

### 🔗 Sources API (`/api/sources/`)
- **GET/POST** `/api/sources/api/sources/` - Источники трафика
- **POST** `/api/sources/api/sources/create_defaults/` - Создание дефолтных источников

### 📢 Broadcast API (`/api/broadcast/`)
- **GET/POST** `/api/broadcast/api/messages/` - Рассылки
- **POST** `/api/broadcast/api/messages/{id}/schedule/` - Планирование рассылки
- **POST** `/api/broadcast/api/messages/{id}/start_sending/` - Запуск рассылки
- **GET** `/api/broadcast/api/logs/` - Логи рассылок

### 🤖 Bot API (`/api/bot/`)
- **GET/POST** `/api/bot/api/voice-commands/` - Голосовые команды
- **GET** `/api/bot/api/voice-commands/user_stats/` - Статистика пользователя
- **GET/POST** `/api/bot/api/sessions/` - Сессии бота
- **POST** `/api/bot/api/sessions/{id}/end_session/` - Завершение сессии
- **POST** `/api/bot/api/sessions/end_inactive/` - Завершение неактивных сессий

## 🔍 Фильтрация и поиск

Все эндпоинты поддерживают:
- **Фильтрация:** `?field=value`
- **Поиск:** `?search=query`
- **Сортировка:** `?ordering=field` или `?ordering=-field`
- **Пагинация:** `?page=1&page_size=10`

## 🔐 Аутентификация

По умолчанию используется Session Authentication.  
Для тестирования в Swagger:
1. Перейдите в админку `/admin/`
2. Войдите под admin/admin123
3. Вернитесь в Swagger

## ⚡ Примеры запросов

### Создание пользователя
```json
POST /api/users/api/users/
{
    "phone_number": "+998901234567",
    "language": "ru"
}
```

### Создание транзакции
```json
POST /api/transactions/api/transactions/
{
    "user": "user_uuid",
    "amount": "1000.00",
    "type": "expense",
    "description": "Покупка продуктов",
    "date": "2024-01-01T12:00:00Z"
}
```

### Создание цели
```json
POST /api/goals/api/goals/
{
    "user": "user_uuid",
    "title": "Новый телефон",
    "target_amount": "500000.00",
    "deadline": "2024-12-31"
}
```

## 📝 Валидация

- Все суммы должны быть > 0
- Номера телефонов должны начинаться с +
- UUID поля отображаются как строки
- Даты в формате ISO 8601

## 🔧 Настройки DRF

- Пагинация: 10 элементов на страницу
- Фильтрация через django-filter
- Поиск и сортировка включены
- CORS разрешен для всех источников (только для разработки) 