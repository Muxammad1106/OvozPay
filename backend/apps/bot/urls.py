from django.urls import path, include
from rest_framework.routers import DefaultRouter
from apps.bot.views.api import VoiceCommandLogViewSet, BotSessionViewSet

router = DefaultRouter()
router.register(r'voice-commands', VoiceCommandLogViewSet)
router.register(r'sessions', BotSessionViewSet)

urlpatterns = [
    path('api/', include(router.urls)),
] 