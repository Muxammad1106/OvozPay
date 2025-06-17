# 📖 Goals & Savings API — Документация

## 🎯 Обзор модуля

**Модуль целей и накоплений** позволяет пользователям:
- Создавать финансовые цели с конкретными суммами и сроками
- Откладывать средства на достижение целей
- Отслеживать прогресс накоплений  
- Получать Telegram уведомления о статусе целей
- Управлять статусами целей (активные, завершенные, проваленные, приостановленные)

---

## 🗄 Модели данных

### Goal (Цель)

Основная модель для финансовых целей пользователя.

| Поле | Тип | Описание |
|------|-----|----------|
| `id` | UUID | Уникальный идентификатор |
| `user` | ForeignKey | Владелец цели |
| `title` | CharField(200) | Название цели |
| `description` | TextField | Описание цели (опционально) |
| `target_amount` | Decimal | Целевая сумма |
| `current_amount` | Decimal | Текущая накопленная сумма |
| `deadline` | Date | Срок достижения цели |
| `status` | CharField | Статус: active, completed, failed, paused |
| `reminder_interval` | CharField | Интервал напоминаний: daily, weekly, monthly, never |
| `last_reminder_sent` | DateTime | Последнее отправленное напоминание |
| `telegram_notified` | Boolean | Отправлено ли Telegram уведомление |
| `created_at` | DateTime | Дата создания |
| `updated_at` | DateTime | Дата последнего обновления |

**Вычисляемые свойства:**
- `progress_percentage` — процент выполнения (0-100%)
- `remaining_amount` — оставшаяся сумма до цели
- `is_overdue` — просрочена ли цель
- `is_completed` — завершена ли цель
- `is_active` — активна ли цель
- `days_left` — дней до дедлайна

### GoalTransaction (Транзакция цели)

Модель для отслеживания пополнений целей.

| Поле | Тип | Описание |
|------|-----|----------|
| `id` | UUID | Уникальный идентификатор |
| `goal` | ForeignKey | Связанная цель |
| `amount` | Decimal | Сумма пополнения |
| `description` | CharField(500) | Описание операции |
| `telegram_notified` | Boolean | Отправлено ли уведомление |
| `created_at` | DateTime | Дата операции |

---

## 🚀 API Endpoints

### 🎯 Goals Management

#### **GET** `/api/goals/api/goals/`
Получить список целей пользователя

**Параметры запроса:**
- `status` — фильтр по статусу (active, completed, failed, paused)
- `reminder_interval` — фильтр по интервалу напоминаний
- `is_overdue` — только просроченные цели (true/false)
- `is_completed` — только завершенные цели (true/false)
- `is_active` — только активные цели (true/false)
- `search` — поиск по названию и описанию
- `ordering` — сортировка (created_at, deadline, target_amount, current_amount)

**Пример ответа:**
```json
{
  "count": 5,
  "next": null,
  "previous": null,
  "results": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "user": 1,
      "user_phone": "+998901234567",
      "title": "Новый iPhone",
      "description": "Накопления на iPhone 15 Pro",
      "target_amount": "15000000.00",
      "current_amount": "3500000.00",
      "deadline": "2024-12-31",
      "status": "active",
      "reminder_interval": "weekly",
      "progress_percentage": 23.3,
      "remaining_amount": "11500000.00",
      "is_overdue": false,
      "is_completed": false,
      "is_active": true,
      "days_left": 145,
      "transactions_count": 7,
      "created_at": "2024-01-15T10:00:00Z",
      "updated_at": "2024-01-20T14:30:00Z"
    }
  ]
}
```

#### **POST** `/api/goals/api/goals/`
Создать новую цель

**Тело запроса:**
```json
{
  "title": "Отпуск в Турции",
  "description": "Накопления на семейный отпуск",
  "target_amount": "8000000.00",
  "deadline": "2024-07-01",
  "reminder_interval": "weekly"
}
```

**Ответ:** `201 Created` + данные созданной цели + Telegram уведомление

#### **GET** `/api/goals/api/goals/{id}/`
Получить детали конкретной цели

#### **PUT** `/api/goals/api/goals/{id}/`
Обновить цель

#### **DELETE** `/api/goals/api/goals/{id}/`
Удалить цель

---

### ⚡ Custom Actions для целей

#### **POST** `/api/goals/api/goals/{id}/add_progress/`
Добавить прогресс к цели

**Тело запроса:**
```json
{
  "amount": "500000.00",
  "description": "Пополнение от зарплаты",
  "withdraw_from_balance": true
}
```

**Ответ:**
```json
{
  "goal": { /* обновленные данные цели */ },
  "transaction": { /* данные созданной транзакции */ },
  "message": "Прогресс успешно добавлен"
}
```

**Логика:**
- Проверка баланса пользователя (если `withdraw_from_balance=true`)
- Создание GoalTransaction
- Списание с баланса через TransactionService
- Обновление current_amount цели
- Автоматическое завершение цели при достижении target_amount
- Отправка Telegram уведомлений

#### **POST** `/api/goals/api/goals/{id}/complete_goal/`
Завершить цель досрочно

