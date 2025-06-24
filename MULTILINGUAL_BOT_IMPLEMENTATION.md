# 🌐 **РЕАЛИЗАЦИЯ МУЛЬТИЯЗЫЧНОСТИ В OVOZPAY BOT**

## 📋 **ОБЗОР**

Система мультиязычности OvozPay Bot обеспечивает полную поддержку трёх языков интерфейса:
- 🇷🇺 **Русский** (ru) - основной язык
- 🇺🇸 **Английский** (en) - международный язык
- 🇺🇿 **Узбекский** (uz) - локальный язык

## 🏗️ **АРХИТЕКТУРА СИСТЕМЫ ПЕРЕВОДОВ**

### Основные компоненты:

```
apps/bot/utils/
├── translations.py         # Система переводов
└── __init__.py

apps/bot/handlers/
├── basic_handlers.py       # Базовые команды с переводами
├── voice_handlers.py       # Голосовые команды с переводами  
├── photo_handlers.py       # Фото команды с переводами
└── __init__.py

apps/bot/services/
├── telegram_api_service.py # API сервис
├── user_service.py         # Управление пользователями
└── __init__.py
```

## 📝 **СИСТЕМА ПЕРЕВОДОВ**

### Класс BotTranslations

```python
from apps.bot.utils.translations import t

# Получение перевода
text = t.get_text('start_welcome', language='ru')

# Перевод с параметрами
text = t.get_text('currency_set', language='en', currency='USD')

# Клавиатуры
keyboard = t.get_language_keyboard()
keyboard = t.get_currency_keyboard(language='uz')
```

### Структура переводов:

```python
TRANSLATIONS = {
    'ru': {
        'start_welcome': '🎉 Добро пожаловать в OvozPay!...',
        'help_title': '📋 Справка по командам OvozPay',
        # ... остальные переводы
    },
    'en': {
        'start_welcome': '🎉 Welcome to OvozPay!...',
        'help_title': '📋 OvozPay Commands Help',
        # ... остальные переводы
    },
    'uz': {
        'start_welcome': '🎉 OvozPay ga xush kelibsiz!...',
        'help_title': '📋 OvozPay buyruqlari yordami',
        # ... остальные переводы
    }
}
```

## 🔄 **ПОЛЬЗОВАТЕЛЬСКИЙ ПОТОК**

### 1. Первый запуск (/start)

```
Пользователь -> /start
    ↓
Проверка языка пользователя
    ↓
Если язык не установлен:
    ↓ 
Показать выбор языка (inline клавиатура)
    ↓
Пользователь выбирает язык
    ↓
Сохранение языка в БД
    ↓
Подтверждение на выбранном языке
```

### 2. Смена языка (/settings)

```
Пользователь -> /settings
    ↓
Показать настройки на текущем языке
    ↓
Пользователь -> "🌐 Язык интерфейса"
    ↓
Показать выбор языков
    ↓
Пользователь выбирает новый язык
    ↓
Обновление в БД + подтверждение
```

## 💾 **МОДЕЛЬ ДАННЫХ**

### TelegramUser модель

```python
class TelegramUser(BaseModel):
    language = models.CharField(
        max_length=5,
        choices=[
            ('ru', 'Русский'),
            ('en', 'English'),
            ('uz', 'O\'zbekcha'),
        ],
        default='ru',
        verbose_name='Язык интерфейса'
    )
    preferred_currency = models.CharField(
        max_length=3,
        choices=[
            ('UZS', 'Узбекский сум'),
            ('USD', 'Доллар США'),
            ('EUR', 'Евро'),
            ('RUB', 'Российский рубль'),
        ],
        default='UZS'
    )
```

## 🎯 **ОБРАБОТЧИКИ КОМАНД**

### BasicHandlers - мультиязычные команды

