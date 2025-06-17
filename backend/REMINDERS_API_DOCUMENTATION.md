# 📑 Документация API модуля напоминаний и планировщика OvozPay

## 🎯 Этап 7: Reminders & Scheduler API

### 📋 Общее описание

Модуль напоминаний и планировщика позволяет пользователям OvozPay создавать автоматические напоминания о финансовых событиях:
- Платежах
- Долгах  
- Целях
- Произвольных событиях

Система автоматически отправляет уведомления через Telegram по расписанию с поддержкой повторных напоминаний.

---

## 🔧 Технические характеристики

- **JWT-аутентификация** на всех эндпоинтах
- **5 типов Telegram уведомлений** с HTML форматированием
- **Celery задачи** для автоматической обработки (каждые 5 минут)
- **Полная валидация** входных данных
- **Атомарность** операций с базой данных
- **Логирование** всех действий
- **Индексы** для оптимизации производительности

---

## 📊 Модели данных

### Reminder (Напоминание)
```python
{
    "id": "UUID",
    "user": "ForeignKey(User)",
    "title": "CharField(255)",
    "description": "TextField (optional)",
    "reminder_type": "choice: payment|debt|goal|custom",
    "scheduled_time": "DateTimeField",
    "repeat": "choice: once|daily|weekly|monthly",
    "is_active": "BooleanField",
    "amount": "DecimalField (optional)",
    "goal": "ForeignKey(Goal, optional)",
    "last_sent": "DateTimeField (optional)",
    "next_reminder": "DateTimeField (optional)",
    "telegram_notified": "BooleanField",
    "created_at": "DateTimeField",
    "updated_at": "DateTimeField"
}
```

### ReminderHistory (История напоминаний)
```python
{
    "id": "UUID",
    "reminder": "ForeignKey(Reminder)",
    "sent_at": "DateTimeField",
    "status": "choice: sent|failed|manual",
    "telegram_message_id": "IntegerField (optional)",
    "error_message": "TextField (optional)",
    "created_at": "DateTimeField"
}
```

---

## 🔗 API Endpoints (12 основных)

### Base URL: `/api/reminders/`

### 1. 📋 Список напоминаний пользователя
```http
GET /api/reminders/
Authorization: Bearer <token>
```

**Query параметры:**
- `reminder_type` - фильтр по типу (payment, debt, goal, custom)
- `repeat` - фильтр по периодичности (once, daily, weekly, monthly)
- `is_active` - фильтр по активности (true/false)
- `search` - поиск по названию или описанию
- `ordering` - сортировка (created_at, scheduled_time, next_reminder)
- `page` - номер страницы

**Пример ответа:**
```json
{
    "count": 15,
    "next": "http://api/reminders/?page=2",
    "previous": null,
    "results": [
        {
            "id": "550e8400-e29b-41d4-a716-446655440000",
            "title": "Оплатить интернет",
            "reminder_type": "payment",
            "reminder_type_display": "Платеж",
            "scheduled_time": "2024-06-20T12:00:00Z",
            "repeat": "monthly",
            "repeat_display": "Ежемесячно",
            "is_active": true,
            "amount": "450000.00",
            "goal_title": null,
            "next_reminder": "2024-07-20T12:00:00Z",
            "is_overdue": false,
            "is_upcoming": true,
            "created_at": "2024-06-01T10:00:00Z"
        }
    ]
}
```

---

### 2. ➕ Создать напоминание
```http
POST /api/reminders/
Authorization: Bearer <token>
Content-Type: application/json
```

**Тело запроса:**
```json
{
    "title": "Оплатить коммунальные услуги",
    "description": "Ежемесячная оплата ЖКХ",
    "reminder_type": "payment",
    "scheduled_time": "2024-06-25T09:00:00Z",
    "repeat": "monthly",
    "amount": "850000.00"
}
```

**Пример ответа:**
```json
{
    "id": "550e8400-e29b-41d4-a716-446655440001",
    "title": "Оплатить коммунальные услуги",
    "description": "Ежемесячная оплата ЖКХ",
    "reminder_type": "payment",
    "reminder_type_display": "Платеж",
    "scheduled_time": "2024-06-25T09:00:00Z",
    "repeat": "monthly",
    "repeat_display": "Ежемесячно",
    "is_active": true,
    "amount": "850000.00",
    "goal": null,
    "goal_title": null,
    "last_sent": null,
    "next_reminder": null,
    "telegram_notified": true,
    "created_at": "2024-06-20T14:30:00Z",
    "updated_at": "2024-06-20T14:30:00Z",
    "user_phone": "+998901234567",
    "is_overdue": false,
    "is_upcoming": false,
    "time_until_reminder": 432000
}
```

---

