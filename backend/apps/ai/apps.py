"""
Конфигурация приложения для модуля AI интеграции OvozPay
Интеграция нейросетей: OCR, Voice Recognition, NLP
"""

from django.apps import AppConfig


class AiConfig(AppConfig):
    """Конфигурация приложения AI"""
    
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.ai'
    verbose_name = 'Искусственный интеллект'
    
    def ready(self):
        """Инициализация при запуске приложения"""
        try:
            # Импортируем сигналы для обработки файлов
            import apps.ai.signals  # noqa
        except ImportError:
            pass
        
        # Проверяем доступность ML библиотек
        try:
            self._check_dependencies()
        except ImportError as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"ML dependencies not fully available: {e}")
    
    def _check_dependencies(self):
        """Проверка доступности зависимостей"""
        # Проверяем Tesseract
        import subprocess
        try:
            subprocess.run(['tesseract', '--version'], capture_output=True, check=True)
        except (subprocess.CalledProcessError, FileNotFoundError):
            raise ImportError("Tesseract OCR not installed")
        
        # Проверяем основные Python библиотеки
        try:
            import cv2  # OpenCV для обработки изображений
            import numpy as np
            import PIL  # Pillow для работы с изображениями
        except ImportError as e:
            raise ImportError(f"Required Python libraries missing: {e}") 