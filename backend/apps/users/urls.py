from django.urls import path, include
from rest_framework.routers import DefaultRouter
from apps.users.views.api import UserViewSet, ReferralViewSet, UserSettingsViewSet
from apps.users.views.api.auth.telegram_auth_views import telegram_login, refresh_token

router = DefaultRouter()
router.register(r'users', UserViewSet)
router.register(r'referrals', ReferralViewSet)
router.register(r'user-settings', UserSettingsViewSet)

urlpatterns = [
    path('api/', include(router.urls)),
    path('auth/telegram-login/', telegram_login, name='telegram_login'),
    path('auth/refresh-token/', refresh_token, name='refresh_token'),
] 