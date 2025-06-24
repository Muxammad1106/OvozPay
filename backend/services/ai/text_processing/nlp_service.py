"""
NLPService - Обработка естественного языка и извлечение финансовых данных
Извлекает суммы, валюты, категории и типы операций из текста
"""

import re
import logging
from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime, date
from decimal import Decimal, InvalidOperation

logger = logging.getLogger(__name__)


class NLPService:
    """Сервис для обработки естественного языка и извлечения финансовых данных"""
    
    def __init__(self):
        self.supported_languages = ['ru', 'uz', 'en']
        
        # Словари ключевых слов для классификации
        self._init_classification_dictionaries()
        
        # Паттерны для извлечения данных
        self._init_regex_patterns()
    
    def _init_classification_dictionaries(self) -> None:
        """Инициализирует словари для классификации операций и категорий"""
        
        # Ключевые слова для расходов
        self.expense_keywords = {
            'ru': [
                'потратил', 'купил', 'заплатил', 'оплатил', 'трата', 'расход',
                'покупка', 'платеж', 'счет', 'чек', 'магазин', 'супермаркет',
                'ресторан', 'кафе', 'такси', 'бензин', 'продукты', 'одежда'
            ],
            'uz': [
                'sotib oldim', 'pul sarfladim', 'to\'ladim', 'xarid', 'xarajat',
                'do\'kon', 'restoran', 'taksi', 'benzin', 'oziq-ovqat'
            ],
            'en': [
                'spent', 'bought', 'paid', 'purchase', 'expense', 'cost',
                'shop', 'store', 'restaurant', 'cafe', 'taxi', 'gas', 'food'
            ]
        }
        
        # Ключевые слова для доходов
        self.income_keywords = {
            'ru': [
                'получил', 'заработал', 'доход', 'зарплата', 'премия',
                'прибыль', 'выручка', 'продал', 'перевод', 'возврат'
            ],
            'uz': [
                'oldim', 'ishladim', 'daromad', 'maosh', 'premiya',
                'foyda', 'sotdim', 'pul oldi'
            ],
            'en': [
                'received', 'earned', 'income', 'salary', 'bonus',
                'profit', 'sold', 'transfer', 'refund'
            ]
        }
        
        # Категории расходов
        self.expense_categories = {
            'продукты': [
                'продукты', 'еда', 'пища', 'супермаркет', 'магазин', 'овощи',
                'фрукты', 'хлеб', 'молоко', 'мясо', 'рыба', 'grocery'
            ],
            'транспорт': [
                'такси', 'автобус', 'метро', 'бензин', 'топливо', 'парковка',
                'проезд', 'билет', 'taxi', 'bus', 'gas', 'fuel'
            ],
            'развлечения': [
                'кино', 'театр', 'концерт', 'ресторан', 'кафе', 'бар',
                'развлечения', 'отдых', 'cinema', 'restaurant', 'cafe'
            ],
            'одежда': [
                'одежда', 'обувь', 'куртка', 'рубашка', 'джинсы', 'платье',
                'костюм', 'clothes', 'shirt', 'shoes', 'jacket'
            ],
            'здоровье': [
                'аптека', 'лекарства', 'врач', 'больница', 'поликлиника',
                'медицина', 'анализы', 'pharmacy', 'medicine', 'doctor'
            ],
            'коммунальные': [
                'коммунальные', 'свет', 'газ', 'вода', 'интернет', 'телефон',
                'электричество', 'utilities', 'electricity', 'internet'
            ]
        }
        
        # Категории доходов
        self.income_categories = {
            'зарплата': [
                'зарплата', 'оклад', 'зп', 'работа', 'salary', 'wage', 'work'
            ],
            'фриланс': [
                'фриланс', 'проект', 'заказ', 'freelance', 'project', 'order'
            ],
            'продажи': [
                'продал', 'продажа', 'sold', 'sale', 'selling'
            ],
            'инвестиции': [
                'дивиденды', 'проценты', 'инвестиции', 'акции', 'dividends', 'investment'
            ]
        }
    
    def _init_regex_patterns(self) -> None:
        """Инициализирует регулярные выражения для извлечения данных"""
        
        # Паттерны для сумм с валютами
        self.amount_patterns = [
            # Российские рубли
            r'(\d{1,3}(?:\s?\d{3})*(?:[,.]\d{1,2})?)\s*(руб|рубл|₽|rub)',
            # Узбекские сумы
            r'(\d{1,3}(?:\s?\d{3})*(?:[,.]\d{1,2})?)\s*(сум|som|сом)',
            # Доллары США
            r'(\d{1,3}(?:\s?\d{3})*(?:[,.]\d{1,2})?)\s*(\$|долл|usd|dollar)',
            # Евро
            r'(\d{1,3}(?:\s?\d{3})*(?:[,.]\d{1,2})?)\s*(€|евро|eur|euro)',
            # Просто числа (предполагаем местную валюту)
            r'(\d{1,3}(?:\s?\d{3})*(?:[,.]\d{1,2})?)\s*(?:тысяч|тыс|к)?$'
        ]
        
        # Паттерны для дат
        self.date_patterns = [
            r'(\d{1,2})[./](\d{1,2})[./](\d{2,4})',  # DD.MM.YYYY или DD/MM/YYYY
            r'(\d{1,2})\s+(января|февраля|марта|апреля|мая|июня|июля|августа|сентября|октября|ноября|декабря)\s+(\d{2,4})',
            r'вчера',
            r'сегодня',
            r'позавчера'
        ]
    
    async def parse_transaction_text(
        self,
        text: str,
        user_language: str = 'ru'
    ) -> Dict[str, Any]:
        """
        Основная функция парсинга текста транзакции
        
        Args:
            text: Текст для анализа
            user_language: Язык пользователя
            
        Returns:
            Словарь с извлечёнными данными
        """
        try:
            text_clean = self._clean_text(text)
            
            result = {
                'original_text': text,
                'cleaned_text': text_clean,
                'transaction_type': None,
                'amount': None,
                'currency': 'UZS',  # По умолчанию сум
                'category': None,
                'description': text_clean,
                'date': None,
                'confidence': 0.0,
                'extracted_entities': {}
            }
            
            # Определяем тип операции
            transaction_type, type_confidence = self._classify_transaction_type(
                text_clean, user_language
            )
            result['transaction_type'] = transaction_type
            
            # Извлекаем сумму и валюту
            amount, currency, amount_confidence = self._extract_amount_and_currency(text_clean)
            result['amount'] = amount
            result['currency'] = currency
            
            # Определяем категорию
            category, category_confidence = self._classify_category(
                text_clean, transaction_type, user_language
            )
            result['category'] = category
            
            # Извлекаем дату
            extracted_date = self._extract_date(text_clean)
            result['date'] = extracted_date
            
            # Рассчитываем общую уверенность
            confidences = [type_confidence, amount_confidence, category_confidence]
            result['confidence'] = sum(confidences) / len(confidences)
            
            # Дополнительные метаданные
            result['extracted_entities'] = {
                'amounts_found': self._find_all_amounts(text_clean),
                'keywords_found': self._find_keywords(text_clean, user_language),
                'potential_shop_names': self._extract_shop_names(text_clean)
            }
            
            logger.info(
                f"Парсинг завершён: тип={transaction_type}, "
                f"сумма={amount} {currency}, категория={category}"
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Ошибка парсинга текста: {e}")
            return {
                'original_text': text,
                'error': str(e),
                'confidence': 0.0
            }
    
    def _clean_text(self, text: str) -> str:
        """Очищает и нормализует текст"""
        # Удаляем лишние пробелы
        text = re.sub(r'\s+', ' ', text.strip())
        
        # Приводим к нижнему регистру для анализа
        text = text.lower()
        
        # Удаляем специальные символы (кроме цифр и валют)
        text = re.sub(r'[^\w\s.,₽$€-]', '', text)
        
        return text
    
    def _classify_transaction_type(
        self,
        text: str,
        language: str
    ) -> Tuple[str, float]:
        """Определяет тип транзакции (доход/расход)"""
        
        expense_score = 0
        income_score = 0
        
        # Проверяем ключевые слова расходов
        expense_words = self.expense_keywords.get(language, self.expense_keywords['ru'])
        for keyword in expense_words:
            if keyword in text:
                expense_score += 1
        
        # Проверяем ключевые слова доходов
        income_words = self.income_keywords.get(language, self.income_keywords['ru'])
        for keyword in income_words:
            if keyword in text:
                income_score += 1
        
        # Дополнительные правила
        if any(word in text for word in ['купил', 'потратил', 'заплатил']):
            expense_score += 2
        
        if any(word in text for word in ['получил', 'заработал', 'продал']):
            income_score += 2
        
        # Определяем результат
        if expense_score > income_score:
            confidence = min(0.9, expense_score / (expense_score + income_score + 1))
            return 'expense', confidence
        elif income_score > expense_score:
            confidence = min(0.9, income_score / (expense_score + income_score + 1))
            return 'income', confidence
        else:
            # По умолчанию расход (как наиболее частая операция)
            return 'expense', 0.3
    
    def _extract_amount_and_currency(self, text: str) -> Tuple[Optional[float], str, float]:
        """Извлекает сумму и валюту из текста"""
        
        for pattern in self.amount_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            
            for match in matches:
                try:
                    if isinstance(match, tuple):
                        amount_str = match[0]
                        currency_str = match[1] if len(match) > 1 else ''
                    else:
                        amount_str = match
                        currency_str = ''
                    
                    # Очищаем сумму
                    amount_str = amount_str.replace(' ', '').replace(',', '.')
                    amount = float(amount_str)
                    
                    # Определяем валюту
                    currency = self._normalize_currency(currency_str)
                    
                    # Уверенность зависит от наличия валюты
                    confidence = 0.9 if currency_str else 0.6
                    
                    return amount, currency, confidence
                    
                except (ValueError, InvalidOperation):
                    continue
        
        return None, 'UZS', 0.0
    
    def _normalize_currency(self, currency_str: str) -> str:
        """Нормализует строку валюты к стандартному коду"""
        currency_str = currency_str.lower()
        
        currency_mapping = {
            'руб': 'RUB', 'рубл': 'RUB', '₽': 'RUB', 'rub': 'RUB',
            'сум': 'UZS', 'som': 'UZS', 'сом': 'UZS',
            '$': 'USD', 'долл': 'USD', 'usd': 'USD', 'dollar': 'USD',
            '€': 'EUR', 'евро': 'EUR', 'eur': 'EUR', 'euro': 'EUR'
        }
        
        return currency_mapping.get(currency_str, 'UZS')
    
    def _classify_category(
        self,
        text: str,
        transaction_type: str,
        language: str
    ) -> Tuple[Optional[str], float]:
        """Определяет категорию транзакции"""
        
        categories = (
            self.expense_categories if transaction_type == 'expense' 
            else self.income_categories
        )
        
        best_category = None
        best_score = 0
        
        for category, keywords in categories.items():
            score = 0
            for keyword in keywords:
                if keyword in text:
                    score += 1
            
            if score > best_score:
                best_score = score
                best_category = category
        
        if best_category:
            confidence = min(0.8, best_score / 3)  # Максимум 0.8
            return best_category, confidence
        
        # Категория по умолчанию
        default_category = 'другое' if transaction_type == 'expense' else 'прочие доходы'
        return default_category, 0.1
    
    def _extract_date(self, text: str) -> Optional[str]:
        """Извлекает дату из текста"""
        
        # Проверяем относительные даты
        if 'сегодня' in text:
            return date.today().isoformat()
        elif 'вчера' in text:
            yesterday = date.today().replace(day=date.today().day - 1)
            return yesterday.isoformat()
        
        # Проверяем абсолютные даты
        for pattern in self.date_patterns:
            matches = re.findall(pattern, text)
            if matches:
                # Пытаемся парсить дату
                try:
                    match = matches[0]
                    if isinstance(match, tuple) and len(match) >= 2:
                        day, month = int(match[0]), int(match[1])
                        year = int(match[2]) if len(match) > 2 else date.today().year
                        
                        # Корректируем год если он двузначный
                        if year < 100:
                            year += 2000
                        
                        extracted_date = date(year, month, day)
                        return extracted_date.isoformat()
                except (ValueError, IndexError):
                    continue
        
        return None
    
    def _find_all_amounts(self, text: str) -> List[float]:
        """Находит все числовые значения в тексте"""
        amounts = []
        
        for pattern in self.amount_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                try:
                    if isinstance(match, tuple):
                        amount_str = match[0]
                    else:
                        amount_str = match
                    
                    amount_str = amount_str.replace(' ', '').replace(',', '.')
                    amount = float(amount_str)
                    amounts.append(amount)
                except ValueError:
                    continue
        
        return amounts
    
    def _find_keywords(self, text: str, language: str) -> List[str]:
        """Находит все ключевые слова в тексте"""
        found_keywords = []
        
        all_keywords = (
            self.expense_keywords.get(language, []) + 
            self.income_keywords.get(language, [])
        )
        
        for keyword in all_keywords:
            if keyword in text:
                found_keywords.append(keyword)
        
        return found_keywords
    
    def _extract_shop_names(self, text: str) -> List[str]:
        """Извлекает потенциальные названия магазинов"""
        # Простая эвристика для нахождения названий
        words = text.split()
        potential_names = []
        
        for i, word in enumerate(words):
            # Ищем слова после предлогов "в", "на", "из"
            if word in ['в', 'на', 'из'] and i + 1 < len(words):
                next_word = words[i + 1]
                if len(next_word) > 2 and not next_word.isdigit():
                    potential_names.append(next_word)
        
        return potential_names
    
    async def extract_amounts(self, text: str) -> List[Dict[str, Any]]:
        """
        Извлекает все суммы из текста
        
        Args:
            text: Входной текст
            
        Returns:
            Список найденных сумм с дополнительной информацией
        """
        try:
            amounts_data = []
            
            for pattern in self.amount_patterns:
                matches = re.findall(pattern, text, re.IGNORECASE)
                
                for match in matches:
                    try:
                        if isinstance(match, tuple):
                            amount_str = match[0]
                            currency_str = match[1] if len(match) > 1 else ''
                        else:
                            amount_str = match
                            currency_str = ''
                        
                        # Очищаем и конвертируем сумму
                        amount_str = amount_str.replace(' ', '').replace(',', '.')
                        amount = float(amount_str)
                        
                        if amount > 0:
                            amounts_data.append({
                                'amount': amount,
                                'currency': self._normalize_currency(currency_str),
                                'raw_text': match,
                                'confidence': 0.9 if currency_str else 0.6
                            })
                            
                    except (ValueError, TypeError):
                        continue
            
            logger.info(f"Найдено сумм: {len(amounts_data)}")
            return amounts_data
            
        except Exception as e:
            logger.error(f"Ошибка извлечения сумм: {e}")
            return []

    async def classify_category(self, text: str, transaction_type: str = 'expense') -> Optional[str]:
        """
        Классифицирует категорию транзакции
        
        Args:
            text: Входной текст
            transaction_type: Тип транзакции ('expense' или 'income')
            
        Returns:
            Название категории или None
        """
        try:
            category, confidence = self._classify_category(text, transaction_type, 'ru')
            
            if confidence > 0.3:
                logger.info(f"Категория определена: {category} (уверенность: {confidence:.2f})")
                return category
            else:
                logger.warning(f"Низкая уверенность категории: {category} ({confidence:.2f})")
                return category  # Возвращаем даже при низкой уверенности
                
        except Exception as e:
            logger.error(f"Ошибка классификации категории: {e}")
            return None

    def get_service_status(self) -> Dict[str, Any]:
        """Возвращает статус сервиса"""
        return {
            'service': 'NLPService',
            'status': 'active',
            'supported_languages': self.supported_languages,
            'expense_categories': list(self.expense_categories.keys()),
            'income_categories': list(self.income_categories.keys()),
            'amount_patterns_count': len(self.amount_patterns),
            'keywords_loaded': {
                lang: len(keywords) 
                for lang, keywords in self.expense_keywords.items()
            }
        }


# Глобальный экземпляр сервиса
nlp_service = NLPService()


# Функции-обёртки для удобства использования
async def parse_financial_text(
    text: str,
    language: str = 'ru'
) -> Dict[str, Any]:
    """
    Упрощённая функция для парсинга финансового текста
    
    Args:
        text: Текст для анализа
        language: Язык текста
        
    Returns:
        Структурированные финансовые данные
    """
    return await nlp_service.parse_transaction_text(text, language)


def sync_parse_financial_text(
    text: str,
    language: str = 'ru'
) -> Dict[str, Any]:
    """Синхронная версия парсинга финансового текста"""
    import asyncio
    return asyncio.run(parse_financial_text(text, language)) 