**Тело запроса:**
```json
{
  "force": false,
  "reason": "Нашел более выгодное предложение"
}
```

#### **POST** `/api/goals/api/goals/{id}/update_status/`
Обновить статус цели

**Тело запроса:**
```json
{
  "status": "paused",
  "reason": "Временные финансовые трудности"
}
```

**Возможные переходы статусов:**
- `active` → `completed`, `failed`, `paused`
- `paused` → `active`, `failed`
- `failed` → `active`
- `completed` → нельзя изменить

#### **GET** `/api/goals/api/goals/stats/`
Получить статистику целей пользователя

**Ответ:**
```json
{
  "total_goals": 12,
  "active_goals": 4,
  "completed_goals": 6,
  "failed_goals": 1,
  "paused_goals": 1,
  "overdue_goals_count": 2,
  "total_target_amount": "45000000.00",
  "total_saved_amount": "28500000.00",
  "average_progress_percentage": 63.3,
  "this_month_saved": "2500000.00",
  "this_year_saved": "15800000.00",
  "recent_goals": [/* последние 5 целей */]
}
```

#### **GET** `/api/goals/api/goals/overdue/`
Получить просроченные цели

#### **POST** `/api/goals/api/goals/check_overdue/`
Проверить и обновить просроченные цели (admin функция)

---

### 💳 Goal Transactions Management

#### **GET** `/api/goals/api/goal-transactions/`
Получить список транзакций по целям

**Параметры запроса:**
- `goal` — фильтр по ID цели
- `goal_id` — фильтр по ID цели  
- `telegram_notified` — фильтр по статусу уведомления
- `date_from` — транзакции с даты
- `date_to` — транзакции до даты
- `search` — поиск по описанию и названию цели

**Пример ответа:**
```json
{
  "count": 15,
  "results": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440001",
      "goal": "550e8400-e29b-41d4-a716-446655440000",
      "goal_title": "Новый iPhone",
      "user_phone": "+998901234567",
      "amount": "500000.00",
      "description": "Пополнение от зарплаты",
      "telegram_notified": true,
      "created_at": "2024-01-20T14:30:00Z"
    }
  ]
}
```

#### **POST** `/api/goals/api/goal-transactions/`
Создать новую транзакцию пополнения

**Тело запроса:**
```json
{
  "goal": "550e8400-e29b-41d4-a716-446655440000",
  "amount": "300000.00",
  "description": "Пополнение с карты",
  "withdraw_from_balance": true
}
```

#### **GET** `/api/goals/api/goal-transactions/summary/`
Получить сводку по транзакциям

**Ответ:**
```json
{
  "total_transactions": 45,
  "total_amount": "15800000.00",
  "this_month_transactions": 8,
  "this_month_amount": "2400000.00",
  "top_goals": [
    {
      "goal__title": "Новый iPhone",
      "goal__id": "550e8400-e29b-41d4-a716-446655440000",
      "transaction_count": 12,
      "total_amount": "4500000.00"
    }
  ]
}
```

---

## 🤖 Telegram Интеграция

### Типы уведомлений

#### 1. 🎯 Создание цели
```
🎯 Новая цель создана!

📝 Название: Новый iPhone
💰 Целевая сумма: 15,000,000 UZS
📅 Срок: 31.12.2024
📊 Прогресс: 0% (0 / 15,000,000 UZS)
⏰ Дней осталось: 145

💪 Начинайте откладывать средства для достижения цели!
```

#### 2. 💵 Пополнение цели
```
💵 Цель пополнена!

🎯 Цель: Новый iPhone
➕ Пополнено: 500,000 UZS
💰 Накоплено: 3,500,000 UZS
🎯 Цель: 15,000,000 UZS
📊 Прогресс: 23.3%
📈 Осталось: 11,500,000 UZS
📅 До срока: 145 дней

💪 Продолжайте в том же духе!
```

#### 3. 🎉 Завершение цели
```
🎉 Цель достигнута!

🎯 Цель: Новый iPhone
💰 Сумма: 15,000,000 UZS
📅 Завершено: 20.01.2024 14:30
⏱ Потребовалось дней: 67

🏆 Поздравляем с достижением цели! Вы большой молодец!
```

#### 4. 😔 Провал цели
```
😔 Цель не достигнута

🎯 Цель: Новый iPhone
💰 Целевая сумма: 15,000,000 UZS
💵 Накоплено: 3,500,000 UZS
📊 Прогресс: 23.3%
📅 Срок истек: 31.12.2024

💪 Не расстраивайтесь! Создайте новую цель и попробуйте снова!

📝 Причина: Истек срок достижения цели
```

#### 5. ⏰ Напоминание о цели
```
⏰ Напоминание о цели

🎯 Цель: Новый iPhone
💰 Накоплено: 3,500,000 UZS
🎯 Цель: 15,000,000 UZS
📊 Прогресс: 23.3%
📈 Осталось: 11,500,000 UZS
📅 До срока: 145 дней

💡 Не забывайте откладывать средства для достижения цели!
```

---

## 🔧 Бизнес-логика (GoalService)

### Основные методы сервиса

