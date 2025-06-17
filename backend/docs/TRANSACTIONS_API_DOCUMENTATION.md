# 💰 OvozPay Transactions API Documentation

## 🚀 Обзор

Финансовый модуль OvozPay предоставляет полный набор API для управления транзакциями, долгами и переводами с автоматическими Telegram уведомлениями.

**Base URL:** `http://localhost:8000/api/transactions/`

## 🏗 Архитектура

### Модели данных

#### Transaction
```python
class Transaction(BaseModel):
    id = UUIDField()
    user = ForeignKey(User)
    amount = DecimalField(max_digits=15, decimal_places=2)
    category = ForeignKey(Category, null=True)
    source = ForeignKey(Source, null=True)
    type = CharField(choices=['income', 'expense', 'debt', 'transfer'])
    description = TextField(blank=True)
    date = DateTimeField()
    related_user = ForeignKey(User, null=True)  # Для переводов
    is_closed = BooleanField(default=False)
    telegram_notified = BooleanField(default=False)
```

#### DebtTransaction (наследует Transaction)
```python
class DebtTransaction(Transaction):
    due_date = DateTimeField(null=True)
    paid_amount = DecimalField(default=0.00)
    status = CharField(choices=['open', 'partial', 'closed', 'overdue'])
    debtor_name = CharField(max_length=100)
    debt_direction = CharField(choices=['from_me', 'to_me'])
```

## 📡 API Endpoints

### 🏦 Транзакции (`/api/transactions/`)

#### Список транзакций
```http
GET /api/transactions/api/transactions/
Authorization: Bearer <access_token>
```

**Фильтрация:**
- `?type=income` - только доходы
- `?type=expense` - только расходы
- `?category=<uuid>` - по категории
- `?source=<uuid>` - по источнику
- `?is_closed=true` - закрытые транзакции
- `?search=описание` - поиск по описанию

**Сортировка:**
- `?ordering=-date` - по дате (убывание)
- `?ordering=amount` - по сумме (возрастание)

**Ответ:**
```json
{
    "count": 25,
    "next": "http://localhost:8000/api/transactions/api/transactions/?page=2",
    "previous": null,
    "results": [
        {
            "id": "550e8400-e29b-41d4-a716-446655440000",
            "user": "550e8400-e29b-41d4-a716-446655440001",
            "user_phone": "+998901234567",
            "amount": "50000.00",
            "category": "550e8400-e29b-41d4-a716-446655440002",
            "category_name": "Продукты",
            "source": null,
            "source_name": null,
            "type": "expense",
            "description": "Покупки в супермаркете",
            "date": "2024-01-15T14:30:00Z",
            "related_user": null,
            "related_user_phone": null,
            "is_closed": false,
            "telegram_notified": true,
            "balance_impact": "-50000.00",
            "created_at": "2024-01-15T14:30:00Z",
            "updated_at": "2024-01-15T14:30:00Z"
        }
    ]
}
```

#### Создание транзакции
```http
POST /api/transactions/api/transactions/
Authorization: Bearer <access_token>
Content-Type: application/json

{
    "amount": "75000.00",
    "type": "income",
    "description": "Зарплата",
    "category": "550e8400-e29b-41d4-a716-446655440003",
    "date": "2024-01-15T09:00:00Z"
}
```

#### Быстрое создание дохода
```http
POST /api/transactions/api/transactions/create_income/
Authorization: Bearer <access_token>
Content-Type: application/json

{
    "amount": "100000.00",
    "description": "Freelance проект",
    "category": "550e8400-e29b-41d4-a716-446655440003"
}
```

#### Быстрое создание расхода
```http
POST /api/transactions/api/transactions/create_expense/
Authorization: Bearer <access_token>
Content-Type: application/json

{
    "amount": "25000.00",
    "description": "Обед в ресторане",
    "category": "550e8400-e29b-41d4-a716-446655440004",
    "check_balance": true
}
```

#### Создание перевода
```http
POST /api/transactions/api/transactions/create_transfer/
Authorization: Bearer <access_token>
Content-Type: application/json

{
    "amount": "50000.00",
    "receiver_phone": "+998901234568",
    "description": "Возврат долга"
}
```

#### Статистика транзакций
```http
GET /api/transactions/api/transactions/stats/
Authorization: Bearer <access_token>
```

**Ответ:**
```json
{
    "total_income": "500000.00",
    "total_expense": "350000.00",
    "total_debts": "100000.00",
    "open_debts_count": 3,
    "current_balance": "150000.00",
    "transactions_count": 15
}
```

### 💳 Долги (`/api/transactions/debts/`)

#### Список долгов
```http
GET /api/transactions/api/debts/
Authorization: Bearer <access_token>
```

