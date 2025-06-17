from django.urls import path, include
from rest_framework.routers import DefaultRouter
from apps.users.views.api import UserViewSet, ReferralViewSet, UserSettingsViewSet

router = DefaultRouter()
router.register(r'users', UserViewSet)
router.register(r'referrals', ReferralViewSet)
router.register(r'user-settings', UserSettingsViewSet)

urlpatterns = [
    path('api/', include(router.urls)),
] 