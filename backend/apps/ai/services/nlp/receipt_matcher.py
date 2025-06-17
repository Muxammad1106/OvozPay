"""
Сервис сопоставления голосовых сообщений с чеками
Анализ аудио-команд и сопоставление с чековыми позициями
"""

import re
import logging
from typing import Dict, List, Optional, Tuple
from decimal import Decimal
from datetime import datetime, timedelta
from difflib import SequenceMatcher

from django.utils import timezone
from django.db.models import Q

from apps.ai.models import OCRResult, VoiceResult, ReceiptVoiceMatch
from apps.ai.services.nlp.command_processor import VoiceCommandProcessor


logger = logging.getLogger(__name__)


class ReceiptVoiceMatcher:
    """Сервис сопоставления голосовых сообщений с чеками"""
    
    # Максимальное время между чеком и голосовым сообщением (в минутах)
    MAX_TIME_DIFF_MINUTES = 5
    
    # Минимальный порог схожести для сопоставления товаров
    SIMILARITY_THRESHOLD = 0.6
    
    # Ключевые слова для определения товаров в речи
    ITEM_KEYWORDS = {
        'ru': ['купил', 'взял', 'покупал', 'приобрел', 'товар', 'продукт'],
        'uz': ['sotib oldim', 'oldim', 'mahsulot', 'tovar'],
        'en': ['bought', 'purchased', 'got', 'item', 'product']
    }
    
    # Ключевые слова для определения сумм
    AMOUNT_KEYWORDS = {
        'ru': ['сум', 'тысяч', 'рублей', 'копеек', 'стоило', 'стоит', 'цена'],
        'uz': ['sum', 'ming', 'turdi', 'narx'],
        'en': ['sum', 'thousand', 'cost', 'price', 'costs']
    }
    
    def __init__(self):
        """Инициализация сервиса"""
        self.command_processor = VoiceCommandProcessor()
    
    def find_matching_receipts(
        self, 
        voice_result: VoiceResult,
        time_window_minutes: int = None
    ) -> List[OCRResult]:
        """
        Поиск подходящих чеков для голосового сообщения
        
        Args:
            voice_result: Результат распознавания голоса
            time_window_minutes: Временное окно поиска (в минутах)
            
        Returns:
            List[OCRResult]: Список подходящих чеков
        """
        if time_window_minutes is None:
            time_window_minutes = self.MAX_TIME_DIFF_MINUTES
        
        # Определяем временные рамки поиска
        voice_time = voice_result.created_at
        start_time = voice_time - timedelta(minutes=time_window_minutes)
        end_time = voice_time + timedelta(minutes=time_window_minutes)
        
        # Ищем чеки пользователя в указанном временном окне
        receipts = OCRResult.objects.filter(
            user=voice_result.user,
            status='completed',
            created_at__range=(start_time, end_time)
        ).order_by('-created_at')
        
        logger.info(f"Найдено {receipts.count()} чеков в временном окне")
        return list(receipts)
    
    def match_voice_with_receipt(
        self, 
        voice_result: VoiceResult, 
        ocr_result: OCRResult
    ) -> ReceiptVoiceMatch:
        """
        Сопоставление голосового сообщения с конкретным чеком
        
        Args:
            voice_result: Результат распознавания голоса
            ocr_result: Результат OCR чека
            
        Returns:
            ReceiptVoiceMatch: Результат сопоставления
        """
        # Создаем запись сопоставления
        match = ReceiptVoiceMatch.objects.create(
            voice_result=voice_result,
            ocr_result=ocr_result,
            user=voice_result.user,
            status='processing'
        )
        
        try:
            # Анализируем голосовое сообщение
            voice_analysis = self._analyze_voice_message(voice_result)
            
            # Анализируем чек
            receipt_analysis = self._analyze_receipt(ocr_result)
            
            # Выполняем сопоставление
            matching_result = self._perform_matching(
                voice_analysis, receipt_analysis
            )
            
            # Обновляем результат
            match.confidence_score = matching_result['confidence']
            match.matched_items = matching_result['matched_items']
            match.voice_items = voice_analysis['items']
            match.receipt_items = receipt_analysis['items']
            match.total_amount_voice = voice_analysis['total_amount']
            match.total_amount_receipt = receipt_analysis['total_amount']
            match.matching_details = matching_result['details']
            match.status = 'completed'
            match.save()
            
            logger.info(f"Сопоставление выполнено: {match.id}, уверенность: {match.confidence_score}")
            
        except Exception as e:
            logger.error(f"Ошибка сопоставления: {e}")
            match.status = 'failed'
            match.error_message = str(e)
            match.save()
        
        return match
    
    def _analyze_voice_message(self, voice_result: VoiceResult) -> Dict:
        """
        Анализ голосового сообщения для извлечения информации о покупках
        
        Args:
            voice_result: Результат распознавания голоса
            
        Returns:
            Dict: Проанализированные данные
        """
        text = voice_result.recognized_text.lower()
        language = voice_result.detected_language or 'ru'
        
        analysis = {
            'items': [],
            'total_amount': 0,
            'language': language,
            'raw_text': voice_result.recognized_text
        }
        
        # Извлекаем товары из текста
        items = self._extract_items_from_voice(text, language)
        analysis['items'] = items
        
        # Извлекаем общую сумму
        total_amount = self._extract_total_amount_from_voice(text, language)
        analysis['total_amount'] = total_amount
        
        return analysis
    
    def _analyze_receipt(self, ocr_result: OCRResult) -> Dict:
        """
        Анализ чека для извлечения структурированных данных
        
        Args:
            ocr_result: Результат OCR чека
            
        Returns:
            Dict: Проанализированные данные чека
        """
        analysis = {
            'items': [],
            'total_amount': float(ocr_result.total_amount),
            'shop_name': ocr_result.shop_name,
            'receipt_number': ocr_result.receipt_number
        }
        
        # Получаем товары из чека
        receipt_items = []
        for item in ocr_result.items.all():
            receipt_items.append({
                'name': item.name,
                'price': float(item.price),
                'quantity': item.quantity,
                'total_price': float(item.total_price)
            })
        
        analysis['items'] = receipt_items
        
        return analysis
    
    def _extract_items_from_voice(self, text: str, language: str) -> List[Dict]:
        """
        Извлечение товаров из голосового текста
        
        Args:
            text: Текст сообщения
            language: Язык сообщения
            
        Returns:
            List[Dict]: Список найденных товаров
        """
        items = []
        
        # Паттерны для извлечения товаров с ценами
        patterns = {
            'ru': [
                r'([\w\s]+?)\s+(?:за\s+)?(\d+(?:\s*тысяч?)?(?:\s*\d+)?)\s*сум',
                r'([\w\s]+?)\s+(\d+(?:\s*тысяч?)?(?:\s*\d+)?)',
                r'купил\s+([\w\s]+?)(?:\s+за\s+(\d+(?:\s*тысяч?)?(?:\s*\d+)?)\s*сум)?',
                r'взял\s+([\w\s]+?)(?:\s+за\s+(\d+(?:\s*тысяч?)?(?:\s*\d+)?)\s*сум)?'
            ],
            'uz': [
                r'([\w\s]+?)\s+(\d+(?:\s*ming)?(?:\s*\d+)?)\s*sum',
                r'sotib\s+oldim\s+([\w\s]+?)(?:\s+(\d+(?:\s*ming)?(?:\s*\d+)?)\s*sum)?'
            ],
            'en': [
                r'([\w\s]+?)\s+(\d+(?:\s*thousand)?(?:\s*\d+)?)\s*sum',
                r'bought\s+([\w\s]+?)(?:\s+for\s+(\d+(?:\s*thousand)?(?:\s*\d+)?)\s*sum)?'
            ]
        }
        
        for pattern in patterns.get(language, patterns['ru']):
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                item_name = match.group(1).strip()
                price_str = match.group(2) if len(match.groups()) > 1 and match.group(2) else '0'
                
                # Конвертируем цену
                price = self._parse_price_from_text(price_str, language)
                
                if item_name and len(item_name) > 2:
                    items.append({
                        'name': item_name,
                        'price': price,
                        'quantity': 1,
                        'confidence': 0.8
                    })
        
        return items
    
    def _extract_total_amount_from_voice(self, text: str, language: str) -> float:
        """
        Извлечение общей суммы из голосового текста
        
        Args:
            text: Текст сообщения
            language: Язык сообщения
            
        Returns:
            float: Общая сумма
        """
        patterns = {
            'ru': [
                r'всего\s+(\d+(?:\s*тысяч?)?(?:\s*\d+)?)\s*сум',
                r'итого\s+(\d+(?:\s*тысяч?)?(?:\s*\d+)?)\s*сум',
                r'потратил\s+(\d+(?:\s*тысяч?)?(?:\s*\d+)?)\s*сум',
                r'заплатил\s+(\d+(?:\s*тысяч?)?(?:\s*\d+)?)\s*сум'
            ],
            'uz': [
                r'jami\s+(\d+(?:\s*ming)?(?:\s*\d+)?)\s*sum',
                r'tolash\s+(\d+(?:\s*ming)?(?:\s*\d+)?)\s*sum'
            ],
            'en': [
                r'total\s+(\d+(?:\s*thousand)?(?:\s*\d+)?)\s*sum',
                r'paid\s+(\d+(?:\s*thousand)?(?:\s*\d+)?)\s*sum'
            ]
        }
        
        for pattern in patterns.get(language, patterns['ru']):
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return self._parse_price_from_text(match.group(1), language)
        
        return 0.0
    
    def _parse_price_from_text(self, price_str: str, language: str) -> float:
        """
        Парсинг цены из текста с учетом языка
        
        Args:
            price_str: Строка с ценой
            language: Язык
            
        Returns:
            float: Цена в числовом формате
        """
        if not price_str:
            return 0.0
        
        # Убираем лишние пробелы
        price_str = ' '.join(price_str.split())
        
        # Паттерны для чисел с "тысячами"
        thousand_patterns = {
            'ru': [r'(\d+)\s*тысяч?\s*(\d+)?', r'(\d+)\s*т\s*(\d+)?'],
            'uz': [r'(\d+)\s*ming\s*(\d+)?'],
            'en': [r'(\d+)\s*thousand\s*(\d+)?']
        }
        
        # Проверяем паттерны с тысячами
        for pattern in thousand_patterns.get(language, thousand_patterns['ru']):
            match = re.search(pattern, price_str, re.IGNORECASE)
            if match:
                thousands = int(match.group(1))
                remainder = int(match.group(2)) if match.group(2) else 0
                return thousands * 1000 + remainder
        
        # Простое число
        numbers = re.findall(r'\d+', price_str)
        if numbers:
            return float(numbers[0])
        
        return 0.0
    
    def _perform_matching(
        self, 
        voice_analysis: Dict, 
        receipt_analysis: Dict
    ) -> Dict:
        """
        Выполнение сопоставления между голосом и чеком
        
        Args:
            voice_analysis: Анализ голосового сообщения
            receipt_analysis: Анализ чека
            
        Returns:
            Dict: Результат сопоставления
        """
        result = {
            'confidence': 0.0,
            'matched_items': [],
            'details': {
                'voice_items_count': len(voice_analysis['items']),
                'receipt_items_count': len(receipt_analysis['items']),
                'amount_match': False,
                'items_match': False
            }
        }
        
        # Сопоставляем суммы
        voice_total = voice_analysis['total_amount']
        receipt_total = receipt_analysis['total_amount']
        
        amount_confidence = 0.0
        if voice_total > 0 and receipt_total > 0:
            amount_diff = abs(voice_total - receipt_total) / max(voice_total, receipt_total)
            amount_confidence = max(0, 1 - amount_diff)
            result['details']['amount_match'] = amount_confidence > 0.8
        
        # Сопоставляем товары
        items_confidence, matched_items = self._match_items(
            voice_analysis['items'], 
            receipt_analysis['items']
        )
        
        result['matched_items'] = matched_items
        result['details']['items_match'] = items_confidence > self.SIMILARITY_THRESHOLD
        
        # Общая уверенность
        if voice_total > 0:
            # Если есть сумма в голосе, учитываем и сумму и товары
            result['confidence'] = (amount_confidence * 0.6 + items_confidence * 0.4)
        else:
            # Если суммы нет, полагаемся только на товары
            result['confidence'] = items_confidence
        
        result['details']['amount_confidence'] = amount_confidence
        result['details']['items_confidence'] = items_confidence
        
        return result
    
    def _match_items(
        self, 
        voice_items: List[Dict], 
        receipt_items: List[Dict]
    ) -> Tuple[float, List[Dict]]:
        """
        Сопоставление товаров из голоса и чека
        
        Args:
            voice_items: Товары из голоса
            receipt_items: Товары из чека
            
        Returns:
            Tuple[float, List[Dict]]: Уверенность и список сопоставлений
        """
        if not voice_items or not receipt_items:
            return 0.0, []
        
        matched_items = []
        total_confidence = 0.0
        
        for voice_item in voice_items:
            best_match = None
            best_similarity = 0.0
            
            for receipt_item in receipt_items:
                similarity = self._calculate_item_similarity(
                    voice_item['name'], 
                    receipt_item['name']
                )
                
                if similarity > best_similarity and similarity > self.SIMILARITY_THRESHOLD:
                    best_similarity = similarity
                    best_match = receipt_item
            
            if best_match:
                matched_items.append({
                    'voice_item': voice_item,
                    'receipt_item': best_match,
                    'similarity': best_similarity,
                    'price_match': self._compare_prices(
                        voice_item.get('price', 0), 
                        best_match['price']
                    )
                })
                total_confidence += best_similarity
        
        # Средняя уверенность по всем товарам из голоса
        if voice_items:
            total_confidence /= len(voice_items)
        
        return total_confidence, matched_items
    
    def _calculate_item_similarity(self, voice_name: str, receipt_name: str) -> float:
        """
        Вычисление схожести названий товаров
        
        Args:
            voice_name: Название из голоса
            receipt_name: Название из чека
            
        Returns:
            float: Коэффициент схожести (0-1)
        """
        # Нормализуем названия
        voice_clean = self._normalize_item_name(voice_name)
        receipt_clean = self._normalize_item_name(receipt_name)
        
        # Используем SequenceMatcher для базовой схожести
        base_similarity = SequenceMatcher(None, voice_clean, receipt_clean).ratio()
        
        # Проверяем наличие ключевых слов
        voice_words = set(voice_clean.split())
        receipt_words = set(receipt_clean.split())
        
        common_words = voice_words.intersection(receipt_words)
        word_similarity = len(common_words) / max(len(voice_words), len(receipt_words))
        
        # Комбинируем схожести
        final_similarity = (base_similarity * 0.6 + word_similarity * 0.4)
        
        return final_similarity
    
    def _normalize_item_name(self, name: str) -> str:
        """Нормализация названия товара"""
        # Приводим к нижнему регистру
        name = name.lower().strip()
        
        # Убираем лишние символы
        name = re.sub(r'[^\w\s]', ' ', name)
        
        # Убираем лишние пробелы
        name = ' '.join(name.split())
        
        return name
    
    def _compare_prices(self, voice_price: float, receipt_price: float) -> bool:
        """
        Сравнение цен с учетом возможных погрешностей
        
        Args:
            voice_price: Цена из голоса
            receipt_price: Цена из чека
            
        Returns:
            bool: Совпадают ли цены
        """
        if voice_price == 0 or receipt_price == 0:
            return True  # Если одна из цен неизвестна, считаем совпадением
        
        # Допускаем погрешность в 10%
        price_diff = abs(voice_price - receipt_price) / max(voice_price, receipt_price)
        return price_diff <= 0.1
    
    def auto_match_recent_receipts(
        self, 
        voice_result: VoiceResult
    ) -> List[ReceiptVoiceMatch]:
        """
        Автоматическое сопоставление с недавними чеками
        
        Args:
            voice_result: Результат распознавания голоса
            
        Returns:
            List[ReceiptVoiceMatch]: Список результатов сопоставления
        """
        matches = []
        
        # Находим подходящие чеки
        receipts = self.find_matching_receipts(voice_result)
        
        for receipt in receipts:
            # Выполняем сопоставление
            match = self.match_voice_with_receipt(voice_result, receipt)
            
            # Добавляем только успешные сопоставления с высокой уверенностью
            if match.status == 'completed' and match.confidence_score > 0.5:
                matches.append(match)
        
        # Сортируем по уверенности
        matches.sort(key=lambda x: x.confidence_score, reverse=True)
        
        logger.info(f"Автоматическое сопоставление: найдено {len(matches)} совпадений")
        
        return matches
    
    def get_processing_status(self) -> Dict:
        """Статус сервиса сопоставления"""
        return {
            'max_time_diff_minutes': self.MAX_TIME_DIFF_MINUTES,
            'similarity_threshold': self.SIMILARITY_THRESHOLD,
            'supported_languages': list(self.ITEM_KEYWORDS.keys()),
            'item_keywords': self.ITEM_KEYWORDS,
            'amount_keywords': self.AMOUNT_KEYWORDS
        } 