**Фильтрация:**
- `?status=open` - открытые долги
- `?status=closed` - закрытые долги
- `?debt_direction=from_me` - я дал в долг
- `?debt_direction=to_me` - мне дали в долг
- `?search=имя` - поиск по имени должника

**Ответ:**
```json
{
    "count": 5,
    "results": [
        {
            "id": "550e8400-e29b-41d4-a716-446655440005",
            "user": "550e8400-e29b-41d4-a716-446655440001",
            "user_phone": "+998901234567",
            "amount": "100000.00",
            "category": null,
            "category_name": null,
            "type": "debt",
            "description": "Деньги на машину",
            "date": "2024-01-10T10:00:00Z",
            "is_closed": false,
            "telegram_notified": true,
            "due_date": "2024-02-10T10:00:00Z",
            "paid_amount": "30000.00",
            "status": "partial",
            "debtor_name": "Алексей Иванов",
            "debt_direction": "from_me",
            "remaining_amount": "70000.00",
            "payment_progress": 30.0,
            "is_overdue": false,
            "created_at": "2024-01-10T10:00:00Z",
            "updated_at": "2024-01-12T15:30:00Z"
        }
    ]
}
```

#### Создание долга
```http
POST /api/transactions/api/debts/
Authorization: Bearer <access_token>
Content-Type: application/json

{
    "amount": "200000.00",
    "debtor_name": "Мария Петрова",
    "debt_direction": "to_me",
    "description": "Займ на обучение",
    "due_date": "2024-03-01T00:00:00Z"
}
```

#### Закрытие долга
```http
POST /api/transactions/api/debts/{debt_id}/close_debt/
Authorization: Bearer <access_token>
Content-Type: application/json

{
    "description": "Долг полностью погашен"
}
```

**Ответ:**
```json
{
    "message": "Долг успешно закрыт",
    "debt": {
        "id": "550e8400-e29b-41d4-a716-446655440005",
        "status": "closed",
        "is_closed": true,
        "paid_amount": "100000.00",
        "remaining_amount": "0.00",
        "payment_progress": 100.0
    }
}
```

#### Добавление частичного платежа
```http
POST /api/transactions/api/debts/{debt_id}/add_payment/
Authorization: Bearer <access_token>
Content-Type: application/json

{
    "payment_amount": "50000.00",
    "description": "Частичный возврат долга"
}
```

**Ответ:**
```json
{
    "message": "Платеж успешно добавлен",
    "is_fully_paid": false,
    "debt": {
        "id": "550e8400-e29b-41d4-a716-446655440005",
        "paid_amount": "80000.00",
        "remaining_amount": "20000.00",
        "status": "partial",
        "payment_progress": 80.0
    }
}
```

#### Просроченные долги
```http
GET /api/transactions/api/debts/overdue/
Authorization: Bearer <access_token>
```

#### Сводка по долгам
```http
GET /api/transactions/api/debts/summary/
Authorization: Bearer <access_token>
```

**Ответ:**
```json
{
    "total_debts": 10,
    "open_debts": 5,
    "closed_debts": 4,
    "overdue_debts": 1,
    "total_amount": 1000000.0,
    "total_paid": 650000.0,
    "total_remaining": 350000.0,
    "debts_from_me_count": 6,
    "debts_to_me_count": 4,
    "debts_from_me_amount": 600000.0,
    "debts_to_me_amount": 400000.0
}
```

## 🤖 Telegram Интеграция

### Автоматические уведомления

Система автоматически отправляет уведомления в Telegram при:

#### 💰 Создании дохода
```
💰 Доход получен

💵 Сумма: 75,000 UZS
📝 Описание: Зарплата
📅 Дата: 15.01.2024 09:00
💳 Баланс: 425,000 UZS
```

#### 💸 Создании расхода
```
💸 Расход создан

💸 Сумма: 25,000 UZS
📝 Описание: Обед в ресторане
📅 Дата: 15.01.2024 13:30
💳 Баланс: 400,000 UZS
```

#### 📤 Отправке перевода
```
📤 Перевод отправлен

💸 Сумма: 50,000 UZS
📝 Описание: Перевод для +998901234568
📅 Дата: 15.01.2024 16:45
```

#### 📥 Получении перевода
```
📥 Перевод получен

💰 Сумма: 50,000 UZS
📝 Описание: Перевод от +998901234567
📅 Дата: 15.01.2024 16:45
```

#### 📋 Создании долга
```
📋 Долг создан

💰 Сумма: 100,000 UZS
📝 Описание: Долг: Алексей Иванов
📅 Дата: 10.01.2024 10:00
```