#### `create_goal(user, title, target_amount, deadline, ...)`
- Создает новую цель
- Отправляет Telegram уведомление о создании
- Возвращает созданную цель

#### `add_progress_to_goal(goal, amount, description, withdraw_from_balance)`
- Проверяет баланс пользователя (если withdraw_from_balance=True)
- Создает GoalTransaction
- Обновляет current_amount цели
- Списывает средства с баланса через TransactionService
- Автоматически завершает цель при достижении target_amount
- Отправляет Telegram уведомления

#### `complete_goal(goal, force=False, reason="")`
- Завершает цель принудительно или по достижению суммы
- Отправляет уведомление о завершении

#### `fail_goal(goal, reason="")`
- Отмечает цель как проваленную
- Отправляет уведомление о провале

#### `get_user_goals_stats(user)`
- Возвращает полную статистику целей пользователя
- Включает финансовую статистику и данные за периоды

#### `check_and_update_overdue_goals()`
- Автоматически проваливает просроченные цели
- Отправляет уведомления о провале

#### `send_goal_reminders()`
- Отправляет напоминания по интервалам (daily, weekly, monthly)
- Обновляет last_reminder_sent

---

## 🔒 Безопасность и валидация

### Аутентификация
- Все endpoints требуют JWT токен
- Пользователи видят только свои цели и транзакции

### Валидация данных

#### Goal валидация:
- `target_amount` > 0 и ≤ 999,999,999,999.99
- `deadline` в будущем
- `title` длиной 3-200 символов
- `description` ≤ 1000 символов
- `current_amount` ≤ `target_amount`

#### GoalTransaction валидация:
- `amount` > 0 и ≤ 999,999,999,999.99
- Цель должна быть активной
- Транзакция не должна превышать remaining_amount
- Пользователь может пополнять только свои цели

### Бизнес-правила

#### Статусы целей:
- **active** — цель активна, можно пополнять
- **completed** — цель достигнута, пополнение запрещено
- **failed** — цель провалена, пополнение запрещено
- **paused** — цель приостановлена, пополнение запрещено

#### Автоматические действия:
- Просроченные active цели автоматически становятся failed
- При достижении target_amount цель становится completed
- При превышении суммы current_amount = target_amount

---

## 📊 Примеры использования

### Создание цели и пополнение

```bash
# 1. Создание цели
curl -X POST "http://localhost:8000/api/goals/api/goals/" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Машина",
    "target_amount": "50000000.00",
    "deadline": "2024-12-31",
    "description": "Накопления на Chevrolet Cobalt"
  }'

# 2. Пополнение цели
curl -X POST "http://localhost:8000/api/goals/api/goals/{goal_id}/add_progress/" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "amount": "2000000.00",
    "description": "Пополнение от зарплаты",
    "withdraw_from_balance": true
  }'

# 3. Статистика
curl -X GET "http://localhost:8000/api/goals/api/goals/stats/" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

### Фильтрация и поиск

```bash
# Только активные цели
GET /api/goals/api/goals/?is_active=true

# Просроченные цели
GET /api/goals/api/goals/?is_overdue=true

# Поиск по названию
GET /api/goals/api/goals/?search=iPhone

# Сортировка по прогрессу
GET /api/goals/api/goals/?ordering=-progress_percentage

# Транзакции по конкретной цели
GET /api/goals/api/goal-transactions/?goal_id={goal_id}

# Транзакции за месяц
GET /api/goals/api/goal-transactions/?date_from=2024-01-01&date_to=2024-01-31
```

---

## 🚀 Интеграция с другими модулями

### С Transaction модулем:
- При пополнении цели создается expense транзакция
- Автоматическая проверка баланса пользователя
- Списание средств с Balance

### С Analytics модулем:
- Получение текущего баланса пользователя
- Обновление статистики после операций

### С Bot модулем:
- Отправка Telegram уведомлений через telegram_api_service
- Поддержка HTML форматирования сообщений

---

## 🐛 Обработка ошибок

### Возможные ошибки API:

#### 400 Bad Request
```json
{
  "error": "Сумма 2000000 превысит целевую сумму. Осталось внести: 500000"
}
```

#### 400 Bad Request (валидация)
```json
{
  "amount": ["Сумма должна быть больше нуля"],
  "deadline": ["Дата цели должна быть в будущем"]
}
```

#### 403 Forbidden
```json
{
  "error": "Нельзя добавлять прогресс к неактивной цели"
}
```

#### 404 Not Found
```json
{
  "detail": "Не найдено."
}
```

---

## 📋 Заключение

Goals & Savings API предоставляет полнофункциональную систему управления финансовыми целями с:

✅ **Полным CRUD** для целей и транзакций  
✅ **Умной бизнес-логикой** с автоматической проверкой статусов  
✅ **Telegram интеграцией** с 5 типами уведомлений  
✅ **Интеграцией с финансовым модулем** для списания средств  
✅ **Развитой статистикой** и отчетностью  
✅ **Безопасностью и валидацией** всех операций  

API готов к использованию в продакшене и легко интегрируется с фронтенд приложениями.

---

*Документация создана: 2024-01-20 | Версия API: 1.0 | Этап 6: Goals & Savings* 