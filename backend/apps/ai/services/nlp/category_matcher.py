"""
NLP сервис для автоматического сопоставления товаров с категориями
Использует текстовый анализ и словари ключевых слов
"""

import re
import logging
from typing import Dict, List, Tuple, Optional
from difflib import SequenceMatcher

from django.db.models import Q
from apps.categories.models import Category


logger = logging.getLogger(__name__)


class CategoryMatcher:
    """Сервис для определения категорий товаров/услуг"""
    
    # Словари категорий по ключевым словам
    CATEGORY_KEYWORDS = {
        'Продукты': {
            'ru': [
                'хлеб', 'молоко', 'мясо', 'рыба', 'овощи', 'фрукты', 'сыр',
                'колбаса', 'курица', 'говядина', 'свинина', 'творог', 'йогурт',
                'масло', 'сахар', 'соль', 'мука', 'рис', 'гречка', 'макароны',
                'картофель', 'лук', 'морковь', 'капуста', 'помидоры', 'огурцы',
                'яблоки', 'бананы', 'апельсины', 'лимоны', 'виноград', 'ягоды',
                'крупа', 'консервы', 'паста', 'спагетти', 'пельмени'
            ],
            'uz': [
                'non', 'sut', 'go\'sht', 'baliq', 'sabzavot', 'meva', 'pishloq',
                'kolbasa', 'tovuq', 'mol go\'shti', 'cho\'chqa go\'shti', 'tvorog',
                'yog\'urt', 'yog\'', 'shakar', 'tuz', 'un', 'guruch', 'grechka',
                'makaron', 'kartoshka', 'piyoz', 'sabzi', 'karam', 'pomidor',
                'bodring', 'olma', 'banan', 'apelsin', 'limon', 'uzum'
            ],
            'en': [
                'bread', 'milk', 'meat', 'fish', 'vegetables', 'fruits', 'cheese',
                'sausage', 'chicken', 'beef', 'pork', 'cottage', 'yogurt',
                'butter', 'sugar', 'salt', 'flour', 'rice', 'buckwheat', 'pasta',
                'potato', 'onion', 'carrot', 'cabbage', 'tomato', 'cucumber',
                'apple', 'banana', 'orange', 'lemon', 'grape', 'berry'
            ]
        },
        'Напитки': {
            'ru': [
                'вода', 'сок', 'чай', 'кофе', 'пиво', 'вино', 'водка', 'коньяк',
                'лимонад', 'газировка', 'кола', 'пепси', 'спрайт', 'энергетик',
                'квас', 'компот', 'морс', 'коктейль', 'виски', 'ром', 'текила'
            ],
            'uz': [
                'suv', 'sharbat', 'choy', 'qahva', 'pivo', 'vino', 'vodka',
                'konyak', 'limonad', 'gazlangan', 'kola', 'pepsi', 'energetik',
                'kompot', 'mors', 'kokteyl'
            ],
            'en': [
                'water', 'juice', 'tea', 'coffee', 'beer', 'wine', 'vodka',
                'cognac', 'lemonade', 'soda', 'cola', 'pepsi', 'sprite',
                'energy', 'kvass', 'cocktail', 'whiskey', 'rum', 'tequila'
            ]
        },
        'Транспорт': {
            'ru': [
                'бензин', 'дизель', 'топливо', 'автобус', 'метро', 'такси',
                'трамвай', 'троллейбус', 'маршрутка', 'парковка', 'штраф',
                'техосмотр', 'страховка', 'ремонт', 'шины', 'масло', 'запчасти'
            ],
            'uz': [
                'benzin', 'dizel', 'yoqilg\'i', 'avtobus', 'metro', 'taksi',
                'tramvay', 'trolleybus', 'marshrut', 'parking', 'jarima',
                'ta\'mir', 'shinalar', 'moy', 'ehtiyot qismlar'
            ],
            'en': [
                'gasoline', 'diesel', 'fuel', 'bus', 'metro', 'taxi',
                'tram', 'parking', 'fine', 'repair', 'tires', 'oil',
                'parts', 'insurance'
            ]
        },
        'Развлечения': {
            'ru': [
                'кино', 'театр', 'концерт', 'ресторан', 'кафе', 'бар', 'клуб',
                'боулинг', 'бильярд', 'караоке', 'игры', 'парк', 'зоопарк',
                'музей', 'выставка', 'цирк', 'аквапарк', 'казино', 'кальян'
            ],
            'uz': [
                'kino', 'teatr', 'konsert', 'restoran', 'kafe', 'bar', 'klub',
                'bouling', 'bilyard', 'karaoke', 'o\'yinlar', 'park', 'hayvonot bog\'i',
                'muzey', 'ko\'rgazma', 'sirk', 'akvapark', 'kazino', 'kalyan'
            ],
            'en': [
                'cinema', 'theater', 'concert', 'restaurant', 'cafe', 'bar',
                'club', 'bowling', 'billiard', 'karaoke', 'games', 'park',
                'zoo', 'museum', 'exhibition', 'circus', 'aquapark', 'casino'
            ]
        },
        'Одежда': {
            'ru': [
                'рубашка', 'брюки', 'джинсы', 'платье', 'юбка', 'куртка',
                'пальто', 'обувь', 'ботинки', 'кроссовки', 'туфли', 'сапоги',
                'носки', 'белье', 'футболка', 'свитер', 'шорты', 'костюм',
                'шляпа', 'кепка', 'перчатки', 'шарф', 'ремень', 'сумка'
            ],
            'uz': [
                'ko\'ylak', 'shim', 'jinsi', 'ko\'ylak', 'yubka', 'kurtka',
                'palto', 'oyoq kiyim', 'botinka', 'krossovka', 'tufli',
                'paypoq', 'ich kiyim', 'futbolka', 'sviter', 'shorts',
                'kostyum', 'shlyapa', 'kepka', 'qo\'lqop', 'sharf', 'kamar'
            ],
            'en': [
                'shirt', 'pants', 'jeans', 'dress', 'skirt', 'jacket',
                'coat', 'shoes', 'boots', 'sneakers', 'socks', 'underwear',
                't-shirt', 'sweater', 'shorts', 'suit', 'hat', 'cap',
                'gloves', 'scarf', 'belt', 'bag'
            ]
        },
        'Здоровье': {
            'ru': [
                'лекарства', 'таблетки', 'сироп', 'мазь', 'врач', 'стоматолог',
                'анализы', 'операция', 'больница', 'поликлиника', 'аптека',
                'витамины', 'лечение', 'массаж', 'физиотерапия', 'рентген'
            ],
            'uz': [
                'dori', 'tabletkalar', 'sirop', 'malham', 'shifokor', 'stomatolog',
                'tahlillar', 'operatsiya', 'kasalxona', 'poliklinika', 'dorixona',
                'vitaminlar', 'davolash', 'massaj', 'fizioterapiya'
            ],
            'en': [
                'medicine', 'pills', 'syrup', 'ointment', 'doctor', 'dentist',
                'analysis', 'operation', 'hospital', 'pharmacy', 'vitamins',
                'treatment', 'massage', 'physiotherapy', 'x-ray'
            ]
        },
        'Коммунальные услуги': {
            'ru': [
                'электричество', 'газ', 'вода', 'отопление', 'интернет',
                'телефон', 'мобильная связь', 'кабельное', 'телевидение',
                'домофон', 'охрана', 'уборка', 'лифт', 'управляющая'
            ],
            'uz': [
                'elektr', 'gaz', 'suv', 'isitish', 'internet', 'telefon',
                'mobil aloqa', 'kabel', 'televideniye', 'domofon', 'qo\'riqchi',
                'tozalash', 'lift', 'boshqaruvchi'
            ],
            'en': [
                'electricity', 'gas', 'water', 'heating', 'internet',
                'phone', 'mobile', 'cable', 'television', 'cleaning',
                'elevator', 'management'
            ]
        },
        'Образование': {
            'ru': [
                'книги', 'учебники', 'тетради', 'ручки', 'карандаши',
                'курсы', 'университет', 'школа', 'репетитор', 'экзамен',
                'семинар', 'тренинг', 'конференция', 'лекция'
            ],
            'uz': [
                'kitoblar', 'darsliklar', 'daftarlar', 'ruchkalar', 'qalamlar',
                'kurslar', 'universitet', 'maktab', 'repetitor', 'imtihon',
                'seminar', 'trening', 'konferensiya', 'ma\'ruza'
            ],
            'en': [
                'books', 'textbooks', 'notebooks', 'pens', 'pencils',
                'courses', 'university', 'school', 'tutor', 'exam',
                'seminar', 'training', 'conference', 'lecture'
            ]
        }
    }
    
    # Названия магазинов и их категории
    SHOP_CATEGORIES = {
        'Продукты': [
            'кorzinka', 'makro', 'carrefour', 'havas', 'супермаркет',
            'продуктовый', 'гастроном', 'универсам', 'магнум'
        ],
        'Одежда': [
            'zara', 'h&m', 'uniqlo', 'adidas', 'nike', 'lcwaikiki',
            'defacto', 'colin\'s', 'mango', 'massimo dutti'
        ],
        'Развлечения': [
            'cinemapark', 'kinomax', 'aura', 'next', 'cosmo', 'пицца',
            'burger', 'kfc', 'mcdonalds', 'subway', 'starbucks'
        ],
        'Здоровье': [
            'аптека', 'дориха', 'pharmacy', 'farmatsiya', 'zdorovye'
        ],
        'Транспорт': [
            'газпром', 'лукойл', 'узгазойл', 'заправка', 'азс'
        ]
    }
    
    def __init__(self):
        """Инициализация матчера"""
        self.default_category_cache = {}
    
    def match_category(
        self, 
        item_name: str, 
        user, 
        shop_name: str = None
    ) -> Tuple[Optional['Category'], float]:
        """
        Определение категории для товара/услуги
        
        Args:
            item_name: Название товара/услуги
            user: Пользователь
            shop_name: Название магазина (опционально)
            
        Returns:
            Tuple[Category, float]: Категория и уровень уверенности (0-1)
        """
        if not item_name.strip():
            return None, 0.0
        
        # Нормализуем текст
        normalized_name = self._normalize_text(item_name)
        
        # Получаем пользовательские категории
        user_categories = Category.objects.filter(user=user).select_related()
        
        # 1. Поиск точного совпадения в названиях категорий пользователя
        exact_match = self._find_exact_category_match(normalized_name, user_categories)
        if exact_match:
            return exact_match, 1.0
        
        # 2. Определение по магазину
        if shop_name:
            shop_category = self._match_by_shop(shop_name, user_categories)
            if shop_category:
                return shop_category, 0.8
        
        # 3. Поиск по ключевым словам
        keyword_match, confidence = self._match_by_keywords(normalized_name, user_categories)
        if keyword_match and confidence > 0.6:
            return keyword_match, confidence
        
        # 4. Поиск по частичному совпадению названий
        partial_match, confidence = self._find_partial_category_match(
            normalized_name, user_categories
        )
        if partial_match and confidence > 0.5:
            return partial_match, confidence
        
        # 5. Создание новой категории или возврат дефолтной
        default_category = self._get_or_create_default_category(
            normalized_name, user
        )
        
        return default_category, 0.3
    
    def _normalize_text(self, text: str) -> str:
        """Нормализация текста для анализа"""
        # Приводим к нижнему регистру
        text = text.lower().strip()
        
        # Убираем лишние пробелы
        text = ' '.join(text.split())
        
        # Убираем специальные символы, оставляем только буквы, цифры и пробелы
        text = re.sub(r'[^\w\s]', ' ', text)
        
        # Убираем повторяющиеся пробелы
        text = ' '.join(text.split())
        
        return text
    
    def _find_exact_category_match(
        self, 
        item_name: str, 
        categories
    ) -> Optional['Category']:
        """Поиск точного совпадения с названием категории"""
        item_words = set(item_name.split())
        
        for category in categories:
            category_words = set(self._normalize_text(category.name).split())
            
            # Проверяем пересечение слов
            if item_words & category_words:
                return category
        
        return None
    
    def _match_by_shop(
        self, 
        shop_name: str, 
        user_categories
    ) -> Optional['Category']:
        """Определение категории по названию магазина"""
        shop_normalized = self._normalize_text(shop_name)
        
        for category_name, shop_keywords in self.SHOP_CATEGORIES.items():
            for keyword in shop_keywords:
                if keyword.lower() in shop_normalized:
                    # Ищем соответствующую категорию у пользователя
                    category = self._find_user_category_by_name(
                        category_name, user_categories
                    )
                    if category:
                        return category
        
        return None
    
    def _match_by_keywords(
        self, 
        item_name: str, 
        user_categories
    ) -> Tuple[Optional['Category'], float]:
        """Поиск категории по ключевым словам"""
        item_words = item_name.split()
        best_match = None
        best_confidence = 0.0
        
        for category_name, languages in self.CATEGORY_KEYWORDS.items():
            # Объединяем ключевые слова всех языков
            all_keywords = []
            for lang_keywords in languages.values():
                all_keywords.extend(lang_keywords)
            
            # Подсчитываем совпадения
            matches = 0
            for word in item_words:
                for keyword in all_keywords:
                    # Проверяем точное совпадение или вхождение
                    if word == keyword or keyword in word or word in keyword:
                        matches += 1
                        break
            
            if matches > 0:
                # Рассчитываем уверенность
                confidence = matches / len(item_words)
                
                if confidence > best_confidence:
                    # Ищем соответствующую категорию пользователя
                    user_category = self._find_user_category_by_name(
                        category_name, user_categories
                    )
                    if user_category:
                        best_match = user_category
                        best_confidence = confidence
        
        return best_match, best_confidence
    
    def _find_partial_category_match(
        self, 
        item_name: str, 
        categories
    ) -> Tuple[Optional['Category'], float]:
        """Поиск частичного совпадения с категориями"""
        best_match = None
        best_ratio = 0.0
        
        for category in categories:
            category_name = self._normalize_text(category.name)
            
            # Используем SequenceMatcher для определения схожести
            ratio = SequenceMatcher(None, item_name, category_name).ratio()
            
            if ratio > best_ratio:
                best_match = category
                best_ratio = ratio
        
        return best_match, best_ratio
    
    def _find_user_category_by_name(
        self, 
        category_name: str, 
        user_categories
    ) -> Optional['Category']:
        """Поиск категории пользователя по названию"""
        normalized_target = self._normalize_text(category_name)
        
        for category in user_categories:
            normalized_category = self._normalize_text(category.name)
            
            # Проверяем различные варианты совпадений
            if (normalized_target == normalized_category or
                normalized_target in normalized_category or
                normalized_category in normalized_target):
                return category
        
        return None
    
    def _get_or_create_default_category(
        self, 
        item_name: str, 
        user
    ) -> Optional['Category']:
        """Получение или создание категории по умолчанию"""
        # Пытаемся определить лучшую категорию по ключевым словам
        for category_name, languages in self.CATEGORY_KEYWORDS.items():
            all_keywords = []
            for lang_keywords in languages.values():
                all_keywords.extend(lang_keywords)
            
            for keyword in all_keywords:
                if keyword in item_name:
                    # Пытаемся найти или создать категорию
                    category = self._get_or_create_category(category_name, user)
                    if category:
                        return category
        
        # Создаем категорию "Прочее" если ничего не подошло
        return self._get_or_create_category('Прочее', user)
    
    def _get_or_create_category(
        self, 
        category_name: str, 
        user
    ) -> Optional['Category']:
        """Получение или создание категории"""
        try:
            # Проверяем кэш
            cache_key = f"{user.id}_{category_name}"
            if cache_key in self.default_category_cache:
                return self.default_category_cache[cache_key]
            
            # Ищем существующую категорию
            category = Category.objects.filter(
                user=user,
                name__icontains=category_name
            ).first()
            
            if not category:
                # Создаем новую категорию
                category = Category.objects.create(
                    user=user,
                    name=category_name,
                    description=f'Автоматически созданная категория для "{category_name}"'
                )
                logger.info(f"Created new category '{category_name}' for user {user.id}")
            
            # Кэшируем результат
            self.default_category_cache[cache_key] = category
            return category
            
        except Exception as e:
            logger.error(f"Error creating category '{category_name}' for user {user.id}: {e}")
            return None
    
    def analyze_receipt_categories(
        self, 
        items: List[Dict], 
        user, 
        shop_name: str = None
    ) -> Dict:
        """
        Анализ категорий для всех позиций чека
        
        Args:
            items: Список позиций чека
            user: Пользователь
            shop_name: Название магазина
            
        Returns:
            Dict: Статистика по категориям
        """
        category_stats = {}
        total_amount = 0
        unmatched_items = []
        
        for item in items:
            category, confidence = self.match_category(
                item.get('name', ''), user, shop_name
            )
            
            amount = float(item.get('total_price', 0))
            total_amount += amount
            
            if category:
                category_name = category.name
                if category_name not in category_stats:
                    category_stats[category_name] = {
                        'items': 0,
                        'amount': 0,
                        'confidence_avg': 0,
                        'confidence_scores': []
                    }
                
                category_stats[category_name]['items'] += 1
                category_stats[category_name]['amount'] += amount
                category_stats[category_name]['confidence_scores'].append(confidence)
            else:
                unmatched_items.append(item)
        
        # Рассчитываем средние значения
        for category_name, stats in category_stats.items():
            if stats['confidence_scores']:
                stats['confidence_avg'] = sum(stats['confidence_scores']) / len(stats['confidence_scores'])
                stats['percentage'] = (stats['amount'] / total_amount * 100) if total_amount > 0 else 0
            del stats['confidence_scores']  # Удаляем временный список
        
        return {
            'categories': category_stats,
            'total_amount': total_amount,
            'matched_items': len(items) - len(unmatched_items),
            'unmatched_items': unmatched_items,
            'matching_rate': (len(items) - len(unmatched_items)) / len(items) if items else 0
        }
    
    def suggest_categories_for_user(self, user, limit: int = 10) -> List[str]:
        """
        Предложение популярных категорий для пользователя
        
        Args:
            user: Пользователь
            limit: Максимальное количество предложений
            
        Returns:
            List[str]: Список предлагаемых категорий
        """
        # Получаем существующие категории пользователя
        existing_categories = set(
            Category.objects.filter(user=user).values_list('name', flat=True)
        )
        
        # Предлагаем популярные категории, которых нет у пользователя
        suggested = []
        for category_name in self.CATEGORY_KEYWORDS.keys():
            if category_name not in existing_categories and len(suggested) < limit:
                suggested.append(category_name)
        
        return suggested
    
    def get_category_keywords(self, category_name: str) -> List[str]:
        """
        Получение ключевых слов для категории
        
        Args:
            category_name: Название категории
            
        Returns:
            List[str]: Список ключевых слов
        """
        if category_name in self.CATEGORY_KEYWORDS:
            all_keywords = []
            for lang_keywords in self.CATEGORY_KEYWORDS[category_name].values():
                all_keywords.extend(lang_keywords)
            return sorted(set(all_keywords))
        
        return [] 