#### ✅ Закрытии долга
```
✅ Долг закрыт

💰 Сумма: 100,000 UZS
📝 Описание: Долг закрыт: Алексей Иванов
📅 Дата: 20.01.2024 14:30
```

#### 💵 Частичном платеже по долгу
```
💵 Платеж по долгу

💰 Сумма: 30,000 UZS
📝 Описание: Частичная оплата долга: Алексей Иванов
📅 Дата: 12.01.2024 15:30
```

## 🛠 Бизнес-логика

### TransactionService

#### Проверка баланса
- Автоматическая проверка баланса перед созданием расходов
- Возможность принудительного создания расхода с `check_balance=false`

#### Обновление баланса
- Автоматическое обновление баланса пользователя после каждой транзакции
- Интеграция с моделью `Balance` из модуля analytics

#### Валидация переводов
- Проверка существования получателя по номеру телефона
- Запрет перевода самому себе
- Создание парных транзакций (списание у отправителя, зачисление у получателя)

#### Управление долгами
- Автоматическое обновление статуса долга при добавлении платежей
- Проверка просрочки по дате `due_date`
- Расчет прогресса выплаты в процентах

## 🔒 Безопасность

### Аутентификация
```http
Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...
```

### Авторизация
- Пользователи видят только свои транзакции и долги
- Фильтрация на уровне QuerySet по `user=request.user`

### Валидация
- Проверка положительности сумм
- Валидация дат (не в далеком будущем)
- Проверка корректности статусов и направлений долгов

## 🚨 Обработка ошибок

### Недостаточно средств
```json
{
    "error": "Недостаточно средств. Баланс: 25000.00, требуется: 50000.00"
}
```

### Пользователь не найден
```json
{
    "error": "Пользователь с таким номером не найден"
}
```

### Долг уже закрыт
```json
{
    "error": "Долг уже закрыт"
}
```

### Валидация суммы
```json
{
    "amount": ["Сумма должна быть больше нуля"]
}
```

## 📊 Примеры использования

### Создание месячной зарплаты
```bash
curl -X POST \
  "http://localhost:8000/api/transactions/api/transactions/create_income/" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "amount": "2500000.00",
    "description": "Зарплата за январь 2024",
    "category": "c1234567-1234-1234-1234-123456789abc"
  }'
```

### Покупка продуктов с проверкой баланса
```bash
curl -X POST \
  "http://localhost:8000/api/transactions/api/transactions/create_expense/" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "amount": "150000.00",
    "description": "Еженедельные продукты",
    "category": "c1234567-1234-1234-1234-123456789def",
    "check_balance": true
  }'
```

### Перевод другу
```bash
curl -X POST \
  "http://localhost:8000/api/transactions/api/transactions/create_transfer/" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "amount": "100000.00",
    "receiver_phone": "+998901234568",
    "description": "Возврат за обед"
  }'
```

### Создание долга с датой возврата
```bash
curl -X POST \
  "http://localhost:8000/api/transactions/api/debts/" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "amount": "500000.00",
    "debtor_name": "Иван Сидоров",
    "debt_direction": "from_me",
    "description": "Займ на ремонт квартиры",
    "due_date": "2024-03-15T00:00:00Z"
  }'
```

### Частичное погашение долга
```bash
curl -X POST \
  "http://localhost:8000/api/transactions/api/debts/550e8400-e29b-41d4-a716-446655440005/add_payment/" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "payment_amount": "150000.00",
    "description": "Первая часть возврата"
  }'
```

## 🔧 Настройка

### Environment Variables
```bash
# Telegram Bot Token (для уведомлений)
TELEGRAM_BOT_TOKEN=8115661165:AAHWkrF_VVfppRcGjxu5ATlt0uOs5qWLJSw

# JWT настройки
JWT_ACCESS_TOKEN_LIFETIME=60  # минуты
JWT_REFRESH_TOKEN_LIFETIME=10080  # минуты (7 дней)
```

### Django Settings
```python
# Транзакционные настройки
TRANSACTION_NOTIFICATIONS_ENABLED = True
TRANSACTION_BALANCE_CHECK_ENABLED = True
TRANSACTION_TELEGRAM_NOTIFICATIONS = True
```

## 📈 Мониторинг

### Логирование
Все операции логируются с уровнем INFO/ERROR:
```
INFO: Created income transaction 550e8400-... for user 123
INFO: Telegram notification sent for transaction 550e8400-...
ERROR: Failed to send Telegram notification for transaction 550e8400-...
```

### Метрики
- Количество созданных транзакций
- Успешность отправки Telegram уведомлений
- Количество отклоненных операций из-за недостатка средств

Финансовый модуль OvozPay готов к полноценному использованию! 🎉 