### 3. 📄 Получить детальную информацию
```http
GET /api/reminders/{id}/
Authorization: Bearer <token>
```

**Пример ответа:**
```json
{
    "id": "550e8400-e29b-41d4-a716-446655440001",
    "title": "Оплатить коммунальные услуги",
    "description": "Ежемесячная оплата ЖКХ",
    "reminder_type": "payment",
    "reminder_type_display": "Платеж",
    "scheduled_time": "2024-06-25T09:00:00Z",
    "repeat": "monthly",
    "repeat_display": "Ежемесячно",
    "is_active": true,
    "amount": "850000.00",
    "goal": null,
    "goal_title": null,
    "last_sent": null,
    "next_reminder": null,
    "telegram_notified": true,
    "created_at": "2024-06-20T14:30:00Z",
    "updated_at": "2024-06-20T14:30:00Z",
    "user_phone": "+998901234567",
    "is_overdue": false,
    "is_upcoming": false,
    "time_until_reminder": 432000
}
```

---

### 4. ✏️ Полное обновление
```http
PUT /api/reminders/{id}/
Authorization: Bearer <token>
Content-Type: application/json
```

**Тело запроса:**
```json
{
    "title": "Оплатить коммунальные услуги (обновлено)",
    "description": "Ежемесячная оплата ЖКХ - новая сумма",
    "reminder_type": "payment",
    "scheduled_time": "2024-06-25T10:00:00Z",
    "repeat": "monthly",
    "amount": "900000.00",
    "is_active": true
}
```

---

### 5. 🔧 Частичное обновление
```http
PATCH /api/reminders/{id}/
Authorization: Bearer <token>
Content-Type: application/json
```

**Тело запроса:**
```json
{
    "amount": "950000.00",
    "scheduled_time": "2024-06-25T11:00:00Z"
}
```

---

### 6. ❌ Удалить напоминание
```http
DELETE /api/reminders/{id}/
Authorization: Bearer <token>
```

**Пример ответа:**
```json
{
    "message": "Напоминание \"Оплатить коммунальные услуги\" успешно удалено"
}
```

---

### 7. ✅ Активировать напоминание
```http
POST /api/reminders/{id}/activate/
Authorization: Bearer <token>
```

**Пример ответа:**
```json
{
    "is_active": true,
    "message": "Напоминание активировано"
}
```

---

### 8. ⏹️ Деактивировать напоминание
```http
POST /api/reminders/{id}/deactivate/
Authorization: Bearer <token>
```

**Пример ответа:**
```json
{
    "is_active": false,
    "message": "Напоминание деактивировано"
}
```

---

### 9. ⏰ Ближайшие напоминания
```http
GET /api/reminders/upcoming/
Authorization: Bearer <token>
```

**Описание:** Возвращает напоминания, которые должны сработать в течение 24 часов.

**Пример ответа:**
```json
{
    "count": 3,
    "results": [
        {
            "id": "550e8400-e29b-41d4-a716-446655440002",
            "title": "Перевести деньги родителям",
            "reminder_type": "custom",
            "reminder_type_display": "Произвольное",
            "scheduled_time": "2024-06-21T15:00:00Z",
            "repeat": "weekly",
            "repeat_display": "Еженедельно",
            "is_active": true,
            "amount": null,
            "goal_title": null,
            "next_reminder": null,
            "is_overdue": false,
            "is_upcoming": true,
            "created_at": "2024-06-15T12:00:00Z"
        }
    ]
}
```

---

### 10. 📚 История выполненных напоминаний
```http
GET /api/reminders/history/
Authorization: Bearer <token>
```

**Query параметры:**
- `status` - фильтр по статусу (sent, failed, manual)
- `reminder__reminder_type` - фильтр по типу напоминания
- `ordering` - сортировка (sent_at, created_at)
- `page` - номер страницы

**Пример ответа:**
```json
{
    "count": 25,
    "next": "http://api/reminders/history/?page=2",
    "previous": null,
    "results": [
        {
            "id": "550e8400-e29b-41d4-a716-446655440010",
            "reminder": "550e8400-e29b-41d4-a716-446655440001",
            "reminder_title": "Оплатить интернет",
            "reminder_type": "payment",
            "sent_at": "2024-06-20T12:00:05Z",
            "status": "sent",
            "status_display": "Отправлено",
            "telegram_message_id": 12345,
            "error_message": null,
            "user_phone": "+998901234567",
            "created_at": "2024-06-20T12:00:05Z"
        }
    ]
}
```

---

### 11. 🚀 Отправить уведомление вручную
```http
POST /api/reminders/{id}/send-now/
Authorization: Bearer <token>
```

