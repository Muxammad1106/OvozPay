"""
AI сервисы для OvozPay
Модуль содержит все AI сервисы для обработки голоса, изображений и текста
"""

from .voice_recognition.whisper_service import WhisperService
from .ocr.easyocr_service import EasyOCRService
from .text_processing.nlp_service import NLPService

__all__ = [
    'WhisperService',
    'EasyOCRService', 
    'NLPService',
] 