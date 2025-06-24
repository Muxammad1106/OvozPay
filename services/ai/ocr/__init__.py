"""
OCR Module
Модуль для распознавания текста с изображений через EasyOCR
"""

from .easyocr_service import EasyOCRService, easyocr_service, extract_receipt_text

__all__ = [
    'EasyOCRService',
    'easyocr_service', 
    'extract_receipt_text'
] 