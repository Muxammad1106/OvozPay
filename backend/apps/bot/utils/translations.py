"""
Система переводов для Telegram бота
Поддерживает русский, английский и узбекский языки
"""

from typing import Dict, Any


class BotTranslations:
    """Класс для управления переводами бота"""
    
    # Основные переводы для всех языков
    TRANSLATIONS = {
        'ru': {
            # Команды и кнопки
            'start_welcome': '🎉 Добро пожаловать в OvozPay!\n\nЯ помогу вам управлять финансами с помощью голосовых команд и фотографий чеков.',
            'choose_language': 'Пожалуйста, выберите язык интерфейса:',
            'language_set': '✅ Язык интерфейса установлен: Русский',
            'help_title': '📋 Справка по командам OvozPay',
            'balance_title': '💰 Ваш текущий баланс',
            'settings_title': '⚙️ Настройки',
            'back_button': '◀️ Назад',
            
            # Основные команды
            'help_commands': '''
🎤 Голосовые команды:
• Скажите: "потратил 5000 сум на продукты"
• Скажите: "заработал 100000 сум"

📸 Фотографии чеков:
• Отправьте фото чека для автоматического создания расходов

📊 Команды:
/menu - главное меню
/balance - показать баланс
/settings - настройки
/help - эта справка
            ''',
            
            # Настройки
            'settings_language': '🌐 Язык интерфейса',
            'settings_currency': '💱 Валюта по умолчанию',
            'settings_phone': '📱 Номер телефона',
            'currency_set': '✅ Валюта установлена: {}',
            'phone_request': 'Пожалуйста, отправьте ваш номер телефона:',
            'phone_set': '✅ Номер телефона сохранён',
            
            # Главное меню
            'main_menu': '📋 Главное меню',
            'menu_balance': '💰 Баланс',
            'menu_history': '📊 История',
            'menu_categories': '📂 Категории',
            'menu_goals': '🎯 Цели',
            'menu_debts': '💸 Долги',
            'menu_settings': '⚙️ Настройки',
            'menu_help': '❓ Помощь',
            
            # Голосовые команды
            'voice_processing': '🎤 Обрабатываю голосовое сообщение...',
            'voice_transcribed': '📝 Распознано: {}',
            'voice_error': '❌ Ошибка обработки голосового сообщения',
            'voice_no_transaction': '🤔 Не смог найти данные о транзакции в голосовом сообщении',
            'voice_transaction_created': '✅ {type} создан:\n💰 *{amount}*\n📂 *{category}*\n📝 {description}',
            'transaction_created': '✅ Транзакция создана:\n💰 Сумма: {} {}\n📝 Описание: {}',
            
            # Фото чеки
            'photo_processing': '📸 Обрабатываю фотографию чека...',
            'photo_text_extracted': '📝 Извлечённый текст:\n{}',
            'photo_error': '❌ Ошибка обработки фотографии',
            'receipt_processed': '✅ Чек обработан. Найдено товаров: {}',
            
            # Валюты
            'uzs': 'Узбекский сум',
            'usd': 'Доллар США', 
            'eur': 'Евро',
            'rub': 'Российский рубль',
            
            # Языки
            'russian': '🇷🇺 Русский',
            'english': '🇺🇸 English',
            'uzbek': '🇺🇿 O\'zbekcha',
            
            # Ошибки
            'error_occurred': '❌ Произошла ошибка. Попробуйте позже.',
            'invalid_command': '❓ Команда не распознана. Используйте /help для справки.',
            'processing_failed': '❌ Не удалось обработать запрос',
            'feature_not_implemented': '🚧 Функция пока не реализована. Скоро будет доступна!',
            
            # Статистика
            'statistics': 'Статистика:',
            'income': 'Доходы',
            'expense': 'Расходы', 
            'transactions': 'Транзакций',
            'categories_title': 'Ваши категории:',
            'no_categories': 'У вас пока нет категорий',
            'create_category_hint': 'Для создания новой категории напишите:\n"создай категорию [название]"',
            
            # Общие
            'yes': 'Да',
            'no': 'Нет',
            'cancel': 'Отмена',
            'save': 'Сохранить',
            'loading': 'Загрузка...',
            
            # Удаление категорий и транзакций
            'category_created': 'Категория создана',
            'category_exists': 'Категория уже существует',
            'category_deleted': 'Категория удалена',
            'category_not_found': 'Категория не найдена',
            'transaction_deleted': 'Транзакция удалена',
            'transaction_not_found': 'Транзакция не найдена',
            'currency_changed': 'Валюта изменена на {currency}'
        },
        
        'en': {
            # Commands and buttons
            'start_welcome': '🎉 Welcome to OvozPay!\n\nI will help you manage your finances using voice commands and receipt photos.',
            'choose_language': 'Please choose your interface language:',
            'language_set': '✅ Interface language set: English',
            'help_title': '📋 OvozPay Commands Help',
            'balance_title': '💰 Your current balance',
            'settings_title': '⚙️ Settings',
            'back_button': '◀️ Back',
            
            # Main commands
            'help_commands': '''
🎤 Voice commands:
• Say: "spent 50 dollars on groceries"
• Say: "earned 1000 dollars"

📸 Receipt photos:
• Send a receipt photo for automatic expense creation

📊 Commands:
/menu - main menu
/balance - show balance
/settings - settings
/help - this help
            ''',
            
            # Settings
            'settings_language': '🌐 Interface Language',
            'settings_currency': '💱 Default Currency',
            'settings_phone': '📱 Phone Number',
            'currency_set': '✅ Currency set: {}',
            'phone_request': 'Please send your phone number:',
            'phone_set': '✅ Phone number saved',
            
            # Main menu
            'main_menu': '📋 Main Menu',
            'menu_balance': '💰 Balance',
            'menu_history': '📊 History',
            'menu_categories': '📂 Categories',
            'menu_goals': '🎯 Goals',
            'menu_debts': '💸 Debts',
            'menu_settings': '⚙️ Settings',
            'menu_help': '❓ Help',
            
            # Voice commands
            'voice_processing': '🎤 Processing voice message...',
            'voice_transcribed': '📝 Recognized: {}',
            'voice_error': '❌ Voice message processing error',
            'voice_no_transaction': '🤔 Could not find transaction data in voice message',
            'voice_transaction_created': '✅ {type} created:\n💰 *{amount}*\n📂 *{category}*\n📝 {description}',
            'transaction_created': '✅ Transaction created:\n💰 Amount: {} {}\n📝 Description: {}',
            
            # Photo receipts
            'photo_processing': '📸 Processing receipt photo...',
            'photo_text_extracted': '📝 Extracted text:\n{}',
            'photo_error': '❌ Photo processing error',
            'receipt_processed': '✅ Receipt processed. Items found: {}',
            
            # Currencies
            'uzs': 'Uzbek Som',
            'usd': 'US Dollar',
            'eur': 'Euro',
            'rub': 'Russian Ruble',
            
            # Languages
            'russian': '🇷🇺 Русский',
            'english': '🇺🇸 English',
            'uzbek': '🇺🇿 O\'zbekcha',
            
            # Errors
            'error_occurred': '❌ An error occurred. Please try again later.',
            'invalid_command': '❓ Command not recognized. Use /help for help.',
            'processing_failed': '❌ Failed to process request',
            'feature_not_implemented': '🚧 Feature not implemented yet. Will be available soon!',
            
            # Statistics  
            'statistics': 'Statistics:',
            'income': 'Income',
            'expense': 'Expenses',
            'transactions': 'Transactions',
            'categories_title': 'Your categories:',
            'no_categories': 'You have no categories yet',
            'create_category_hint': 'To create a new category write:\n"create category [name]"',
            
            # General
            'yes': 'Yes',
            'no': 'No',
            'cancel': 'Cancel',
            'save': 'Save',
            'loading': 'Loading...',
            
            # Удаление категорий и транзакций
            'category_created': 'Category created',
            'category_exists': 'Category already exists',
            'category_deleted': 'Category deleted',
            'category_not_found': 'Category not found',
            'transaction_deleted': 'Transaction deleted',
            'transaction_not_found': 'Transaction not found',
            'currency_changed': 'Currency changed to {currency}'
        },
        
        'uz': {
            # Commands and buttons
            'start_welcome': '🎉 OvozPay ga xush kelibsiz!\n\nMen sizga ovozli buyruqlar va chek rasmlari yordamida moliyani boshqarishga yordam beraman.',
            'choose_language': 'Iltimos, interfeys tilini tanlang:',
            'language_set': '✅ Interfeys tili o\'rnatildi: O\'zbekcha',
            'help_title': '📋 OvozPay buyruqlari yordami',
            'balance_title': '💰 Sizning joriy balansingiz',
            'settings_title': '⚙️ Sozlamalar',
            'back_button': '◀️ Orqaga',
            
            # Main commands
            'help_commands': '''
🎤 Ovozli buyruqlar:
• Ayting: "5000 so'm mahsulotlarga sarfladim"
• Ayting: "100000 so'm ishlab topdim"

📸 Chek rasmlari:
• Avtomatik xarajat yaratish uchun chek rasmini yuboring

📊 Buyruqlar:
/menu - asosiy menyu
/balance - balansni ko'rsatish
/settings - sozlamalar
/help - bu yordam
            ''',
            
            # Settings
            'settings_language': '🌐 Interfeys tili',
            'settings_currency': '💱 Asosiy valyuta',
            'settings_phone': '📱 Telefon raqami',
            'currency_set': '✅ Valyuta o\'rnatildi: {}',
            'phone_request': 'Iltimos, telefon raqamingizni yuboring:',
            'phone_set': '✅ Telefon raqami saqlandi',
            
            # Asosiy menyu
            'main_menu': '📋 Asosiy menyu',
            'menu_balance': '💰 Balans',
            'menu_history': '📊 Tarix',
            'menu_categories': '📂 Kategoriyalar',
            'menu_goals': '🎯 Maqsadlar',
            'menu_debts': '💸 Qarzlar',
            'menu_settings': '⚙️ Sozlamalar',
            'menu_help': '❓ Yordam',
            
            # Voice commands
            'voice_processing': '🎤 Ovozli xabarni qayta ishlamoqda...',
            'voice_transcribed': '📝 Tanildi: {}',
            'voice_error': '❌ Ovozli xabarni qayta ishlashda xatolik',
            'voice_no_transaction': '🤔 Ovozli xabarda tranzaksiya ma\'lumotlari topilmadi',
            'voice_transaction_created': '✅ {type} yaratildi:\n💰 *{amount}*\n📂 *{category}*\n📝 {description}',
            'transaction_created': '✅ Tranzaksiya yaratildi:\n💰 Summa: {} {}\n📝 Ta\'rif: {}',
            
            # Photo receipts
            'photo_processing': '📸 Chek rasmini qayta ishlamoqda...',
            'photo_text_extracted': '📝 Olingan matn:\n{}',
            'photo_error': '❌ Rasmni qayta ishlashda xatolik',
            'receipt_processed': '✅ Chek qayta ishlandi. Topilgan mahsulotlar: {}',
            
            # Currencies
            'uzs': 'O\'zbek so\'mi',
            'usd': 'AQSH dollari',
            'eur': 'Evro',
            'rub': 'Rossiya rubli',
            
            # Languages
            'russian': '🇷🇺 Русский',
            'english': '🇺🇸 English',
            'uzbek': '🇺🇿 O\'zbekcha',
            
            # Errors
            'error_occurred': '❌ Xatolik yuz berdi. Keyinroq urinib ko\'ring.',
            'invalid_command': '❓ Buyruq tanilmadi. Yordam uchun /help dan foydalaning.',
            'processing_failed': '❌ So\'rovni qayta ishlab bo\'lmadi',
            'feature_not_implemented': '🚧 Funksiya hali amalga oshirilmagan. Tez orada mavjud bo\'ladi!',
            
            # Statistics
            'statistics': 'Statistika:',
            'income': 'Daromadlar',
            'expense': 'Xarajatlar',
            'transactions': 'Tranzaksiyalar',
            'categories_title': 'Sizning kategoriyalaringiz:',
            'no_categories': 'Sizda hali kategoriyalar yo\'q',
            'create_category_hint': 'Yangi kategoriya yaratish uchun yozing:\n"kategoriya yarat [nomi]"',
            
            # General
            'yes': 'Ha',
            'no': 'Yo\'q',
            'cancel': 'Bekor qilish',
            'save': 'Saqlash',
            'loading': 'Yuklamoqda...',
            
            # Удаление категорий и транзакций
            'category_created': 'Kategoriya yaratildi',
            'category_exists': 'Kategoriya mavjud',
            'category_deleted': 'Kategoriya o\'chirildi',
            'category_not_found': 'Kategoriya topilmadi',
            'transaction_deleted': 'Tranzaksiya o\'chirildi',
            'transaction_not_found': 'Tranzaksiya topilmadi',
            'currency_changed': 'Valyuta o\'zgartirildi: {currency}'
        }
    }
    
    @classmethod
    def get_text(cls, key: str, language: str = 'ru', **kwargs) -> str:
        """
        Получает переведённый текст по ключу
        
        Args:
            key: Ключ перевода
            language: Код языка (ru/en/uz)
            **kwargs: Параметры для форматирования строки
            
        Returns:
            Переведённый текст
        """
        if language not in cls.TRANSLATIONS:
            language = 'ru'  # Fallback to Russian
        
        translations = cls.TRANSLATIONS[language]
        text = translations.get(key, cls.TRANSLATIONS['ru'].get(key, f'[Missing: {key}]'))
        
        if kwargs:
            try:
                return text.format(**kwargs)
            except (KeyError, ValueError):
                return text
        
        return text
    
    @classmethod
    def get_language_keyboard(cls) -> Dict[str, Any]:
        """Возвращает клавиатуру выбора языка"""
        return {
            'keyboard': [
                ['🇷🇺 Русский', '🇺🇸 English'],
                ['🇺🇿 O\'zbekcha']
            ],
            'resize_keyboard': True,
            'one_time_keyboard': True
        }
    
    @classmethod
    def get_currency_keyboard(cls, language: str = 'ru') -> Dict[str, Any]:
        """Возвращает клавиатуру выбора валюты"""
        return {
            'keyboard': [
                [f'💵 {cls.get_text("usd", language)}', f'💶 {cls.get_text("eur", language)}'],
                [f'💴 {cls.get_text("uzs", language)}', f'💷 {cls.get_text("rub", language)}']
            ],
            'resize_keyboard': True,
            'one_time_keyboard': True
        }
    
    @classmethod
    def get_settings_keyboard(cls, language: str = 'ru') -> Dict[str, Any]:
        """Возвращает клавиатуру настроек"""
        return {
            'keyboard': [
                [cls.get_text('settings_language', language)],
                [cls.get_text('settings_currency', language)],
                [cls.get_text('settings_phone', language)],
                [cls.get_text('back_button', language)]
            ],
            'resize_keyboard': True
        }
    
    @classmethod
    def get_main_menu_keyboard(cls, language: str = 'ru') -> Dict[str, Any]:
        """Возвращает главную клавиатуру меню"""
        return {
            'keyboard': [
                [cls.get_text('menu_balance', language), cls.get_text('menu_history', language)],
                [cls.get_text('menu_categories', language), cls.get_text('menu_goals', language)],
                [cls.get_text('menu_debts', language), cls.get_text('menu_settings', language)],
                [cls.get_text('menu_help', language)]
            ],
            'resize_keyboard': True
        }


# Глобальный объект для удобного использования
t = BotTranslations() 