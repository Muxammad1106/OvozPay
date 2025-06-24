"""
Сервис для парсинга голосовых команд и извлечения транзакций
"""

import re
import logging
from decimal import Decimal, InvalidOperation
from typing import Dict, Any, Optional, List, Tuple

logger = logging.getLogger(__name__)


class VoiceParserService:
    """Сервис для парсинга голосовых команд и извлечения данных о транзакциях"""
    
    def __init__(self):
        # Ключевые слова для определения типа транзакции
        self.expense_keywords = {
            'ru': [
                'потратил', 'трата', 'купил', 'заплатил', 'оплатил', 'потрачено',
                'расход', 'израсходовал', 'кто-то', 'минус', 'вычесть'
            ],
            'en': [
                'spent', 'bought', 'paid', 'expense', 'cost', 'minus'
            ],
            'uz': [
                'sarfladim', 'xarid', 'to\'ladim', 'chiqim'
            ]
        }
        
        self.income_keywords = {
            'ru': [
                'заработал', 'получил', 'доход', 'зарплата', 'прибыль',
                'заработок', 'плюс', 'добавить', 'пришло'
            ],
            'en': [
                'earned', 'received', 'income', 'salary', 'profit', 'plus'
            ],
            'uz': [
                'topдim', 'olдim', 'daromad', 'maosh'
            ]
        }
        
        # Категории для автоклассификации
        self.expense_categories = {
            'ru': {
                'еда': ['еда', 'продукты', 'магазин', 'ресторан', 'кафе', 'пицца', 'обед', 'ужин'],
                'транспорт': ['такси', 'автобус', 'метро', 'бензин', 'билет', 'поездка'],
                'покупки': ['одежда', 'обувь', 'магазин', 'покупки', 'шопинг'],
                'здоровье': ['врач', 'лекарство', 'аптека', 'больница', 'таблетки'],
                'развлечения': ['кино', 'театр', 'игры', 'концерт', 'клуб'],
                'жкх': ['квартплата', 'коммуналка', 'свет', 'газ', 'вода', 'интернет'],
                'другое': []
            },
            'en': {
                'food': ['food', 'grocery', 'restaurant', 'cafe', 'lunch', 'dinner'],
                'transport': ['taxi', 'bus', 'subway', 'gas', 'ticket', 'trip'],
                'shopping': ['clothes', 'shoes', 'shopping', 'store'],
                'health': ['doctor', 'medicine', 'pharmacy', 'hospital'],
                'entertainment': ['movie', 'theater', 'games', 'concert'],
                'utilities': ['rent', 'electricity', 'gas', 'water', 'internet'],
                'other': []
            }
        }
        
        self.income_categories = {
            'ru': {
                'зарплата': ['зарплата', 'работа', 'оклад'],
                'фриланс': ['фриланс', 'заказ', 'проект'],
                'продажи': ['продал', 'продажа', 'реализация'],
                'другое': []
            },
            'en': {
                'salary': ['salary', 'wage', 'work'],
                'freelance': ['freelance', 'project', 'order'],
                'sales': ['sold', 'sale'],
                'other': []
            }
        }
    
    def parse_voice_text(self, text: str, language: str = 'ru') -> Optional[Dict[str, Any]]:
        """
        Парсит распознанный текст и извлекает данные о транзакции
        
        Args:
            text: Распознанный текст
            language: Язык текста
            
        Returns:
            Dict с данными транзакции или None
        """
        if not text or not text.strip():
            return None
        
        text = text.lower().strip()
        logger.info(f"Парсим текст: '{text}' (язык: {language})")
        
        try:
            # 1. Определяем тип транзакции
            transaction_type = self._detect_transaction_type(text, language)
            if not transaction_type:
                logger.warning(f"Не удалось определить тип транзакции: {text}")
                return None
            
            # 2. Извлекаем сумму
            amount = self._extract_amount(text)
            if not amount:
                logger.warning(f"Не удалось найти сумму в тексте: {text}")
                return None
            
            # 3. Определяем категорию
            category = self._classify_category(text, transaction_type, language)
            
            # 4. Извлекаем описание
            description = self._extract_description(text, amount)
            
            result = {
                'type': transaction_type,
                'amount': amount,
                'category': category,
                'description': description,
                'confidence': self._calculate_confidence(text, transaction_type, amount, category)
            }
            
            logger.info(f"Распознано: {result}")
            return result
            
        except Exception as e:
            logger.error(f"Ошибка парсинга текста: {e}")
            return None
    
    def _detect_transaction_type(self, text: str, language: str = 'ru') -> Optional[str]:
        """Определяет тип транзакции (доход/расход)"""
        
        expense_words = self.expense_keywords.get(language, self.expense_keywords['ru'])
        income_words = self.income_keywords.get(language, self.income_keywords['ru'])
        
        expense_score = sum(1 for word in expense_words if word in text)
        income_score = sum(1 for word in income_words if word in text)
        
        if expense_score > income_score:
            return 'expense'
        elif income_score > expense_score:
            return 'income'
        
        # Если не определено, считаем расходом (чаще встречается)
        return 'expense'
    
    def _extract_amount(self, text: str) -> Optional[Decimal]:
        """Извлекает сумму из текста"""
        
        # Паттерны для поиска сумм
        patterns = [
            r'(\d+[\s,.]?\d*)\s*(?:сум|som|рубл|руб|доллар|usd|евро|eur)',  # С валютой
            r'(\d+[\s,.]?\d*)\s*(?:тысяч|тыс|к)',  # Тысячи
            r'(\d{1,3}(?:[\s,]\d{3})*(?:[.,]\d{2})?)',  # Числа с разделителями
            r'(\d+[.,]?\d*)',  # Простые числа
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                for match in matches:
                    try:
                        # Очищаем и конвертируем
                        amount_str = match.replace(' ', '').replace(',', '.')
                        amount = Decimal(amount_str)
                        
                        # Проверяем на разумность
                        if 1 <= amount <= 999999999:
                            # Обрабатываем тысячи
                            if 'тысяч' in text or 'тыс' in text or 'к' in text.split():
                                amount *= 1000
                            
                            return amount
                            
                    except (ValueError, InvalidOperation):
                        continue
        
        return None
    
    def _classify_category(self, text: str, transaction_type: str, language: str = 'ru') -> str:
        """Классифицирует категорию транзакции"""
        
        categories = (
            self.expense_categories.get(language, self.expense_categories['ru'])
            if transaction_type == 'expense'
            else self.income_categories.get(language, self.income_categories['ru'])
        )
        
        best_category = None
        best_score = 0
        
        for category, keywords in categories.items():
            score = sum(1 for keyword in keywords if keyword in text)
            if score > best_score:
                best_score = score
                best_category = category
        
        # Возвращаем найденную категорию или дефолтную
        return best_category or ('другое' if transaction_type == 'expense' else 'другое')
    
    def _extract_description(self, text: str, amount: Decimal) -> str:
        """Извлекает описание транзакции"""
        
        # Убираем числа и общие слова
        description = text
        
        # Убираем сумму
        amount_str = str(amount).replace('.', '[.,]')
        description = re.sub(rf'\b{amount_str}\b', '', description)
        
        # Убираем служебные слова
        stop_words = [
            'потратил', 'заплатил', 'купил', 'трата', 'расход',
            'заработал', 'получил', 'доход',
            'сум', 'рубл', 'руб', 'доллар', 'usd', 'евро', 'eur',
            'тысяч', 'тыс', 'на', 'за', 'в', 'для'
        ]
        
        for word in stop_words:
            description = description.replace(word, '')
        
        # Очищаем и обрезаем
        description = ' '.join(description.split())[:100]
        
        return description.strip() or 'Голосовая команда'
    
    def _calculate_confidence(
        self,
        text: str,
        transaction_type: str,
        amount: Decimal,
        category: str
    ) -> float:
        """Рассчитывает уверенность в правильности парсинга"""
        
        confidence = 0.5  # Базовая уверенность
        
        # Бонус за ясный тип транзакции
        type_keywords = (
            self.expense_keywords['ru'] + 
            self.income_keywords['ru']
        )
        if any(word in text for word in type_keywords):
            confidence += 0.2
        
        # Бонус за ясную сумму
        if amount and amount > 10:
            confidence += 0.2
        
        # Бонус за определенную категорию
        if category != 'другое':
            confidence += 0.1
        
        return min(confidence, 1.0)
    
    def is_valid_transaction_text(self, text: str) -> bool:
        """Проверяет, содержит ли текст данные о транзакции"""
        if not text or len(text.strip()) < 3:
            return False
        
        text = text.lower()
        
        # Проверяем наличие числа
        has_number = bool(re.search(r'\d+', text))
        
        # Проверяем наличие ключевых слов
        all_keywords = []
        for lang in ['ru', 'en', 'uz']:
            all_keywords.extend(self.expense_keywords.get(lang, []))
            all_keywords.extend(self.income_keywords.get(lang, []))
        
        has_keywords = any(word in text for word in all_keywords)
        
        return has_number and has_keywords 