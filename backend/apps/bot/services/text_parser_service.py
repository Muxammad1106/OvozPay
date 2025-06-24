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
        # Улучшенные паттерны для валют
        self.currency_patterns = {
            'UZS': [
                r'(\d+(?:[,\s]\d{3})*(?:[,.]\d{1,2})?)\s*сум(?:ов|а|ов)?',
                r'(\d+(?:[,\s]\d{3})*(?:[,.]\d{1,2})?)\s*uzs',
                r'(\d+(?:[,\s]\d{3})*(?:[,.]\d{1,2})?)\s*so\'m',
                r'(\d+(?:[,\s]\d{3})*(?:[,.]\d{1,2})?)\s*сўм',
                r'(\d+(?:[,\s]\d{3})*(?:[,.]\d{1,2})?)\s*som',
            ],
            'USD': [
                r'(\d+(?:[,\s]\d{3})*(?:[,.]\d{1,2})?)\s*(?:\$|доллар(?:ов|а)?|usd|dollar)',
                r'\$\s*(\d+(?:[,\s]\d{3})*(?:[,.]\d{1,2})?)',
                r'(\d+(?:[,\s]\d{3})*(?:[,.]\d{1,2})?)\s*бакс',
            ],
            'EUR': [
                r'(\d+(?:[,\s]\d{3})*(?:[,.]\d{1,2})?)\s*(?:евро|eur|€)',
                r'€\s*(\d+(?:[,\s]\d{3})*(?:[,.]\d{1,2})?)',
            ],
            'RUB': [
                r'(\d+(?:[,\s]\d{3})*(?:[,.]\d{1,2})?)\s*(?:рубл(?:ей|я|ь)|руб|rub)',
                r'(\d+(?:[,\s]\d{3})*(?:[,.]\d{1,2})?)\s*₽',
            ]
        }
        
        # Словарь для распознавания чисел словами
        self.number_words = {
            'ru': {
                'один': 1, 'одна': 1, 'одну': 1, 'одной': 1,
                'два': 2, 'две': 2, 'двух': 2,
                'три': 3, 'трех': 3, 'трём': 3,
                'четыре': 4, 'четырех': 4, 'четырём': 4,
                'пять': 5, 'пяти': 5, 'пятью': 5,
                'шесть': 6, 'шести': 6, 'шестью': 6,
                'семь': 7, 'семи': 7, 'семью': 7,
                'восемь': 8, 'восьми': 8, 'восемью': 8,
                'девять': 9, 'девяти': 9, 'девятью': 9,
                'десять': 10, 'десяти': 10, 'десятью': 10,
                'одиннадцать': 11, 'одиннадцати': 11,
                'двенадцать': 12, 'двенадцати': 12,
                'тринадцать': 13, 'тринадцати': 13,
                'четырнадцать': 14, 'четырнадцати': 14,
                'пятнадцать': 15, 'пятнадцати': 15,
                'шестнадцать': 16, 'шестнадцати': 16,
                'семнадцать': 17, 'семнадцати': 17,
                'восемнадцать': 18, 'восемнадцати': 18,
                'девятнадцать': 19, 'девятнадцати': 19,
                'двадцать': 20, 'двадцати': 20, 'двадцатью': 20,
                'тридцать': 30, 'тридцати': 30, 'тридцатью': 30,
                'сорок': 40, 'сорока': 40,
                'пятьдесят': 50, 'пятидесяти': 50, 'пятьюдесятью': 50,
                'шестьдесят': 60, 'шестидесяти': 60,
                'семьдесят': 70, 'семидесяти': 70,
                'восемьдесят': 80, 'восьмидесяти': 80,
                'девяносто': 90, 'девяноста': 90,
                'сто': 100, 'ста': 100, 'сотню': 100,
                'двести': 200, 'двухсот': 200,
                'триста': 300, 'трехсот': 300,
                'четыреста': 400, 'четырехсот': 400,
                'пятьсот': 500, 'пятисот': 500,
                'шестьсот': 600, 'шестисот': 600,
                'семьсот': 700, 'семисот': 700,
                'восемьсот': 800, 'восьмисот': 800,
                'девятьсот': 900, 'девятисот': 900,
                'тысяча': 1000, 'тысячи': 1000, 'тысяч': 1000, 'тысячу': 1000,
                'миллион': 1000000, 'миллиона': 1000000, 'миллионов': 1000000,
                'миллиард': 1000000000, 'миллиарда': 1000000000, 'миллиардов': 1000000000
            }
        }
        
        # Ключевые слова для типов транзакций
        self.expense_keywords = {
            'ru': ['потратил', 'купил', 'заплатил', 'потрачено', 'расход', 'трата', 'оплатил', 'заплачено', 'взял', 'приобрел', 'истратил', 'потрати'],
            'en': ['spent', 'bought', 'paid', 'expense', 'cost', 'purchase', 'got', 'acquired', 'buy'],
            'uz': ['sarfladim', 'sotib oldim', 'to\'ladim', 'xarajat', 'pul sarflandi', 'sotib oldi']
        }
        
        # Команды управления настройками + КОМАНДЫ УДАЛЕНИЯ
        self.management_keywords = {
            'ru': {
                'language': ['поменяй язык', 'смени язык', 'установи язык', 'язык на', 'переключи язык'],
                'currency': ['смени валюту', 'поменяй валюту', 'установи валюту', 'валюта на', 'сделай валютой'],
                'create_category': ['создай категорию', 'добавь категорию', 'новая категория'],
                'delete_category': ['удали категорию', 'удалить категорию', 'убери категорию', 'стереть категорию'],
                'delete_transaction': ['удали транзакцию', 'удалить транзакцию', 'отмени операцию', 'убери операцию']
            },
            'en': {
                'language': ['change language', 'set language', 'switch language', 'language to'],
                'currency': ['change currency', 'set currency', 'switch currency', 'currency to'],
                'create_category': ['create category', 'add category', 'new category'],
                'delete_category': ['delete category', 'remove category', 'erase category'],
                'delete_transaction': ['delete transaction', 'remove transaction', 'cancel operation']
            },
            'uz': {
                'language': ['tilni o\'zgartir', 'til o\'rnat', 'tilni almashtir'],
                'currency': ['valyutani o\'zgartir', 'valyuta o\'rnat', 'valyutani almashtir'],
                'create_category': ['kategoriya yarat', 'kategoriya qo\'sh', 'yangi kategoriya'],
                'delete_category': ['kategoriyani o\'chir', 'kategoriya o\'chir', 'kategoriyani olib tashla'],
                'delete_transaction': ['operatsiyani o\'chir', 'tranzaksiyani o\'chir', 'operatsiya bekor qil']
            }
        }
        
        self.income_keywords = {
            'ru': ['заработал', 'получил', 'доход', 'зарплата', 'прибыль', 'заработано', 'поступило'],
            'en': ['earned', 'received', 'income', 'salary', 'profit', 'got'],
            'uz': ['ishlab topdim', 'oldim', 'daromad', 'maosh', 'foyda']
        }
        
        # ЗНАЧИТЕЛЬНО РАСШИРЕННЫЕ автоматические категории с огромным количеством товаров
        self.auto_categories = {
            'ru': {
                'еда': [
                    # Молочные продукты
                    'молоко', 'кефир', 'ряженка', 'йогурт', 'творог', 'сметана', 'масло сливочное', 'сыр', 'брынза', 'кисломолочные',
                    
                    # Хлебобулочные
                    'хлеб', 'батон', 'багет', 'лаваш', 'сдоба', 'булочки', 'печенье', 'торт', 'пирожки', 'кекс',
                    
                    # Мясо и рыба
                    'мясо', 'говядина', 'свинина', 'баранина', 'курица', 'индейка', 'колбаса', 'сосиски', 'ветчина', 'рыба', 'семга', 'окунь', 'треска',
                    
                    # Овощи и фрукты
                    'овощи', 'фрукты', 'яблоки', 'бананы', 'апельсины', 'мандарины', 'груши', 'виноград', 'картошка', 'лук', 'морковь', 'капуста', 'помидоры', 'огурцы', 'перец', 'свекла',
                    
                    # Крупы и макароны
                    'рис', 'гречка', 'овсянка', 'манка', 'макароны', 'спагетти', 'лапша', 'пшено', 'перловка',
                    
                    # Консервы и заморозка
                    'консервы', 'тушенка', 'компот', 'варенье', 'мороженое', 'замороженные овощи', 'пельмени', 'вареники',
                    
                    # Приправы и соусы
                    'соль', 'сахар', 'мука', 'масло растительное', 'уксус', 'приправы', 'кетчуп', 'майонез', 'горчица',
                    
                    # Напитки
                    'вода', 'сок', 'лимонад', 'чай', 'кофе', 'пиво', 'вино', 'коньяк', 'водка',
                    
                    # Общие
                    'продукты', 'еда', 'пища', 'супермаркет', 'магазин продуктов', 'продуктовый', 'гастроном', 'ресторан', 'кафе', 'столовая', 'обед', 'ужин', 'завтрак'
                ],
                
                'транспорт': [
                    'бензин', 'топливо', 'дизель', 'газ пропан', 'автобус', 'метро', 'машина', 'авто', 'автомобиль', 'проезд', 'парковка', 'гараж', 'мойка', 'шиномонтаж', 'техосмотр', 'страховка авто', 'запчасти'
                ],
                
                'такси': [
                    'такси', 'uber', 'yandex такси', 'яндекс такси', 'bolt', 'поездка', 'машина такси', 'трансфер'
                ],
                
                'коммунальные': [
                    'свет', 'электричество', 'газ', 'вода', 'интернет', 'телефон', 'коммуналка', 'коммунальные', 'отопление', 'канализация', 'домофон', 'кабельное тв', 'мобильная связь'
                ],
                
                'одежда': [
                    # Верхняя одежда
                    'одежда', 'куртка', 'пальто', 'шуба', 'плащ', 'ветровка', 'пуховик',
                    
                    # Обувь
                    'обувь', 'ботинки', 'сапоги', 'туфли', 'кроссовки', 'тапочки', 'сандалии', 'босоножки',
                    
                    # Повседневная одежда
                    'джинсы', 'брюки', 'штаны', 'юбка', 'платье', 'рубашка', 'блузка', 'футболка', 'свитер', 'кофта', 'пиджак', 'костюм',
                    
                    # Нижнее белье и аксессуары
                    'белье', 'носки', 'колготки', 'трусы', 'бюстгальтер', 'шапка', 'шарф', 'перчатки', 'ремень', 'сумка', 'рюкзак',
                    
                    # Места покупок
                    'магазин одежды', 'бутик', 'секонд-хенд'
                ],
                
                'развлечения': [
                    'кино', 'театр', 'игры', 'книги', 'музыка', 'концерт', 'клуб', 'дискотека', 'боулинг', 'бильярд', 'караоке', 'парк развлечений', 'аттракционы', 'цирк', 'музей', 'выставка'
                ],
                
                'здоровье': [
                    'лекарства', 'врач', 'больница', 'аптека', 'медицина', 'поликлиника', 'стоматолог', 'анализы', 'узи', 'рентген', 'прививка', 'операция', 'массаж', 'физиотерапия'
                ],
                
                'работа': [
                    'зарплата', 'премия', 'работа', 'подработка', 'бонус', 'аванс', 'доплата', 'надбавка'
                ],
                
                'вредные привычки': [
                    'сигареты', 'курение', 'табак', 'сигары', 'кальян', 'алкоголь', 'пиво', 'вино', 'водка', 'коньяк', 'виски', 'шампанское', 'самогон'
                ],
                
                'красота': [
                    'парикмахер', 'маникюр', 'педикюр', 'салон красоты', 'косметика', 'крем', 'шампунь', 'мыло', 'духи', 'помада', 'тушь', 'стрижка', 'окрашивание', 'укладка'
                ],
                
                'образование': [
                    'курсы', 'книги', 'обучение', 'университет', 'школа', 'репетитор', 'семинар', 'тренинг', 'мастер-класс', 'учебники', 'канцелярия', 'тетради', 'ручки'
                ],
                
                'дом': [
                    # Мебель
                    'мебель', 'диван', 'кровать', 'стол', 'стул', 'шкаф', 'комод', 'полка',
                    
                    # Бытовая техника
                    'холодильник', 'стиральная машина', 'микроволновка', 'телевизор', 'пылесос', 'утюг', 'чайник', 'мультиварка',
                    
                    # Ремонт и строительство
                    'ремонт', 'краска', 'обои', 'плитка', 'линолеум', 'ламинат', 'гвозди', 'шурупы', 'инструменты', 'строительство', 'декор', 'посуда', 'кастрюли', 'сковородки'
                ],
                
                'спорт': [
                    'спортзал', 'фитнес', 'тренажерный зал', 'бассейн', 'йога', 'танцы', 'спортивная одежда', 'кроссовки для спорта', 'абонемент'
                ],
                
                'хобби': [
                    'рукоделие', 'вязание', 'шитье', 'вышивание', 'рисование', 'краски', 'кисти', 'холст', 'пазлы', 'конструктор'
                ],
                
                'подарки': [
                    'подарок', 'сувенир', 'цветы', 'букет', 'торт на день рождения', 'открытка', 'игрушка'
                ],
                
                'животные': [
                    'корм для животных', 'ветеринар', 'зоомагазин', 'игрушки для животных', 'ошейник', 'поводок'
                ]
            },
            
            'en': {
                'food': [
                    'groceries', 'milk', 'bread', 'meat', 'vegetables', 'fruits', 'food', 'restaurant', 'cafe', 'apples', 'bananas', 'chicken', 'beef', 'cheese', 'yogurt', 'butter', 'eggs', 'rice', 'pasta', 'fish', 'supermarket', 'grocery store'
                ],
                'transport': ['gas', 'fuel', 'bus', 'metro', 'taxi', 'car', 'auto', 'parking', 'garage'],
                'utilities': ['electricity', 'gas', 'water', 'internet', 'phone', 'heating'],
                'clothing': ['clothes', 'shoes', 'jacket', 'jeans', 'dress', 'shirt', 'boots', 'sneakers'],
                'entertainment': ['cinema', 'movies', 'games', 'books', 'music', 'concert', 'club'],
                'health': ['medicine', 'doctor', 'hospital', 'pharmacy', 'dentist'],
                'work': ['salary', 'bonus', 'work', 'job', 'wage'],
                'home': ['furniture', 'repair', 'tools', 'construction', 'decoration']
            },
            
            'uz': {
                'oziq-ovqat': [
                    'mahsulotlar', 'sut', 'non', 'go\'sht', 'sabzavot', 'meva', 'ovqat', 'restoran', 'olma', 'banan', 'tovuq', 'mol go\'shti', 'pishloq', 'yogurt', 'sariyog', 'tuxum', 'guruch', 'makaron', 'baliq'
                ],
                'transport': ['benzin', 'yoqilg\'i', 'avtobus', 'metro', 'taksi', 'mashina'],
                'kommunal': ['elektr', 'gaz', 'suv', 'internet', 'telefon'],
                'kiyim': ['kiyim', 'oyoq kiyim', 'kurtka', 'jinsi', 'ko\'ylak'],
                'o\'yin-kulgi': ['kino', 'teatr', 'o\'yinlar', 'kitoblar', 'musiqa'],
                'salomatlik': ['dori', 'shifokor', 'kasalxona', 'dorixona'],
                'ish': ['maosh', 'mukofot', 'ish', 'ishlab topish']
            }
        }
    
    async def parse_transaction_text(self, text: str, language: str = 'ru', user_currency: str = 'UZS') -> Optional[Dict[str, Any]]:
        """
        Основной метод парсинга транзакции из текста
        
        Args:
            text: Текст для парсинга
            language: Язык текста
            user_currency: Валюта пользователя для конвертации
            
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
            amount, detected_currency = self._extract_amount_and_currency(text)
            if not amount:
                return None
            
            # 3. Конвертируем в валюту пользователя если нужно
            final_amount = amount
            final_currency = detected_currency
            
            if detected_currency != user_currency:
                final_amount = await self._convert_currency(amount, detected_currency, user_currency)
                final_currency = user_currency
                
                logger.info(f"Converted transaction: {amount} {detected_currency} → {final_amount:.2f} {final_currency}")
            
            # 4. Извлекаем описание и автоматически определяем категорию
            description, category = self._extract_description_and_category(text, language)
            
            return {
                'type': transaction_type,
                'amount': final_amount,
                'currency': final_currency,
                'original_amount': amount,
                'original_currency': detected_currency,
                'description': description,
                'category': category,
                'source': 'text'
            }
            
        except Exception as e:
            logger.error(f"Error parsing transaction text: {e}")
            return None

    def parse_management_command(self, text: str, language: str = 'ru') -> Optional[Dict[str, Any]]:
        """
        Парсит команды управления (смена языка, валюты, создание категорий, УДАЛЕНИЕ)
        
        Returns:
            Dict с типом команды и параметрами или None
        """
        try:
            text = text.lower().strip()
            
            # Проверяем команды для всех языков (мультиязычность)
            for lang in ['ru', 'en', 'uz']:
                commands = self.management_keywords.get(lang, {})
                
                # Проверяем смену языка
                for keyword in commands.get('language', []):
                    if keyword in text:
                        target_lang = self._extract_target_language(text)
                        return {
                            'type': 'change_language',
                            'target_language': target_lang,
                            'source': 'management'
                        }
                
                # Проверяем смену валюты
                for keyword in commands.get('currency', []):
                    if keyword in text:
                        target_currency = self._extract_target_currency(text)
                        return {
                            'type': 'change_currency',
                            'target_currency': target_currency,
                            'source': 'management'
                        }
                
                # Проверяем УДАЛЕНИЕ КАТЕГОРИИ
                for keyword in commands.get('delete_category', []):
                    if keyword in text:
                        category_name = self._extract_delete_target(text, keyword)
                        if category_name:
                            return {
                                'type': 'delete_category',
                                'category_name': category_name,
                                'source': 'management'
                            }
                
                # Проверяем УДАЛЕНИЕ ТРАНЗАКЦИИ
                for keyword in commands.get('delete_transaction', []):
                    if keyword in text:
                        # Для транзакций можем искать номер или описание
                        target = self._extract_delete_target(text, keyword)
                        if target:
                            return {
                                'type': 'delete_transaction',
                                'target': target,
                                'source': 'management'
                            }
                
                # Проверяем создание категории
                for keyword in commands.get('create_category', []):
                    if keyword in text:
                        category_name = self._extract_category_name(text, keyword)
                        if category_name:
                            return {
                                'type': 'create_category',
                                'category_name': category_name,
                                'source': 'management'
                            }
            
            return None
            
        except Exception as e:
            logger.error(f"Error parsing management command: {e}")
            return None

    def _extract_target_language(self, text: str) -> str:
        """Извлекает целевой язык из команды"""
        if any(word in text for word in ['русский', 'russian', 'ru']):
            return 'ru'
        elif any(word in text for word in ['английский', 'english', 'en']):
            return 'en'
        elif any(word in text for word in ['узбекский', 'uzbek', 'uz', 'o\'zbek']):
            return 'uz'
        return 'ru'  # по умолчанию
    
    def _extract_target_currency(self, text: str) -> str:
        """Извлекает целевую валюту из команды"""
        if any(word in text for word in ['доллар', 'dollar', 'usd', '$']):
            return 'USD'
        elif any(word in text for word in ['евро', 'euro', 'eur', '€']):
            return 'EUR'
        elif any(word in text for word in ['рубль', 'ruble', 'rub', '₽']):
            return 'RUB'
        elif any(word in text for word in ['сум', 'som', 'uzs']):
            return 'UZS'
        return 'UZS'  # по умолчанию
    
    def _extract_category_name(self, text: str, keyword: str) -> Optional[str]:
        """Извлекает название категории из команды"""
        # Убираем ключевую фразу и извлекаем название
        parts = text.split(keyword)
        if len(parts) > 1:
            category_name = parts[1].strip()
            # Убираем лишние слова
            category_name = re.sub(r'\b(для|with|uchun)\b', '', category_name).strip()
            return category_name if category_name else None
        return None
    
    def _extract_delete_target(self, text: str, keyword: str) -> Optional[str]:
        """Извлекает название объекта для удаления из команды"""
        # Убираем ключевую фразу и извлекаем название
        parts = text.split(keyword)
        if len(parts) > 1:
            target_name = parts[1].strip()
            # Убираем лишние слова и предлоги
            target_name = re.sub(r'\b(для|with|uchun|под|номер|number|raqam)\b', '', target_name).strip()
            
            # Если это может быть номер транзакции
            if target_name.isdigit():
                return target_name
            
            # Если это название категории/описание
            if len(target_name) > 0:
                return target_name
                
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
        
        # Нормализуем текст - убираем лишние пробелы
        text = re.sub(r'\s+', ' ', text.strip())
        
        # Сначала пробуем найти числа словами с валютой
        words_amount, words_currency = self._extract_amount_from_words(text)
        if words_amount:
            logger.info(f"Found amount from words: {words_amount} {words_currency}")
            return words_amount, words_currency
        
        # Проверяем каждую валюту с улучшенными паттернами
        for currency, patterns in self.currency_patterns.items():
            for pattern in patterns:
                matches = re.finditer(pattern, text, re.IGNORECASE)
                for match in matches:
                    amount_str = match.group(1)
                    # Убираем все пробелы и заменяем запятые на точки для десятичных
                    amount_str = re.sub(r'\s', '', amount_str)
                    
                    # Обрабатываем запятые: если это тысячи (1,500) или десятичные (1,50)
                    if ',' in amount_str:
                        parts = amount_str.split(',')
                        if len(parts) == 2:
                            # Если после запятой 3 цифры - это тысячи
                            if len(parts[1]) == 3 and parts[1].isdigit():
                                amount_str = parts[0] + parts[1]  # 1,500 → 1500
                            # Если после запятой 1-2 цифры - это десятичные
                            elif len(parts[1]) <= 2 and parts[1].isdigit():
                                amount_str = parts[0] + '.' + parts[1]  # 1,50 → 1.50
                    
                    try:
                        amount = Decimal(amount_str)
                        if amount > 0:  # Проверяем что сумма положительная
                            logger.info(f"Found {amount} {currency} using pattern: {pattern}")
                            return amount, currency
                    except (InvalidOperation, ValueError) as e:
                        logger.warning(f"Failed to parse amount '{amount_str}': {e}")
                        continue
        
        # Улучшенный поиск просто чисел
        number_patterns = [
            r'(\d+(?:\.\d{1,2})?)',      # 10000.50, 15.99
            r'(\d+(?:\s\d{3})*)',        # 10 000, 1 000 000
            r'(\d+(?:,\d{3})*)',         # 10,000, 1,000,000
            r'(\d{1,3}(?:[\s,]\d{3})*)', # 1,000 или 1 000
            r'(\d+)',                    # просто число
        ]
        
        for pattern in number_patterns:
            matches = re.finditer(pattern, text)
            for match in matches:
                amount_str = match.group(1)
                # Убираем пробелы и обрабатываем запятые правильно
                amount_str = re.sub(r'\s', '', amount_str)
                
                # Обрабатываем запятые: если это тысячи (1,500) или десятичные (1,50)
                if ',' in amount_str:
                    parts = amount_str.split(',')
                    if len(parts) == 2:
                        # Если после запятой 3 цифры - это тысячи
                        if len(parts[1]) == 3 and parts[1].isdigit():
                            amount_str = parts[0] + parts[1]  # 1,500 → 1500
                        # Если после запятой 1-2 цифры - это десятичные
                        elif len(parts[1]) <= 2 and parts[1].isdigit():
                            amount_str = parts[0] + '.' + parts[1]  # 1,50 → 1.50
                
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

    def _extract_amount_from_words(self, text: str) -> tuple[Optional[Decimal], str]:
        """Извлекает сумму из слов (тысяча долларов, одна тысяча сум и т.д.)"""
        
        text_lower = text.lower()
        
        # Определяем валюту из текста
        detected_currency = 'UZS'  # по умолчанию
        
        currency_keywords = {
            'USD': ['доллар', 'долларов', 'dollaro', 'usd', '$'],
            'EUR': ['евро', 'eur', '€'],
            'RUB': ['рубл', 'руб', 'rub', '₽'],
            'UZS': ['сум', 'сом', 'uzs', 'so\'m']
        }
        
        for currency, keywords in currency_keywords.items():
            if any(keyword in text_lower for keyword in keywords):
                detected_currency = currency
                break
        
        # Паттерны для чисел словами с валютой
        number_word_patterns = [
            # "одна тысяча долларов", "тысяча долларов"
            r'(?:одн[ауо]?\s+)?тысяч[ауи]?\s+(?:доллар|сум|рубл|евро)',
            # "две тысячи долларов", "пять тысяч сум"
            r'(?:дв[ае]|три|четыре|пять|шесть|семь|восемь|девять|десять)\s+тысяч[иь]?\s+(?:доллар|сум|рубл|евро)',
            # просто "тысяча долларов"
            r'тысяч[ауи]?\s+(?:доллар|сум|рубл|евро)',
            # "сто долларов", "двести сум" и т.д.
            r'(?:сто|двести|триста|четыреста|пятьсот|шестьсот|семьсот|восемьсот|девятьсот)\s+(?:доллар|сум|рубл|евро)',
            # "пятьдесят долларов" и т.д.
            r'(?:десять|двадцать|тридцать|сорок|пятьдесят|шестьдесят|семьдесят|восемьдесят|девяносто)\s+(?:доллар|сум|рубл|евро)'
        ]
        
        for pattern in number_word_patterns:
            match = re.search(pattern, text_lower)
            if match:
                matched_text = match.group(0)
                amount = self._parse_number_words(matched_text)
                if amount:
                    return Decimal(amount), detected_currency
        
        return None, detected_currency

    def _parse_number_words(self, text: str) -> Optional[int]:
        """Парсит числа из слов в числовое значение"""
        
        words = text.lower().split()
        number_words_dict = self.number_words.get('ru', {})
        
        total = 0
        current = 0
        
        for word in words:
            # Пропускаем валютные слова
            if word in ['доллар', 'долларов', 'сум', 'сом', 'рубл', 'рублей', 'евро']:
                continue
                
            if word in number_words_dict:
                value = number_words_dict[word]
                
                if value == 1000:
                    if current == 0:
                        current = 1
                    total += current * 1000
                    current = 0
                elif value == 1000000:
                    if current == 0:
                        current = 1
                    total += current * 1000000
                    current = 0
                elif value == 1000000000:
                    if current == 0:
                        current = 1
                    total += current * 1000000000
                    current = 0
                else:
                    current += value
        
        total += current
        
        return total if total > 0 else None

    async def _convert_currency(self, amount: Decimal, from_currency: str, to_currency: str) -> Decimal:
        """Конвертирует валюту (базовая реализация с фиксированными курсами)"""
        
        if from_currency == to_currency:
            return amount
        
        # Базовые курсы (в реальном проекте должны получаться из API)
        exchange_rates = {
            'USD_UZS': 12300,
            'EUR_UZS': 13400,
            'RUB_UZS': 135,
            'UZS_USD': 1 / 12300,
            'UZS_EUR': 1 / 13400,
            'UZS_RUB': 1 / 135,
            'USD_EUR': 0.92,
            'EUR_USD': 1.09,
            'USD_RUB': 91,
            'RUB_USD': 1 / 91,
            'EUR_RUB': 99,
            'RUB_EUR': 1 / 99
        }
        
        rate_key = f"{from_currency}_{to_currency}"
        rate = exchange_rates.get(rate_key, 1)
        
        converted_amount = amount * Decimal(str(rate))
        
        logger.info(f"Converted {amount} {from_currency} to {converted_amount:.2f} {to_currency} (rate: {rate})")
        
        return converted_amount
    
    def _extract_description_and_category(self, text: str, language: str) -> tuple[str, str]:
        """Извлекает описание и автоматически определяет категорию"""
        
        # Создаём копию текста для обработки
        clean_text = text
        
        # Убираем ключевые слова транзакций
        all_keywords = (
            self.expense_keywords.get(language, []) + 
            self.income_keywords.get(language, [])
        )
        
        for keyword in all_keywords:
            # Используем более точный паттерн с границами слов
            pattern = rf'\b{re.escape(keyword)}\b'
            clean_text = re.sub(pattern, '', clean_text, flags=re.IGNORECASE)
        
        # Убираем валютные паттерны (сначала сохраняем найденные суммы)
        for currency, patterns in self.currency_patterns.items():
            for pattern in patterns:
                clean_text = re.sub(pattern, '', clean_text, flags=re.IGNORECASE)
        
        # Убираем оставшиеся числа
        clean_text = re.sub(r'\b\d+(?:[\s,]*\d+)*(?:\.\d+)?\b', '', clean_text)
        
        # Убираем предлоги и служебные слова
        prepositions = {
            'ru': ['на', 'за', 'в', 'с', 'для', 'по', 'из', 'к', 'у', 'о', 'от', 'до', 'при', 'под'],
            'en': ['on', 'for', 'in', 'with', 'to', 'from', 'at', 'by', 'of', 'the', 'a', 'an'],
            'uz': ['uchun', 'bilan', 'dan', 'ga', 'da', 'ning', 'ni', 'va', 'yoki']
        }
        
        for prep in prepositions.get(language, []):
            pattern = rf'\b{re.escape(prep)}\b'
            clean_text = re.sub(pattern, '', clean_text, flags=re.IGNORECASE)
        
        # Очищаем и нормализуем
        description = ' '.join(clean_text.split()).strip()
        
        # Если описание слишком короткое или пустое
        if not description or len(description) < 2:
            # Пытаемся извлечь из исходного текста без агрессивной очистки
            simple_clean = text
            for keyword in all_keywords:
                simple_clean = simple_clean.replace(keyword, '', 1)
            
            # Убираем только числа с валютами
            for currency, patterns in self.currency_patterns.items():
                for pattern in patterns:
                    simple_clean = re.sub(pattern, '', simple_clean, flags=re.IGNORECASE)
            
            description = ' '.join(simple_clean.split()).strip()
            
            # Если всё ещё пустое - ставим значение по умолчанию
            if not description or len(description) < 2:
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