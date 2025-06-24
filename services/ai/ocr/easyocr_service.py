"""
EasyOCRService - Распознавание текста с изображений через EasyOCR
Поддерживает русский, узбекский и английский языки
"""

import asyncio
import logging
import tempfile
from typing import Optional, Dict, Any, List
from pathlib import Path
import cv2
import numpy as np
from django.conf import settings

logger = logging.getLogger(__name__)


class EasyOCRService:
    """Сервис для распознавания текста с изображений через EasyOCR"""
    
    def __init__(self):
        self.supported_languages = ['ru', 'en']  # Совместимые языки для EasyOCR
        self.temp_dir = Path(tempfile.gettempdir()) / 'ovozpay_images'
        self.temp_dir.mkdir(exist_ok=True)
        
        # Ленивая инициализация EasyOCR
        self._reader = None
        self._check_dependencies()
    
    def _check_dependencies(self) -> None:
        """Проверяет установлены ли необходимые библиотеки"""
        try:
            import easyocr
            import cv2
            logger.info("EasyOCR и OpenCV успешно найдены")
        except ImportError as e:
            logger.error(f"Ошибка импорта зависимостей: {e}")
            logger.warning(
                "Для работы с изображениями установите: "
                "pip install easyocr opencv-python"
            )
    
    def _get_reader(self):
        """Возвращает экземпляр EasyOCR reader (ленивая инициализация)"""
        if self._reader is None:
            try:
                import easyocr
                self._reader = easyocr.Reader(
                    self.supported_languages,
                    gpu=getattr(settings, 'EASYOCR_USE_GPU', False)
                )
                logger.info("EasyOCR reader инициализирован")
            except Exception as e:
                logger.error(f"Ошибка инициализации EasyOCR: {e}")
                raise
        
        return self._reader
    
    async def extract_text_from_image(
        self,
        image_path: str,
        enhance_image: bool = True,
        user_id: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Извлекает текст из изображения
        
        Args:
            image_path: Путь к изображению
            enhance_image: Применять ли предобработку изображения
            user_id: ID пользователя для логирования
            
        Returns:
            Словарь с извлечённым текстом и метаданными
        """
        start_time = asyncio.get_event_loop().time()
        
        try:
            # Валидация файла
            if not Path(image_path).exists():
                raise FileNotFoundError(f"Изображение не найдено: {image_path}")
            
            logger.info(f"Начинаем OCR обработку изображения для пользователя {user_id}")
            
            # Предобработка изображения (если включена)
            processed_image_path = image_path
            if enhance_image:
                processed_image_path = await self._enhance_image(image_path)
            
            # Запускаем OCR в отдельном потоке
            ocr_result = await self._run_ocr_extraction(processed_image_path)
            
            if ocr_result:
                processing_time = asyncio.get_event_loop().time() - start_time
                
                result = {
                    'raw_text': ocr_result['raw_text'],
                    'structured_data': ocr_result['structured_data'],
                    'confidence': ocr_result['confidence'],
                    'processing_time': processing_time,
                    'detected_regions': len(ocr_result['regions']),
                    'image_size': ocr_result.get('image_size', (0, 0))
                }
                
                logger.info(
                    f"OCR завершён за {processing_time:.2f}с, "
                    f"найдено {len(ocr_result['regions'])} текстовых областей"
                )
                
                return result
            else:
                logger.warning("OCR не смог обнаружить текст на изображении")
                return None
                
        except Exception as e:
            processing_time = asyncio.get_event_loop().time() - start_time
            logger.error(f"Ошибка OCR обработки за {processing_time:.2f}с: {e}")
            return None
        finally:
            # Очистка временных файлов
            if enhance_image and processed_image_path != image_path:
                try:
                    Path(processed_image_path).unlink()
                except:
                    pass
    
    async def _enhance_image(self, image_path: str) -> str:
        """Улучшает качество изображения для лучшего OCR"""
        try:
            import cv2
            
            # Читаем изображение
            image = cv2.imread(image_path)
            if image is None:
                raise ValueError("Не удалось загрузить изображение")
            
            # Применяем улучшения
            enhanced = await asyncio.get_event_loop().run_in_executor(
                None,
                self._apply_image_enhancements,
                image
            )
            
            # Сохраняем улучшенное изображение
            enhanced_path = self.temp_dir / f"enhanced_{Path(image_path).name}"
            cv2.imwrite(str(enhanced_path), enhanced)
            
            return str(enhanced_path)
            
        except Exception as e:
            logger.error(f"Ошибка улучшения изображения: {e}")
            return image_path  # Возвращаем оригинал при ошибке
    
    def _apply_image_enhancements(self, image: np.ndarray) -> np.ndarray:
        """Применяет различные улучшения к изображению"""
        try:
            import cv2
            
            # Конвертируем в серый
            if len(image.shape) == 3:
                gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            else:
                gray = image.copy()
            
            # Увеличиваем контрастность
            enhanced = cv2.convertScaleAbs(gray, alpha=1.2, beta=20)
            
            # Применяем гауссово размытие для удаления шума
            denoised = cv2.GaussianBlur(enhanced, (3, 3), 0)
            
            # Применяем адаптивную пороговую обработку
            thresh = cv2.adaptiveThreshold(
                denoised, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
                cv2.THRESH_BINARY, 11, 2
            )
            
            return thresh
            
        except Exception as e:
            logger.error(f"Ошибка применения улучшений: {e}")
            return image
    
    async def _run_ocr_extraction(self, image_path: str) -> Optional[Dict[str, Any]]:
        """Запускает процесс OCR извлечения"""
        try:
            reader = self._get_reader()
            
            # Запускаем OCR в отдельном потоке
            results = await asyncio.get_event_loop().run_in_executor(
                None,
                reader.readtext,
                image_path
            )
            
            if not results:
                return None
            
            # Обрабатываем результаты
            regions = []
            all_text = []
            confidences = []
            
            for (bbox, text, confidence) in results:
                if confidence > 0.3:  # Фильтруем низкокачественные результаты
                    regions.append({
                        'bbox': bbox,
                        'text': text.strip(),
                        'confidence': confidence
                    })
                    all_text.append(text.strip())
                    confidences.append(confidence)
            
            if not regions:
                return None
            
            # Объединяем весь текст
            raw_text = ' '.join(all_text)
            
            # Структурированные данные (базовый парсинг)
            structured_data = self._parse_receipt_data(raw_text, regions)
            
            return {
                'raw_text': raw_text,
                'regions': regions,
                'structured_data': structured_data,
                'confidence': sum(confidences) / len(confidences) if confidences else 0
            }
            
        except Exception as e:
            logger.error(f"Ошибка выполнения OCR: {e}")
            return None
    
    def _parse_receipt_data(self, raw_text: str, regions: List[Dict]) -> Dict[str, Any]:
        """Базовый парсинг данных чека"""
        import re
        from datetime import datetime
        
        structured = {
            'amounts': [],
            'dates': [],
            'items': [],
            'total_amount': None,
            'shop_name': None
        }
        
        try:
            # Поиск сумм (числа с возможными валютами)
            amount_patterns = [
                r'(\d{1,3}(?:\s?\d{3})*(?:[,.]\d{2})?)\s*(сум|руб|₽|\$|€)',
                r'(\d{1,3}(?:\s?\d{3})*(?:[,.]\d{2})?)\s*$',
                r'ИТОГО:?\s*(\d{1,3}(?:\s?\d{3})*(?:[,.]\d{2})?)',
                r'СУММА:?\s*(\d{1,3}(?:\s?\d{3})*(?:[,.]\d{2})?)'
            ]
            
            for pattern in amount_patterns:
                matches = re.findall(pattern, raw_text, re.IGNORECASE)
                for match in matches:
                    if isinstance(match, tuple):
                        amount_str = match[0]
                    else:
                        amount_str = match
                    
                    # Очищаем и конвертируем
                    amount_str = amount_str.replace(' ', '').replace(',', '.')
                    try:
                        amount = float(amount_str)
                        if amount > 0:
                            structured['amounts'].append(amount)
                    except ValueError:
                        continue
            
            # Находим наибольшую сумму как итоговую
            if structured['amounts']:
                structured['total_amount'] = max(structured['amounts'])
            
            # Поиск дат
            date_patterns = [
                r'(\d{1,2}[./]\d{1,2}[./]\d{2,4})',
                r'(\d{1,2}\s+\w+\s+\d{2,4})'
            ]
            
            for pattern in date_patterns:
                dates = re.findall(pattern, raw_text)
                structured['dates'].extend(dates)
            
            # Поиск названия товаров (строки между суммами)
            lines = raw_text.split('\n')
            for line in lines:
                line = line.strip()
                # Пропускаем строки только с числами или служебной информацией
                if (len(line) > 3 and 
                    not re.match(r'^\d+[.,]?\d*\s*$', line) and
                    not re.match(r'^[=\-_*]+$', line) and
                    'чек' not in line.lower() and
                    'касса' not in line.lower()):
                    structured['items'].append(line)
            
            # Поиск названия магазина (обычно в начале чека)
            first_lines = raw_text.split('\n')[:5]
            for line in first_lines:
                line = line.strip()
                if (len(line) > 5 and 
                    not re.search(r'\d', line) and  # Нет цифр
                    len(line.split()) <= 4):  # Не слишком длинная
                    structured['shop_name'] = line
                    break
                    
        except Exception as e:
            logger.error(f"Ошибка парсинга данных чека: {e}")
        
        return structured
    
    def cleanup_temp_files(self, older_than_hours: int = 24) -> None:
        """Очищает временные файлы старше указанного времени"""
        try:
            import time
            current_time = time.time()
            cutoff_time = current_time - (older_than_hours * 3600)
            
            for file_path in self.temp_dir.glob('*'):
                if file_path.is_file() and file_path.stat().st_mtime < cutoff_time:
                    file_path.unlink()
                    logger.debug(f"Удален временный файл: {file_path}")
                    
        except Exception as e:
            logger.error(f"Ошибка очистки временных файлов: {e}")
    
    async def initialize(self) -> bool:
        """
        Инициализирует EasyOCR сервис
        
        Returns:
            bool: True если инициализация успешна
        """
        try:
            import easyocr
            import cv2
            
            # Создаём reader для проверки
            _ = self._get_reader()
            
            logger.info("EasyOCR сервис успешно инициализирован")
            return True
            
        except Exception as e:
            logger.error(f"Ошибка инициализации EasyOCR: {e}")
            return False

    async def health_check(self) -> bool:
        """
        Проверяет готовность сервиса к работе
        
        Returns:
            bool: True если сервис готов
        """
        try:
            import easyocr
            import cv2
            
            # Проверяем, что можем создать reader
            _ = self._get_reader()
            
            logger.info("EasyOCR сервис готов к работе")
            return True
            
        except Exception as e:
            logger.error(f"Ошибка проверки здоровья EasyOCR: {e}")
            return False

    def get_supported_languages(self) -> list:
        """
        Возвращает список поддерживаемых языков
        
        Returns:
            list: Список кодов языков
        """
        return self.supported_languages

    def get_supported_formats(self) -> list:
        """
        Возвращает список поддерживаемых форматов изображений
        
        Returns:
            list: Список поддерживаемых форматов
        """
        return [
            'jpg', 'jpeg', 'png', 'bmp', 'tiff', 
            'webp', 'tga', 'gif', 'ppm', 'pgm'
        ]

    def get_service_status(self) -> Dict[str, Any]:
        """Возвращает статус сервиса"""
        try:
            import easyocr
            import cv2
            
            return {
                'service': 'EasyOCRService',
                'status': 'active',
                'supported_languages': self.supported_languages,
                'temp_dir': str(self.temp_dir),
                'easyocr_available': True,
                'opencv_available': True
            }
            
        except ImportError as e:
            return {
                'service': 'EasyOCRService',
                'status': 'error',
                'error': f'Отсутствуют зависимости: {e}',
                'easyocr_available': False,
                'opencv_available': False
            }
        except Exception as e:
            return {
                'service': 'EasyOCRService',
                'status': 'error',
                'error': str(e)
            }


# Глобальный экземпляр сервиса
easyocr_service = EasyOCRService()


# Функции-обёртки для удобства использования
async def extract_receipt_text(
    image_path: str,
    user_id: Optional[str] = None
) -> Optional[Dict[str, Any]]:
    """
    Упрощённая функция для извлечения текста с чека
    
    Args:
        image_path: Путь к изображению чека
        user_id: ID пользователя
        
    Returns:
        Структурированные данные чека или None
    """
    result = await easyocr_service.extract_text_from_image(
        image_path, 
        enhance_image=True, 
        user_id=user_id
    )
    
    if result and result.get('structured_data'):
        return result['structured_data']
    
    return None


def sync_extract_receipt_text(
    image_path: str,
    user_id: Optional[str] = None
) -> Optional[Dict[str, Any]]:
    """Синхронная версия извлечения текста с чека"""
    return asyncio.run(extract_receipt_text(image_path, user_id)) 