"""
URL маршруты для модуля целей и накоплений OvozPay
Этап 6: Goals & Savings API
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from apps.goals.views.api import GoalViewSet, GoalTransactionViewSet

# Создаем роутер для API endpoints
router = DefaultRouter()
router.register(r'goals', GoalViewSet, basename='goal')
router.register(r'goal-transactions', GoalTransactionViewSet, basename='goal-transaction')

urlpatterns = [
    path('api/', include(router.urls)),
]

# Для документации: доступные endpoints
"""
API Endpoints:

Goals:
- GET    /api/goals/                     - Список целей
- POST   /api/goals/                     - Создание цели
- GET    /api/goals/{id}/                - Детали цели
- PUT    /api/goals/{id}/                - Обновление цели
- DELETE /api/goals/{id}/                - Удаление цели
- POST   /api/goals/{id}/add_progress/   - Добавить прогресс
- POST   /api/goals/{id}/complete_goal/  - Завершить цель
- POST   /api/goals/{id}/update_status/  - Обновить статус
- GET    /api/goals/stats/               - Статистика целей
- GET    /api/goals/overdue/             - Просроченные цели
- POST   /api/goals/check_overdue/       - Проверить просроченные

Goal Transactions:
- GET    /api/goal-transactions/         - Список транзакций
- POST   /api/goal-transactions/         - Создание транзакции
- GET    /api/goal-transactions/{id}/    - Детали транзакции
- GET    /api/goal-transactions/summary/ - Сводка по транзакциям
""" 