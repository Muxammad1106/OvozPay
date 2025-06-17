"""
URL маршруты для AI модуля OvozPay
OCR, Voice Recognition, Command Processing
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter

from apps.ai.views.api.ai_views import (
    OCRResultViewSet,
    OCRItemViewSet,
    VoiceResultViewSet,
    VoiceCommandViewSet,
    AIProcessingLogViewSet,
    AIServiceViewSet,
)

# Создаем основной роутер
router = DefaultRouter()

# Регистрируем ViewSets
router.register(r'ocr/results', OCRResultViewSet, basename='ocr-results')
router.register(r'ocr/items', OCRItemViewSet, basename='ocr-items')
router.register(r'voice/results', VoiceResultViewSet, basename='voice-results')
router.register(r'voice/commands', VoiceCommandViewSet, basename='voice-commands')
router.register(r'logs', AIProcessingLogViewSet, basename='ai-logs')
router.register(r'services', AIServiceViewSet, basename='ai-services')

# URL patterns
urlpatterns = [
    # API v1 маршруты через роутер
    path('api/v1/', include(router.urls)),
    
    # Дополнительные маршруты могут быть добавлены здесь
]

# Имя приложения для reverse URL lookup
app_name = 'ai' 