**Пример ответа:**
```json
{
    "message": "Напоминание \"Оплатить интернет\" отправлено",
    "sent_at": "2024-06-20T16:30:00Z",
    "telegram_message_id": 12346
}
```

---

### 12. 📝 Список доступных типов
```http
GET /api/reminders/types/
Authorization: Bearer <token>
```

**Пример ответа:**
```json
{
    "reminder_types": [
        {"value": "payment", "label": "Платеж"},
        {"value": "debt", "label": "Долг"},
        {"value": "goal", "label": "Цель"},
        {"value": "custom", "label": "Произвольное"}
    ],
    "repeat_types": [
        {"value": "once", "label": "Однократно"},
        {"value": "daily", "label": "Ежедневно"},
        {"value": "weekly", "label": "Еженедельно"},
        {"value": "monthly", "label": "Ежемесячно"}
    ]
}
```

---

## 📊 Дополнительные эндпоинты

### Статистика напоминаний
```http
GET /api/reminders/stats/
Authorization: Bearer <token>
```

**Пример ответа:**
```json
{
    "total_reminders": 25,
    "active_reminders": 18,
    "inactive_reminders": 7,
    "overdue_reminders": 2,
    "upcoming_reminders": 5,
    "payment_reminders": 8,
    "debt_reminders": 3,
    "goal_reminders": 6,
    "custom_reminders": 8,
    "once_reminders": 5,
    "daily_reminders": 3,
    "weekly_reminders": 7,
    "monthly_reminders": 10,
    "total_sent": 145,
    "sent_today": 8,
    "sent_this_week": 22,
    "sent_this_month": 85
}
```

### Просроченные напоминания
```http
GET /api/reminders/overdue/
Authorization: Bearer <token>
```

### Обработать запланированные (админ)
```http
POST /api/reminders/process-scheduled/
Authorization: Bearer <admin_token>
```

---

## 🤖 Telegram уведомления (5 типов)

### 1. 🔔 Создание напоминания
```html
<b>🔔 Создано новое напоминание!</b>

📝 <b>Событие:</b> Оплатить интернет
📅 <b>Дата:</b> 20.06.2024 12:00
🔄 <b>Повтор:</b> ежемесячно
📱 <b>Тип:</b> Платеж
💰 <b>Сумма:</b> 450,000 UZS

✅ Напоминание активировано и будет отправлено в указанное время!
```

### 2. 💵 Напоминание о платеже
```html
<b>💵 Напоминание о платеже!</b>

📝 <b>Событие:</b> Оплатить интернет
📅 <b>Дата:</b> 20.06.2024 12:00
💰 <b>Сумма:</b> 450,000 UZS
📋 <b>Описание:</b> Ежемесячная оплата через Click

⏰ Время пришло! Не забудьте совершить платеж.
```

### 3. 📋 Напоминание о долге
```html
<b>📋 Напоминание о долге!</b>

📝 <b>Событие:</b> Вернуть долг Ахмаду
📅 <b>Дата:</b> 22.06.2024 18:00
💰 <b>Сумма:</b> 2,500,000 UZS
📋 <b>Описание:</b> Одолжил на ремонт

⚠️ Не забудьте погасить долг вовремя!
```

### 4. 🎯 Напоминание о цели
```html
<b>🎯 Напоминание о цели!</b>

📝 <b>Событие:</b> Пополнить накопления на отпуск
📅 <b>Дата:</b> 25.06.2024 20:00
🎯 <b>Цель:</b> Поездка в Турцию
📊 <b>Прогресс:</b> 65.5%
💰 <b>Осталось:</b> 3,450,000 UZS

🚀 Продолжайте работать над достижением цели!
```

### 5. 📝 Кастомное напоминание
```html
<b>📝 Кастомное напоминание!</b>

📝 <b>Событие:</b> Купить подарок маме
📅 <b>Дата:</b> 30.06.2024 14:00
📋 <b>Описание:</b> День рождения 5 июля
💰 <b>Сумма:</b> 1,000,000 UZS

🔔 Время выполнить запланированное действие!
```

---

## ⚙️ Celery задачи

### Основные задачи

#### 1. `send_scheduled_reminders`
- **Частота:** каждые 5 минут
- **Функция:** обработка запланированных напоминаний
- **Retry:** 3 попытки с экспоненциальной задержкой

#### 2. `repeat_reminders`
- **Частота:** каждые 5 минут
- **Функция:** обновление времени следующего напоминания для повторных

#### 3. `send_single_reminder`
- **Тип:** по требованию
- **Функция:** отправка конкретного напоминания
- **Retry:** 2 попытки

### Вспомогательные задачи

#### 4. `cleanup_old_reminder_history`
- **Частота:** ежедневно в 2:00
- **Функция:** удаление истории старше 6 месяцев

