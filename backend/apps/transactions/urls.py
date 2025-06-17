from django.urls import path, include
from rest_framework.routers import DefaultRouter
from apps.transactions.views.api import TransactionViewSet, DebtTransactionViewSet

router = DefaultRouter()
router.register(r'transactions', TransactionViewSet)
router.register(r'debts', DebtTransactionViewSet)

urlpatterns = [
    path('api/', include(router.urls)),
] 