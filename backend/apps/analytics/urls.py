from django.urls import path, include
from rest_framework.routers import DefaultRouter
from apps.analytics.views.api import ReportViewSet, BalanceViewSet

router = DefaultRouter()
router.register(r'reports', ReportViewSet)
router.register(r'balances', BalanceViewSet)

urlpatterns = [
    path('api/', include(router.urls)),
] 