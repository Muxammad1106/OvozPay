"""
Сервис для парсинга текстовых транзакций
Поддерживает различные валюты и автоматическое создание категорий
"""

import re
import logging
from typing import Dict, Any, Optional, List
from decimal import Decimal, InvalidOperation

logger = logging.getLogger(__name__)


class TextParserService:
    """Сервис для парсинга текстовых команд пользователей"""
    
    def __init__(self):
        # Паттерны для валют
        self.currency_patterns = {
            'UZS': [
                r'(\d+(?:\s*\d+)*)\s*сум(?:ов|а|ов)?',
                r'(\d+(?:\s*\d+)*)\s*uzs',
                r'(\d+(?:\s*\d+)*)\s*so\'m',
                r'(\d+(?:\s*\d+)*)\s*сўм',
            ],
            'USD': [
                r'(\d+(?:\s*\d+)*)\s*(?:\$|доллар(?:ов|а)?|usd|dollar)',
                r'\$\s*(\d+(?:\s*\d+)*)',
            ],
            'EUR': [
                r'(\d+(?:\s*\d+)*)\s*(?:евро|eur|€)',
                r'€\s*(\d+(?:\s*\d+)*)',
            ],
            'RUB': [
                r'(\d+(?:\s*\d+)*)\s*(?:рубл(?:ей|я|ь)|руб|rub)',
            ]
        }
        
        # Ключевые слова для типов транзакций
        self.expense_keywords = {
            'ru': ['потратил', 'купил', 'заплатил', 'потрачено', 'расход', 'трата', 'оплатил', 'заплачено'],
            'en': ['spent', 'bought', 'paid', 'expense', 'cost', 'purchase'],
            'uz': ['sarfladim', 'sotib oldim', 'to\'ladim', 'xarajat', 'pul sarflandi']
        }
        
        self.income_keywords = {
            'ru': ['заработал', 'получил', 'доход', 'зарплата', 'прибыль', 'заработано'],
            'en': ['earned', 'received', 'income', 'salary', 'profit', 'got'],
            'uz': ['ishlab topdim', 'oldim', 'daromad', 'maosh', 'foyda']
        }
        
        # Автоматические категории
        self.auto_categories = {
            'ru': {
                'еда': ['продукты', 'молоко', 'хлеб', 'мясо', 'овощи', 'фрукты', 'еда', 'ресторан', 'кафе', 'яблоки', 'картошка'],
                'транспорт': ['бензин', 'топливо', 'автобус', 'метро', 'такси', 'машина', 'авто', 'проезд'],
                'коммунальные': ['свет', 'газ', 'вода', 'интернет', 'телефон', 'коммуналка'],
                'одежда': ['одежда', 'обувь', 'куртка', 'джинсы', 'платье', 'рубашка'],
                'развлечения': ['кино', 'театр', 'игры', 'книги', 'музыка'],
                'здоровье': ['лекарства', 'врач', 'больница', 'аптека', 'медицина'],
                'работа': ['зарплата', 'премия', 'работа', 'подработка']
            },
            'en': {
                'food': ['groceries', 'milk', 'bread', 'meat', 'vegetables', 'fruits', 'food', 'restaurant', 'cafe', 'apples'],
                'transport': ['gas', 'fuel', 'bus', 'metro', 'taxi', 'car', 'auto'],
                'utilities': ['electricity', 'gas', 'water', 'internet', 'phone'],
                'clothing': ['clothes', 'shoes', 'jacket', 'jeans', 'dress', 'shirt'],
                'entertainment': ['cinema', 'movies', 'games', 'books', 'music'],
                'health': ['medicine', 'doctor', 'hospital', 'pharmacy'],
                'work': ['salary', 'bonus', 'work', 'job']
            },
            'uz': {
                'oziq-ovqat': ['mahsulotlar', 'sut', 'non', 'go\'sht', 'sabzavot', 'meva', 'ovqat', 'restoran'],
                'transport': ['benzin', 'yoqilg\'i', 'avtobus', 'metro', 'taksi', 'mashina'],
                'kommunal': ['elektr', 'gaz', 'suv', 'internet', 'telefon'],
                'kiyim': ['kiyim', 'oyoq kiyim', 'kurtka', 'jinsi', 'ko\'ylak'],
                'o\'yin-kulgi': ['kino', 'teatr', 'o\'yinlar', 'kitoblar', 'musiqa'],
                'salomatlik': ['dori', 'shifokor', 'kasalxona', 'dorixona'],
                'ish': ['maosh', 'mukofot', 'ish', 'ishlab topish']
            }
        }
    
    def parse_transaction_text(self, text: str, language: str = 'ru') -> Optional[Dict[str, Any]]:
        """
        Основной метод парсинга транзакции из текста
        
        Args:
            text: Текст для парсинга
            language: Язык текста
            
        Returns:
            Словарь с данными транзакции или None
        """
        try:
            text = text.lower().strip()
            
            # 1. Определяем тип транзакции
            transaction_type = self._detect_transaction_type(text, language)
            if not transaction_type:
                return None
            
            # 2. Извлекаем сумму и валюту
            amount, currency = self._extract_amount_and_currency(text)
            if not amount:
                return None
            
            # 3. Извлекаем описание и автоматически определяем категорию
            description, category = self._extract_description_and_category(text, language)
            
            return {
                'type': transaction_type,
                'amount': amount,
                'currency': currency,
                'description': description,
                'category': category,
                'source': 'text'
            }
            
        except Exception as e:
            logger.error(f"Error parsing transaction text: {e}")
            return None
    
    def _detect_transaction_type(self, text: str, language: str) -> Optional[str]:
        """Определяет тип транзакции (доход/расход)"""
        
        # Проверяем ключевые слова расходов
        expense_words = self.expense_keywords.get(language, [])
        for word in expense_words:
            if word in text:
                logger.info(f"Detected expense by keyword: '{word}'")
                return 'expense'
        
        # Проверяем ключевые слова доходов  
        income_words = self.income_keywords.get(language, [])
        for word in income_words:
            if word in text:
                logger.info(f"Detected income by keyword: '{word}'")
                return 'income'
        
        # Если есть числа и нет ключевых слов - считаем расходом
        if re.search(r'\d+', text):
            logger.info("No keywords found, defaulting to expense")
            return 'expense'
        
        logger.warning(f"Could not detect transaction type for: '{text}'")
        return None
    
    def _extract_amount_and_currency(self, text: str) -> tuple[Optional[Decimal], str]:
        """Извлекает сумму и валюту из текста"""
        
        # Проверяем каждую валюту
        for currency, patterns in self.currency_patterns.items():
            for pattern in patterns:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    amount_str = match.group(1).replace(' ', '').replace(',', '')
                    try:
                        amount = Decimal(amount_str)
                        logger.info(f"Found {amount} {currency} using pattern: {pattern}")
                        return amount, currency
                    except (InvalidOperation, ValueError) as e:
                        logger.warning(f"Failed to parse amount '{amount_str}': {e}")
                        continue
        
        # Попытка найти просто число (более гибкий паттерн)
        number_patterns = [
            r'(\d+(?:[\s,]*\d+)*)',  # 10000 или 10 000 или 10,000
            r'(\d+\.?\d*)',          # 10000.50
            r'(\d+)',                # просто число
        ]
        
        for pattern in number_patterns:
            match = re.search(pattern, text)
            if match:
                amount_str = match.group(1).replace(' ', '').replace(',', '')
                try:
                    amount = Decimal(amount_str)
                    if amount > 0:  # Проверяем что сумма положительная
                        logger.info(f"Found number {amount} (defaulting to UZS)")
                        return amount, 'UZS'  # По умолчанию сум
                except (InvalidOperation, ValueError) as e:
                    logger.warning(f"Failed to parse number '{amount_str}': {e}")
                    continue
        
        logger.warning(f"No amount found in text: '{text}'")
        return None, 'UZS'
    
    def _extract_description_and_category(self, text: str, language: str) -> tuple[str, str]:
        """Извлекает описание и автоматически определяет категорию"""
        
        # Убираем ключевые слова транзакций и суммы
        clean_text = text
        
        # Убираем ключевые слова
        all_keywords = (
            self.expense_keywords.get(language, []) + 
            self.income_keywords.get(language, [])
        )
        
        for keyword in all_keywords:
            clean_text = re.sub(rf'\b{re.escape(keyword)}\b', '', clean_text, flags=re.IGNORECASE)
        
        # Убираем валютные паттерны
        for currency, patterns in self.currency_patterns.items():
            for pattern in patterns:
                clean_text = re.sub(pattern, '', clean_text, flags=re.IGNORECASE)
        
        # Убираем просто числа (которые остались после валютных паттернов)
        clean_text = re.sub(r'\b\d+(?:[\s,]*\d+)*\b', '', clean_text)
        
        # Убираем предлоги и артикли
        prepositions = {
            'ru': ['на', 'за', 'в', 'с', 'для', 'по', 'из', 'к', 'у', 'о'],
            'en': ['on', 'for', 'in', 'with', 'to', 'from', 'at', 'by', 'of'],
            'uz': ['uchun', 'bilan', 'dan', 'ga', 'da', 'ning']
        }
        
        for prep in prepositions.get(language, []):
            clean_text = re.sub(rf'\b{re.escape(prep)}\b', '', clean_text, flags=re.IGNORECASE)
        
        # Очищаем и нормализуем
        description = ' '.join(clean_text.split()).strip()
        
        # Если описание пустое, ставим значение по умолчанию
        if not description:
            default_descriptions = {
                'ru': 'покупка',
                'en': 'purchase',
                'uz': 'xarid'
            }
            description = default_descriptions.get(language, 'покупка')
        
        # Определяем категорию
        category = self._auto_detect_category(description, language)
        
        return description, category
    
    def _auto_detect_category(self, description: str, language: str) -> str:
        """Автоматически определяет категорию по описанию"""
        
        categories = self.auto_categories.get(language, {})
        
        # Проверяем каждую категорию
        for category_name, keywords in categories.items():
            for keyword in keywords:
                if keyword.lower() in description.lower():
                    return category_name
        
        # Категория по умолчанию
        default_categories = {
            'ru': 'прочее',
            'en': 'other', 
            'uz': 'boshqa'
        }
        
        return default_categories.get(language, 'прочее')

    def get_currency_display_name(self, currency: str, language: str = 'ru') -> str:
        """Возвращает отображаемое название валюты"""
        
        currency_names = {
            'UZS': {
                'ru': 'сум',
                'en': 'som',
                'uz': 'so\'m'
            },
            'USD': {
                'ru': 'доллар',
                'en': 'dollar', 
                'uz': 'dollar'
            },
            'EUR': {
                'ru': 'евро',
                'en': 'euro',
                'uz': 'evro'  
            },
            'RUB': {
                'ru': 'рубль',
                'en': 'ruble',
                'uz': 'rubl'
            }
        }
        
        return currency_names.get(currency, {}).get(language, currency)

    def test_parsing(self) -> None:
        """Тестирует парсинг различных вариантов"""
        
        test_cases = [
            "потратил 10000 сум на продукты",
            "купил молоко за 5000",
            "заработал 1000 долларов",
            "потратил 50$ на бензин",
            "заплатил 200 евро за одежду",
            "получил зарплату 2000000 сум",
        ]
        
        for case in test_cases:
            result = self.parse_transaction_text(case)
            print(f"'{case}' -> {result}") 