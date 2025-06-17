"""
URL маршруты для модуля напоминаний и планировщика OvozPay
Этап 7: Reminders & Scheduler API
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from apps.reminders.views.api import ReminderViewSet, ReminderHistoryViewSet

# Создаем роутер для API
router = DefaultRouter()
router.register(r'reminders', ReminderViewSet, basename='reminder')
router.register(r'reminder-history', ReminderHistoryViewSet, basename='reminder-history')

urlpatterns = [
    # API маршруты через роутер
    path('', include(router.urls)),
]

# Для документации - список всех доступных эндпоинтов:
"""
API Endpoints (12 основных + дополнительные):

REMINDERS:
1. GET /api/reminders/ - Список напоминаний пользователя
2. POST /api/reminders/ - Создать напоминание
3. GET /api/reminders/{id}/ - Получить детальную информацию
4. PUT /api/reminders/{id}/ - Полное обновление
5. PATCH /api/reminders/{id}/ - Частичное обновление
6. DELETE /api/reminders/{id}/ - Удалить напоминание
7. POST /api/reminders/{id}/activate/ - Активировать напоминание
8. POST /api/reminders/{id}/deactivate/ - Деактивировать напоминание
9. GET /api/reminders/upcoming/ - Ближайшие напоминания
10. GET /api/reminders/history/ - История выполненных напоминаний
11. POST /api/reminders/{id}/send-now/ - Отправить уведомление вручную
12. GET /api/reminders/types/ - Список доступных типов

ДОПОЛНИТЕЛЬНЫЕ:
- GET /api/reminders/stats/ - Статистика напоминаний
- GET /api/reminders/overdue/ - Просроченные напоминания
- POST /api/reminders/process-scheduled/ - Обработать запланированные (админ)

REMINDER HISTORY:
- GET /api/reminder-history/ - История напоминаний
- GET /api/reminder-history/{id}/ - Детали записи истории
- GET /api/reminder-history/summary/ - Сводка по истории
""" 