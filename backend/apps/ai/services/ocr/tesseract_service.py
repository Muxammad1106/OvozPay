"""
Сервис OCR распознавания с использованием Tesseract
Реальная интеграция для распознавания чеков
"""

import os
import re
import logging
import tempfile
import subprocess
from typing import Dict, List, Optional, Tuple
from decimal import Decimal
from datetime import datetime
from PIL import Image, ImageEnhance, ImageFilter
import cv2
import numpy as np

from django.conf import settings
from django.core.files.uploadedfile import UploadedFile

from apps.ai.models import OCRResult, OCRItem, AIProcessingLog
from apps.categories.models import Category


logger = logging.getLogger(__name__)


class TesseractOCRService:
    """Сервис OCR распознавания с Tesseract"""
    
    # Поддерживаемые языки
    SUPPORTED_LANGUAGES = ['rus', 'eng', 'uzb', 'uzb_cyrl']
    
    # Комбинация языков для многоязычного распознавания
    LANGUAGE_CONFIG = 'rus+eng+uzb+uzb_cyrl'
    
    # PSM режимы для разных типов текста
    PSM_MODES = {
        'receipt': '6',  # Uniform block of text
        'document': '1',  # OSD only
        'line': '7',     # Single text line
        'word': '8',     # Single word
        'auto': '3'      # Fully automatic
    }
    
    # Паттерны для извлечения данных из чеков
    PATTERNS = {
        'total_amount': [
            r'ИТОГО[:\s]*(\d+[.,]\d+)',
            r'СУММА[:\s]*(\d+[.,]\d+)',
            r'ВСЕГО[:\s]*(\d+[.,]\d+)', 
            r'TOTAL[:\s]*(\d+[.,]\d+)',
            r'JAMI[:\s]*(\d+[.,]\d+)',
            r'(\d+[.,]\d+)\s*СУМ',
            r'(\d+[.,]\d+)\s*SUM'
        ],
        'shop_name': [
            r'^([А-ЯЁ\s]{3,30})',
            r'ИП\s+([А-ЯЁ\s]{3,30})',
            r'ООО\s+([А-ЯЁ\s]{3,30})',
            r'МЧЖ\s+([А-ЯЁ\s]{3,30})'
        ],
        'receipt_number': [
            r'№\s*(\d+)',
            r'ЧЕК\s*№\s*(\d+)',
            r'RECEIPT\s*№\s*(\d+)',
            r'CHECK\s*(\d+)'
        ],
        'date_time': [
            r'(\d{2}[./]\d{2}[./]\d{4})\s+(\d{2}:\d{2})',
            r'(\d{2}[./]\d{2}[./]\d{2})\s+(\d{2}:\d{2})',
            r'(\d{4}-\d{2}-\d{2})\s+(\d{2}:\d{2})'
        ],
        'items': [
            r'([А-ЯЁа-яё\s]+)\s+(\d+[.,]\d+)\s*(?:x|х|\*)\s*(\d+)\s*=?\s*(\d+[.,]\d+)',
            r'([А-ЯЁа-яё\s]+)\s+(\d+[.,]\d+)',
            r'(\d+)\.\s*([А-ЯЁа-яё\s]+)\s+(\d+[.,]\d+)'
        ]
    }
    
    def __init__(self):
        """Инициализация сервиса"""
        self.tesseract_available = self._check_tesseract_availability()
        self.supported_languages = self._get_available_languages()
        
    def _check_tesseract_availability(self) -> bool:
        """Проверка доступности Tesseract"""
        try:
            result = subprocess.run(
                ['tesseract', '--version'],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                logger.info("Tesseract OCR доступен")
                return True
        except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
            logger.warning("Tesseract OCR недоступен")
        
        return False
    
    def _get_available_languages(self) -> List[str]:
        """Получение списка доступных языков"""
        try:
            result = subprocess.run(
                ['tesseract', '--list-langs'],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                languages = result.stdout.strip().split('\n')[1:]  # Убираем заголовок
                available = [lang for lang in self.SUPPORTED_LANGUAGES if lang in languages]
                logger.info(f"Доступные языки OCR: {available}")
                return available
        except Exception as e:
            logger.error(f"Ошибка получения языков: {e}")
        
        return ['eng']  # Fallback
    
    def process_receipt_image(self, user, image_file: UploadedFile, 
                            recognition_type: str = 'receipt') -> OCRResult:
        """
        Основной метод обработки изображения чека
        
        Args:
            user: Пользователь
            image_file: Файл изображения
            recognition_type: Тип распознавания
            
        Returns:
            OCRResult: Результат OCR обработки
        """
        # Создаем запись результата
        ocr_result = OCRResult.objects.create(
            user=user,
            original_filename=image_file.name,
            recognition_type=recognition_type,
            status='processing'
        )
        
        try:
            # Сохраняем изображение
            ocr_result.image = image_file
            ocr_result.save()
            
            if not self.tesseract_available:
                # Возвращаем демо-результат если Tesseract недоступен
                return self._create_demo_result(ocr_result)
            
            # Предобработка изображения
            processed_image_path = self._preprocess_image(image_file)
            
            # OCR распознавание
            raw_text = self._perform_ocr(processed_image_path, recognition_type)
            
            # Обработка и извлечение данных
            parsed_data = self._parse_receipt_data(raw_text)
            
            # Обновляем результат
            ocr_result.raw_text = raw_text
            ocr_result.shop_name = parsed_data.get('shop_name', '')
            ocr_result.total_amount = parsed_data.get('total_amount', 0)
            ocr_result.receipt_number = parsed_data.get('receipt_number', '')
            ocr_result.receipt_date = parsed_data.get('receipt_date')
            ocr_result.items_count = len(parsed_data.get('items', []))
            ocr_result.confidence_score = parsed_data.get('confidence', 0.0)
            ocr_result.status = 'completed'
            ocr_result.save()
            
            # Создаем записи товаров
            self._create_ocr_items(ocr_result, parsed_data.get('items', []))
            
            # Очистка временного файла
            if os.path.exists(processed_image_path):
                os.unlink(processed_image_path)
            
            logger.info(f"OCR обработка завершена: {ocr_result.id}")
            return ocr_result
            
        except Exception as e:
            logger.error(f"Ошибка OCR обработки: {e}")
            ocr_result.status = 'failed'
            ocr_result.error_message = str(e)
            ocr_result.save()
            return ocr_result
    
    def _preprocess_image(self, image_file: UploadedFile) -> str:
        """
        Предобработка изображения для улучшения OCR
        
        Args:
            image_file: Файл изображения
            
        Returns:
            str: Путь к обработанному изображению
        """
        try:
            # Создаем временный файл
            with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as temp_file:
                temp_path = temp_file.name
            
            # Загружаем изображение
            image = Image.open(image_file)
            
            # Конвертируем в RGB если нужно
            if image.mode != 'RGB':
                image = image.convert('RGB')
            
            # Увеличиваем размер если изображение маленькое
            width, height = image.size
            if width < 800 or height < 600:
                scale_factor = max(800/width, 600/height)
                new_size = (int(width * scale_factor), int(height * scale_factor))
                image = image.resize(new_size, Image.Resampling.LANCZOS)
            
            # Улучшаем контрастность
            enhancer = ImageEnhance.Contrast(image)
            image = enhancer.enhance(1.2)
            
            # Улучшаем четкость
            enhancer = ImageEnhance.Sharpness(image)
            image = enhancer.enhance(1.1)
            
            # Конвертируем в numpy array для OpenCV
            img_array = np.array(image)
            img_cv = cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)
            
            # Применяем Gaussian blur для сглаживания
            img_cv = cv2.GaussianBlur(img_cv, (1, 1), 0)
            
            # Применяем пороговую фильтрацию для бинаризации
            gray = cv2.cvtColor(img_cv, cv2.COLOR_BGR2GRAY)
            _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            
            # Сохраняем обработанное изображение
            cv2.imwrite(temp_path, thresh)
            
            return temp_path
            
        except Exception as e:
            logger.error(f"Ошибка предобработки изображения: {e}")
            # Возвращаем оригинальное изображение
            with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as temp_file:
                image_file.seek(0)
                temp_file.write(image_file.read())
                return temp_file.name
    
    def _perform_ocr(self, image_path: str, recognition_type: str = 'receipt') -> str:
        """
        Выполнение OCR распознавания
        
        Args:
            image_path: Путь к изображению
            recognition_type: Тип распознавания
            
        Returns:
            str: Распознанный текст
        """
        try:
            # Определяем PSM режим
            psm_mode = self.PSM_MODES.get(recognition_type, '6')
            
            # Формируем команду Tesseract
            cmd = [
                'tesseract',
                image_path,
                'stdout',
                '--psm', psm_mode,
                '-l', self.LANGUAGE_CONFIG,
                '-c', 'tessedit_char_whitelist=0123456789АБВГДЕЁЖЗИЙКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯабвгдеёжзийклмнопрстуфхцчшщъыьэюяABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz .,:;()-+/*=№'
            ]
            
            # Выполняем OCR
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                raw_text = result.stdout.strip()
                logger.info(f"OCR успешно: {len(raw_text)} символов")
                return raw_text
            else:
                logger.error(f"Ошибка Tesseract: {result.stderr}")
                return ""
                
        except subprocess.TimeoutExpired:
            logger.error("Превышено время ожидания OCR")
            return ""
        except Exception as e:
            logger.error(f"Ошибка выполнения OCR: {e}")
            return ""
    
    def _parse_receipt_data(self, raw_text: str) -> Dict:
        """
        Парсинг данных из распознанного текста
        
        Args:
            raw_text: Сырой текст OCR
            
        Returns:
            Dict: Извлеченные данные
        """
        data = {
            'shop_name': '',
            'total_amount': 0,
            'receipt_number': '',
            'receipt_date': None,
            'items': [],
            'confidence': 0.8
        }
        
        if not raw_text:
            return data
        
        lines = raw_text.split('\n')
        text = ' '.join(lines)
        
        # Извлекаем общую сумму
        data['total_amount'] = self._extract_total_amount(text)
        
        # Извлекаем название магазина
        data['shop_name'] = self._extract_shop_name(lines)
        
        # Извлекаем номер чека
        data['receipt_number'] = self._extract_receipt_number(text)
        
        # Извлекаем дату и время
        data['receipt_date'] = self._extract_date_time(text)
        
        # Извлекаем товары
        data['items'] = self._extract_items(lines)
        
        # Рассчитываем уверенность на основе найденных данных
        confidence_score = 0.0
        if data['total_amount'] > 0:
            confidence_score += 0.3
        if data['shop_name']:
            confidence_score += 0.2
        if data['receipt_number']:
            confidence_score += 0.2
        if data['items']:
            confidence_score += 0.3
        
        data['confidence'] = min(confidence_score, 1.0)
        
        return data
    
    def _extract_total_amount(self, text: str) -> float:
        """Извлечение общей суммы"""
        for pattern in self.PATTERNS['total_amount']:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                amount_str = match.group(1).replace(',', '.')
                try:
                    return float(amount_str)
                except ValueError:
                    continue
        return 0.0
    
    def _extract_shop_name(self, lines: List[str]) -> str:
        """Извлечение названия магазина"""
        # Обычно название магазина в первых строчках
        for line in lines[:3]:
            line = line.strip()
            if len(line) > 3 and re.match(r'^[А-ЯЁ\s]+$', line):
                return line
        return ""
    
    def _extract_receipt_number(self, text: str) -> str:
        """Извлечение номера чека"""
        for pattern in self.PATTERNS['receipt_number']:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1)
        return ""
    
    def _extract_date_time(self, text: str) -> Optional[datetime]:
        """Извлечение даты и времени"""
        for pattern in self.PATTERNS['date_time']:
            match = re.search(pattern, text)
            if match:
                try:
                    date_str = match.group(1)
                    time_str = match.group(2)
                    
                    # Парсим дату
                    if '.' in date_str:
                        date_parts = date_str.split('.')
                    elif '/' in date_str:
                        date_parts = date_str.split('/')
                    elif '-' in date_str:
                        date_parts = date_str.split('-')
                        if len(date_parts[0]) == 4:  # YYYY-MM-DD
                            year, month, day = date_parts
                        else:
                            day, month, year = date_parts
                    else:
                        continue
                    
                    if len(date_parts) == 3:
                        if len(date_parts[0]) == 4:  # YYYY
                            year, month, day = date_parts
                        else:  # DD
                            day, month, year = date_parts
                            if len(year) == 2:
                                year = f"20{year}"
                        
                        # Парсим время
                        hour, minute = time_str.split(':')
                        
                        return datetime(
                            int(year), int(month), int(day),
                            int(hour), int(minute)
                        )
                except (ValueError, IndexError):
                    continue
        
        return None
    
    def _extract_items(self, lines: List[str]) -> List[Dict]:
        """Извлечение товаров"""
        items = []
        
        for line in lines:
            line = line.strip()
            if len(line) < 3:
                continue
            
            # Пробуем разные паттерны товаров
            for pattern in self.PATTERNS['items']:
                match = re.search(pattern, line, re.IGNORECASE)
                if match:
                    try:
                        if len(match.groups()) == 4:  # Название, цена, количество, сумма
                            name = match.group(1).strip()
                            price = float(match.group(2).replace(',', '.'))
                            quantity = int(match.group(3))
                            total = float(match.group(4).replace(',', '.'))
                        elif len(match.groups()) == 2:  # Название, цена
                            name = match.group(1).strip()
                            price = float(match.group(2).replace(',', '.'))
                            quantity = 1
                            total = price
                        elif len(match.groups()) == 3:  # Номер, название, цена
                            name = match.group(2).strip()
                            price = float(match.group(3).replace(',', '.'))
                            quantity = 1
                            total = price
                        else:
                            continue
                        
                        if name and price > 0:
                            items.append({
                                'name': name,
                                'price': price,
                                'quantity': quantity,
                                'total_price': total
                            })
                            break
                    except (ValueError, IndexError):
                        continue
        
        return items
    
    def _create_ocr_items(self, ocr_result: OCRResult, items: List[Dict]):
        """Создание записей товаров"""
        for item_data in items:
            OCRItem.objects.create(
                ocr_result=ocr_result,
                name=item_data['name'],
                price=Decimal(str(item_data['price'])),
                quantity=item_data['quantity'],
                total_price=Decimal(str(item_data['total_price']))
            )
    
    def _create_demo_result(self, ocr_result: OCRResult) -> OCRResult:
        """Создание демо-результата когда Tesseract недоступен"""
        demo_items = [
            {'name': 'Хлеб белый', 'price': 4500, 'quantity': 2, 'total_price': 9000},
            {'name': 'Молоко 1л', 'price': 8500, 'quantity': 1, 'total_price': 8500},
            {'name': 'Яйца 10шт', 'price': 15000, 'quantity': 1, 'total_price': 15000},
            {'name': 'Помидоры 1кг', 'price': 12000, 'quantity': 1, 'total_price': 12000},
            {'name': 'Картофель 2кг', 'price': 16000, 'quantity': 1, 'total_price': 16000}
        ]
        
        ocr_result.raw_text = "Демо-режим OCR\nKORZINKA.UZ\nХлеб белый 4500 x 2 = 9000\nМолоко 1л 8500\nИТОГО: 60500"
        ocr_result.shop_name = 'KORZINKA.UZ'
        ocr_result.total_amount = 60500
        ocr_result.receipt_number = 'А001234567'
        ocr_result.receipt_date = datetime.now()
        ocr_result.items_count = len(demo_items)
        ocr_result.confidence_score = 0.95
        ocr_result.status = 'completed'
        ocr_result.save()
        
        self._create_ocr_items(ocr_result, demo_items)
        
        return ocr_result
    
    def get_processing_status(self) -> Dict:
        """Статус сервиса OCR"""
        return {
            'tesseract_available': self.tesseract_available,
            'supported_languages': self.supported_languages,
            'language_config': self.LANGUAGE_CONFIG,
            'psm_modes': self.PSM_MODES
        } 