```python
async def handle_start_command(self, update: Dict[str, Any]) -> None:
    # Получаем пользователя
    user = await self.user_service.get_or_create_user(chat_id, user_data)
    
    # Проверяем установленный язык
    if not user.language or user.language == 'ru':
        # Показываем выбор языка
        welcome_text = t.get_text('start_welcome', 'ru')
        choose_text = t.get_text('choose_language', 'ru')
        
        await self.telegram_api.send_message(
            chat_id=chat_id,
            text=f"{welcome_text}\n\n{choose_text}",
            reply_markup=t.get_language_keyboard()
        )
    else:
        # Приветствие на установленном языке
        welcome_text = t.get_text('start_welcome', user.language)
        await self.telegram_api.send_message(chat_id=chat_id, text=welcome_text)
```

### Обработка callback queries

```python
async def handle_callback_query(self, update: Dict[str, Any]) -> None:
    callback_data = callback_query.get('data', '')
    
    # Обработка выбора языка
    if callback_data.startswith('lang_'):
        await self._handle_language_selection(chat_id, callback_data, user)
    
    # Обработка выбора валюты  
    elif callback_data.startswith('curr_'):
        await self._handle_currency_selection(chat_id, callback_data, user)
```

## 🎤 **ГОЛОСОВЫЕ КОМАНДЫ**

### Мультиязычная обработка голоса

```python
async def handle_voice_message(self, update: Dict[str, Any]) -> None:
    # Получаем язык пользователя
    user = await self.user_service.get_user_by_chat_id(chat_id)
    language = user.language
    
    # Сообщение о начале обработки на языке пользователя
    processing_text = t.get_text('voice_processing', language)
    await self.telegram_api.send_message(chat_id=chat_id, text=processing_text)
    
    # Распознавание с учётом языка
    whisper_language = self._get_whisper_language(language)
    transcription = await self.ai_manager.whisper_service.transcribe_audio(
        audio_file_path=audio_file_path,
        language=whisper_language
    )
    
    # Результат на языке пользователя
    transcribed_text = t.get_text('voice_transcribed', language, transcription)
    await self.telegram_api.send_message(chat_id=chat_id, text=transcribed_text)
```

### Маппинг языков для Whisper

```python
def _get_whisper_language(self, bot_language: str) -> str:
    language_map = {
        'ru': 'ru',  # Русский
        'en': 'en',  # Английский 
        'uz': 'uz'   # Узбекский
    }
    return language_map.get(bot_language, 'ru')
```

## 📸 **ФОТОГРАФИИ ЧЕКОВ**

### Мультиязычная обработка фото

```python
async def handle_photo_message(self, update: Dict[str, Any]) -> None:
    # Получаем язык пользователя
    user = await self.user_service.get_user_by_chat_id(chat_id)
    language = user.language
    
    # Сообщение о начале обработки
    processing_text = t.get_text('photo_processing', language)
    await self.telegram_api.send_message(chat_id=chat_id, text=processing_text)
    
    # Результат обработки на языке пользователя
    if receipt_data and receipt_data.get('items'):
        success_text = t.get_text('receipt_processed', language, len(items))
        await self.telegram_api.send_message(chat_id=chat_id, text=success_text)
```

## ⚙️ **НАСТРОЙКИ ПОЛЬЗОВАТЕЛЯ**

### Inline клавиатуры настроек

```python
def get_settings_keyboard(cls, language: str = 'ru') -> Dict[str, Any]:
    return {
        'inline_keyboard': [
            [
                {'text': cls.get_text('settings_language', language), 'callback_data': 'set_language'}
            ],
            [
                {'text': cls.get_text('settings_currency', language), 'callback_data': 'set_currency'}
            ],
            [
                {'text': cls.get_text('settings_phone', language), 'callback_data': 'set_phone'}
            ]
        ]
    }
```

### Смена языка

```python
async def _handle_language_selection(self, chat_id: int, callback_data: str, user: TelegramUser):
    language_map = {
        'lang_ru': 'ru',
        'lang_en': 'en', 
        'lang_uz': 'uz'
    }
    
    new_language = language_map.get(callback_data)
    
    # Обновляем язык в БД
    await self.user_service.update_user_language(chat_id, new_language)
    
    # Подтверждение на новом языке
    confirmation_text = t.get_text('language_set', new_language)
    await self.telegram_api.send_message(chat_id=chat_id, text=confirmation_text)
```

