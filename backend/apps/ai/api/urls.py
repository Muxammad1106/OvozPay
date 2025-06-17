"""
URL маршруты для AI API
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import OCRViewSet, VoiceViewSet, ReceiptVoiceMatchViewSet

# Создаем роутер
router = DefaultRouter()
router.register(r'ocr', OCRViewSet, basename='ocr')
router.register(r'voice', VoiceViewSet, basename='voice')
router.register(r'match', ReceiptVoiceMatchViewSet, basename='match')

app_name = 'ai_api'

urlpatterns = [
    path('', include(router.urls)),
]

# Список всех доступных endpoints:
# 
# OCR Endpoints:
# POST   /api/ai/ocr/scan-receipt/           - Сканирование чека
# GET    /api/ai/ocr/processing-status/      - Статус OCR сервиса
# GET    /api/ai/ocr/                        - Список результатов OCR
# GET    /api/ai/ocr/{id}/                   - Детали результата OCR
# 
# Voice Endpoints:
# POST   /api/ai/voice/recognize/            - Распознавание голоса
# GET    /api/ai/voice/processing-status/    - Статус Voice сервиса  
# GET    /api/ai/voice/supported-languages/  - Поддерживаемые языки
# GET    /api/ai/voice/                      - Список результатов распознавания
# GET    /api/ai/voice/{id}/                 - Детали результата распознавания
# 
# Receipt-Voice Matching Endpoints:
# POST   /api/ai/match/match-with-receipt/   - Сопоставление голоса с чеком
# POST   /api/ai/match/auto-match/           - Автоматическое сопоставление
# GET    /api/ai/match/recent-matches/       - Недавние сопоставления
# GET    /api/ai/match/processing-status/    - Статус сервиса сопоставления
# GET    /api/ai/match/                      - Список сопоставлений
# GET    /api/ai/match/{id}/                 - Детали сопоставления 