#### 5. `deactivate_expired_reminders`
- **Частота:** ежедневно в 1:00
- **Функция:** деактивация просроченных одноразовых напоминаний

#### 6. `generate_reminder_stats`
- **Частота:** ежедневно в 23:00
- **Функция:** генерация ежедневной статистики

---

## 🔐 Безопасность

### Аутентификация
- **JWT токены** на всех эндпоинтах
- **Изоляция данных** - пользователи видят только свои напоминания
- **Валидация ownership** - проверка принадлежности целей пользователю

### Валидация
- **Время в будущем** для новых напоминаний
- **Положительные суммы** для платежей и долгов
- **Обязательные поля** в зависимости от типа
- **Кросс-валидация** связанных полей

---

## 📈 Производительность

### Индексы базы данных
```sql
-- Для поиска напоминаний пользователя
CREATE INDEX reminders_user_active_idx ON reminders (user_id, is_active);

-- Для планировщика
CREATE INDEX reminders_scheduled_active_idx ON reminders (scheduled_time, is_active);
CREATE INDEX reminders_next_active_idx ON reminders (next_reminder, is_active);

-- Для фильтрации
CREATE INDEX reminders_type_idx ON reminders (reminder_type);
CREATE INDEX reminders_repeat_idx ON reminders (repeat);

-- Для истории
CREATE INDEX history_reminder_sent_idx ON reminder_history (reminder_id, sent_at);
CREATE INDEX history_status_idx ON reminder_history (status);
```

### Оптимизации
- **select_related** для связанных объектов
- **Пагинация** для больших наборов данных
- **Фильтрация на уровне БД** для минимизации объема данных
- **Атомарные операции** для целостности данных

---

## 🧪 Примеры использования

### Создание платежного напоминания
```bash
curl -X POST http://localhost:8000/api/reminders/ \
  -H "Authorization: Bearer your_jwt_token" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Оплатить мобильную связь",
    "reminder_type": "payment",
    "scheduled_time": "2024-07-01T10:00:00Z",
    "repeat": "monthly",
    "amount": "150000.00",
    "description": "Ucell тариф Business"
  }'
```

### Создание напоминания о цели
```bash
curl -X POST http://localhost:8000/api/reminders/ \
  -H "Authorization: Bearer your_jwt_token" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Пополнить накопления на машину",
    "reminder_type": "goal",
    "scheduled_time": "2024-06-30T20:00:00Z",
    "repeat": "weekly",
    "goal": "550e8400-e29b-41d4-a716-446655440000",
    "description": "Еженедельное пополнение цели"
  }'
```

### Получение ближайших напоминаний
```bash
curl -X GET "http://localhost:8000/api/reminders/upcoming/" \
  -H "Authorization: Bearer your_jwt_token"
```

### Отправка напоминания вручную
```bash
curl -X POST "http://localhost:8000/api/reminders/550e8400-e29b-41d4-a716-446655440001/send-now/" \
  -H "Authorization: Bearer your_jwt_token"
```

---

## ❌ Коды ошибок

### 400 Bad Request
```json
{
    "error": "Ошибка валидации",
    "details": {
        "scheduled_time": ["Время напоминания не может быть в прошлом"],
        "amount": ["Для напоминания о платеже необходимо указать сумму"]
    }
}
```

### 401 Unauthorized
```json
{
    "detail": "Authentication credentials were not provided."
}
```

### 403 Forbidden
```json
{
    "error": "Недостаточно прав доступа"
}
```

### 404 Not Found
```json
{
    "detail": "Not found."
}
```

---

## ✅ Статус готовности

### ✅ Выполненные требования ТЗ:
- [x] 12 основных API эндпоинтов
- [x] 5 типов Telegram уведомлений
- [x] Celery задачи (каждые 5 минут)
- [x] JWT аутентификация
- [x] Полная валидация данных
- [x] Фильтрация и сортировка
- [x] Атомарность операций
- [x] Логирование уведомлений
- [x] Индексы для производительности
- [x] Swagger документация
- [x] Миграции применены
- [x] System check пройден

### 🚀 Дополнительные возможности:
- [x] История напоминаний с детальной статистикой
- [x] Просроченные напоминания
- [x] Административные функции
- [x] Автоматическая очистка старых данных
- [x] Детальная статистика пользователя
- [x] Вычисляемые поля (is_overdue, time_until_reminder)
- [x] Богатое HTML форматирование в Telegram

---

## 📞 Поддержка

Для вопросов по API модуля напоминаний обращайтесь:
- **Email:** admin@ovozpay.uz
- **Документация:** `/swagger/` или `/redoc/`
- **Тестирование:** Все эндпоинты доступны через Swagger UI

**Модуль готов к продакшен использованию! 🎉** 