## 🧪 **ТЕСТИРОВАНИЕ**

### Команда тестирования

```bash
# Базовое тестирование
python manage.py test_multilingual_bot

# Тестирование с конкретным chat_id
python manage.py test_multilingual_bot --chat-id 123456789

# Тестирование на английском языке
python manage.py test_multilingual_bot --chat-id 123456789 --language en

# Тестирование на узбекском языке
python manage.py test_multilingual_bot --chat-id 123456789 --language uz
```

### Что тестируется:

1. **Система переводов**
   - Получение текстов на разных языках
   - Форматирование с параметрами
   - Fallback на русский язык

2. **Клавиатуры**
   - Клавиатура выбора языка
   - Клавиатура выбора валюты
   - Клавиатура настроек

3. **Обработка сообщений**
   - Команда /start с выбором языка
   - Симуляция пользовательского взаимодействия

## 📊 **СТАТИСТИКА И ЛОГИРОВАНИЕ**

### Логирование языковых переключений

```python
logger.info(f"Language set to {new_language} for user {chat_id}")
```

### Модели для аналитики

- `MessageLog` - логи всех сообщений с языком пользователя
- `BotStatistics` - статистика по языкам
- `VoiceCommand` - команды с указанием языка распознавания
- `PhotoReceipt` - обработка фото с языком интерфейса

## 🚀 **РАСШИРЕНИЕ СИСТЕМЫ**

### Добавление нового языка

1. **Добавить переводы в translations.py**
```python
TRANSLATIONS = {
    # ... существующие языки
    'new_lang': {
        'start_welcome': 'Перевод на новый язык...',
        # ... все ключи переводов
    }
}
```

2. **Обновить модель TelegramUser**
```python
LANGUAGE_CHOICES = [
    ('ru', 'Русский'),
    ('en', 'English'), 
    ('uz', 'O\'zbekcha'),
    ('new_lang', 'Новый язык'),  # Добавить выбор
]
```

3. **Обновить клавиатуру языков**
```python
def get_language_keyboard(cls) -> Dict[str, Any]:
    return {
        'inline_keyboard': [
            # ... существующие кнопки
            [
                {'text': '🏳️ Новый язык', 'callback_data': 'lang_new_lang'}
            ]
        ]
    }
```

### Добавление новых переводов

```python
# Добавить новый ключ во все языки
TRANSLATIONS = {
    'ru': {
        # ... существующие переводы
        'new_feature': 'Новая функция на русском',
    },
    'en': {
        # ... существующие переводы  
        'new_feature': 'New feature in English',
    },
    'uz': {
        # ... существующие переводы
        'new_feature': 'Yangi funksiya o\'zbek tilida',
    }
}
```

## ✅ **ГОТОВЫЕ ФУНКЦИИ**

- ✅ **Полная мультиязычность интерфейса** (ru/en/uz)
- ✅ **Автоматический выбор языка при первом запуске**
- ✅ **Смена языка через настройки**
- ✅ **Мультиязычные голосовые команды**
- ✅ **Мультиязычная обработка фотографий**
- ✅ **Inline клавиатуры на всех языках**
- ✅ **Локализация валют и настроек**
- ✅ **Система тестирования переводов**
- ✅ **Логирование языковых действий**

## 🎯 **РЕЗУЛЬТАТ**

Теперь OvozPay Bot полностью поддерживает мультиязычность:

1. **При первом запуске** - пользователь выбирает язык интерфейса
2. **Все команды** работают на выбранном языке
3. **Голосовые команды** распознаются на языке пользователя
4. **Фотографии чеков** обрабатываются с интерфейсом на выбранном языке
5. **Настройки** позволяют сменить язык в любой момент
6. **AI обработка** адаптирована под каждый язык

Бот готов к использованию международной аудиторией! 🌟 