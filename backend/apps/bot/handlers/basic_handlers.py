"""
Базовые обработчики команд для Telegram бота
Поддержка мультиязычности интерфейса
"""

import logging
import json
from typing import Dict, Any, Optional
from django.conf import settings
from asgiref.sync import sync_to_async

from ..models import TelegramUser, BotSession
from ..services.telegram_api_service import TelegramAPIService
from ..services.user_service import UserService
from ..services.transaction_service import TransactionService
from ..utils.translations import t

logger = logging.getLogger(__name__)


class BasicHandlers:
    """Обработчики базовых команд бота"""
    
    def __init__(self):
        self.telegram_api = TelegramAPIService()
        self.user_service = UserService()
        self.transaction_service = TransactionService()
    
    async def handle_start_command(self, update: Dict[str, Any]) -> None:
        """
        Обработчик команды /start
        Показывает выбор языка для новых пользователей
        """
        try:
            message = update.get('message', {})
            chat_id = message.get('chat', {}).get('id')
            user_data = message.get('from', {})
            
            if not chat_id:
                logger.error("No chat_id in /start command")
                return
            
            # Получаем или создаём пользователя
            user = await self.user_service.get_or_create_user(
                chat_id=chat_id,
                user_data=user_data
            )
            
            # Если у пользователя не установлен язык, показываем выбор
            if not user.language or user.language == 'ru':
                welcome_text = t.get_text('start_welcome', 'ru')
                choose_text = t.get_text('choose_language', 'ru')
                
                await self.telegram_api.send_message(
                    chat_id=chat_id,
                    text=f"{welcome_text}\n\n{choose_text}",
                    reply_markup=t.get_language_keyboard()
                )
            else:
                # Показываем приветствие и главное меню
                welcome_text = t.get_text('start_welcome', user.language)
                menu_text = t.get_text('main_menu', user.language)
                
                await self.telegram_api.send_message(
                    chat_id=chat_id,
                    text=f"{welcome_text}\n\n{menu_text}",
                    reply_markup=t.get_main_menu_keyboard(user.language)
                )
            
            logger.info(f"Handled /start for user {chat_id}")
            
        except Exception as e:
            logger.error(f"Error in handle_start_command: {e}")
            await self._send_error_message(chat_id, 'ru')
    
    async def handle_help_command(self, update: Dict[str, Any]) -> None:
        """Обработчик команды /help"""
        try:
            message = update.get('message', {})
            chat_id = message.get('chat', {}).get('id')
            
            if not chat_id:
                return
            
            # Получаем язык пользователя
            user = await self.user_service.get_user_by_chat_id(chat_id)
            language = user.language if user else 'ru'
            
            help_title = t.get_text('help_title', language)
            help_commands = t.get_text('help_commands', language)
            
            await self.telegram_api.send_message(
                chat_id=chat_id,
                text=f"{help_title}\n{help_commands}"
            )
            
            logger.info(f"Handled /help for user {chat_id}")
            
        except Exception as e:
            logger.error(f"Error in handle_help_command: {e}")
            await self._send_error_message(chat_id, 'ru')
    
    async def handle_balance_command(self, update: Dict[str, Any]) -> None:
        """Обработчик команды /balance"""
        try:
            message = update.get('message', {})
            chat_id = message.get('chat', {}).get('id')
            
            if not chat_id:
                return
            
            # Получаем пользователя и язык
            user = await self.user_service.get_user_by_chat_id(chat_id)
            if not user:
                await self.handle_start_command(update)
                return
            
            language = user.language
            balance_title = t.get_text('balance_title', language)
            
            # Получаем реальный баланс пользователя
            balance, stats = await self.transaction_service.get_user_balance(chat_id)
            
            balance_text = f"{balance_title}\n\n💰 *{balance:,.0f}* {user.preferred_currency}"
            
            if stats.get('transactions_count', 0) > 0:
                balance_text += f"\n\n📊 *Статистика:*"
                balance_text += f"\n💚 Доходы: {stats.get('total_income', 0):,.0f}"
                balance_text += f"\n💸 Расходы: {stats.get('total_expense', 0):,.0f}"
                balance_text += f"\n📝 Транзакций: {stats.get('transactions_count', 0)}"
            
            await self.telegram_api.send_message(
                chat_id=chat_id,
                text=balance_text,
                parse_mode='Markdown'
            )
            
            logger.info(f"Handled /balance for user {chat_id}")
            
        except Exception as e:
            logger.error(f"Error in handle_balance_command: {e}")
            user = await self.user_service.get_user_by_chat_id(chat_id)
            language = user.language if user else 'ru'
            await self._send_error_message(chat_id, language)
    
    async def handle_menu_command(self, update: Dict[str, Any]) -> None:
        """Обработчик команды /menu - показ главного меню"""
        try:
            message = update.get('message', {})
            chat_id = message.get('chat', {}).get('id')
            
            if not chat_id:
                return
            
            # Получаем пользователя и язык
            user = await self.user_service.get_user_by_chat_id(chat_id)
            if not user:
                await self.handle_start_command(update)
                return
            
            language = user.language
            menu_text = t.get_text('main_menu', language)
            
            await self.telegram_api.send_message(
                chat_id=chat_id,
                text=menu_text,
                reply_markup=t.get_main_menu_keyboard(language)
            )
            
            logger.info(f"Handled /menu for user {chat_id}")
            
        except Exception as e:
            logger.error(f"Error in handle_menu_command: {e}")
            user = await self.user_service.get_user_by_chat_id(chat_id)
            language = user.language if user else 'ru'
            await self._send_error_message(chat_id, language)

    async def handle_settings_command(self, update: Dict[str, Any]) -> None:
        """Обработчик команды /settings"""
        try:
            message = update.get('message', {})
            chat_id = message.get('chat', {}).get('id')
            
            if not chat_id:
                return
            
            # Получаем пользователя и язык
            user = await self.user_service.get_user_by_chat_id(chat_id)
            if not user:
                await self.handle_start_command(update)
                return
            
            language = user.language
            settings_title = t.get_text('settings_title', language)
            
            await self.telegram_api.send_message(
                chat_id=chat_id,
                text=settings_title,
                reply_markup=t.get_settings_keyboard(language)
            )
            
            logger.info(f"Handled /settings for user {chat_id}")
            
        except Exception as e:
            logger.error(f"Error in handle_settings_command: {e}")
            user = await self.user_service.get_user_by_chat_id(chat_id)
            language = user.language if user else 'ru'
            await self._send_error_message(chat_id, language)
    
    async def handle_callback_query(self, update: Dict[str, Any]) -> None:
        """Обработчик callback queries - теперь используем ReplyKeyboard вместо InlineKeyboard"""
        try:
            callback_query = update.get('callback_query', {})
            
            # Просто отвечаем на callback query, если вдруг старые кнопки ещё где-то остались
            await self.telegram_api.answer_callback_query(
                callback_query_id=callback_query.get('id', ''),
                text="Используйте кнопки клавиатуры ниже 👇"
            )
            
        except Exception as e:
            logger.error(f"Error in handle_callback_query: {e}")
    
    async def handle_text_message(self, update: Dict[str, Any]) -> None:
        """Обработчик текстовых сообщений"""
        try:
            message = update.get('message', {})
            chat_id = message.get('chat', {}).get('id')
            text = message.get('text', '').strip()
            
            if not chat_id or not text:
                return
            
            # Получаем пользователя
            user = await self.user_service.get_user_by_chat_id(chat_id)
            if not user:
                await self.handle_start_command(update)
                return
            
            logger.info(f"Processing text message from {chat_id}: '{text}'")
            
            # Обработка кнопок языка
            if text in ['🇷🇺 Русский', '🇺🇸 English', '🇺🇿 O\'zbekcha']:
                await self._handle_language_button(chat_id, text, user)
                return
            
            # Обработка кнопок валют
            if any(currency in text for currency in ['💵', '💶', '💴', '💷']):
                await self._handle_currency_button(chat_id, text, user)
                return
            
            # Обработка кнопок главного меню
            language = user.language
            menu_buttons = {
                t.get_text('menu_balance', language): 'show_balance',
                t.get_text('menu_history', language): 'show_history',
                t.get_text('menu_categories', language): 'show_categories',
                t.get_text('menu_goals', language): 'show_goals',
                t.get_text('menu_debts', language): 'show_debts',
                t.get_text('menu_settings', language): 'show_settings',
                t.get_text('menu_help', language): 'show_help',
                t.get_text('back_button', language): 'back_to_menu'
            }
            
            if text in menu_buttons:
                await self._handle_menu_button(chat_id, menu_buttons[text], user)
                return
            
            # Обработка кнопок настроек
            settings_buttons = {
                t.get_text('settings_language', language): 'set_language',
                t.get_text('settings_currency', language): 'set_currency',
                t.get_text('settings_phone', language): 'set_phone'
            }
            
            if text in settings_buttons:
                await self._handle_settings_button(chat_id, settings_buttons[text], user)
                return
            
            # Обработка кнопок категорий (если текст начинается с emoji категории)
            if any(emoji in text for emoji in ['💸', '💰']):
                await self._show_category_details(chat_id, text, user)
                return
            
            # Пробуем распарсить как транзакцию
            if await self._try_parse_transaction_text(chat_id, text, user):
                return
            
            # Пробуем распарсить как команду управления
            if await self._try_parse_management_command(chat_id, text, user):
                return
            
            # Если ничего не подошло
            await self.telegram_api.send_message(
                chat_id=chat_id,
                text=t.get_text('invalid_command', language)
            )
            
        except Exception as e:
            logger.error(f"Error in handle_text_message: {e}")
            user = await self.user_service.get_user_by_chat_id(chat_id) if chat_id else None
            language = user.language if user else 'ru'
            await self._send_error_message(chat_id, language)

    async def _handle_language_button(self, chat_id: int, text: str, user: TelegramUser) -> None:
        """Обработка нажатия кнопки языка"""
        language_map = {
            '🇷🇺 Русский': 'ru',
            '🇺🇸 English': 'en',
            '🇺🇿 O\'zbekcha': 'uz'
        }
        
        new_language = language_map.get(text)
        if new_language:
            await self._handle_language_selection(chat_id, f'lang_{new_language}', user)

    async def _handle_currency_button(self, chat_id: int, text: str, user: TelegramUser) -> None:
        """Обработка нажатия кнопки валюты"""
        currency_map = {
            '💵': 'usd',
            '💶': 'eur', 
            '💴': 'uzs',
            '💷': 'rub'
        }
        
        for symbol, currency in currency_map.items():
            if symbol in text:
                await self._handle_currency_selection(chat_id, f'curr_{currency}', user)
                break

    async def _handle_menu_button(self, chat_id: int, action: str, user: TelegramUser) -> None:
        """Обработка нажатий кнопок главного меню"""
        if action == 'show_balance':
            await self._show_balance(chat_id, user)
        elif action == 'show_history':
            await self._show_history(chat_id, user)
        elif action == 'show_categories':
            await self._show_categories(chat_id, user)
        elif action == 'show_goals':
            await self._show_goals(chat_id, user)
        elif action == 'show_debts':
            await self._show_debts(chat_id, user)
        elif action == 'show_settings':
            await self._show_settings_menu(chat_id, user)
        elif action == 'show_help':
            await self._show_help_menu(chat_id, user)
        elif action == 'back_to_menu':
            await self._show_main_menu(chat_id, user)

    async def _handle_settings_button(self, chat_id: int, action: str, user: TelegramUser) -> None:
        """Обработка нажатий кнопок настроек"""
        if action == 'set_language':
            await self._show_language_settings(chat_id, user)
        elif action == 'set_currency':
            await self._show_currency_settings(chat_id, user)
        elif action == 'set_phone':
            await self._show_phone_settings(chat_id, user)

    async def _try_parse_transaction_text(self, chat_id: int, text: str, user: TelegramUser) -> bool:
        """Пытается распарсить текст как транзакцию"""
        try:
            logger.info(f"Attempting to parse text: '{text}' for user {chat_id} (language: {user.language})")
            
            from ..services.text_parser_service import TextParserService
            
            parser = TextParserService()
            # Используем асинхронный парсинг с конвертацией валют
            parsed_data = await parser.parse_transaction_text(
                text, 
                user.language, 
                user.preferred_currency
            )
            
            logger.info(f"Parser result: {parsed_data}")
            
            if parsed_data:
                # Создаем транзакцию
                logger.info(f"Creating transaction from parsed data: {parsed_data}")
                transaction = await self.transaction_service.create_transaction_from_text(
                    chat_id, parsed_data
                )
                
                if transaction:
                    logger.info(f"Transaction created successfully: {transaction.id}")
                    # Отправляем подтверждение с информацией о конвертации
                    await self._send_text_transaction_confirmation(
                        chat_id, transaction, parsed_data, user.language
                    )
                    return True
                else:
                    logger.error("Failed to create transaction from text")
            else:
                logger.warning(f"No transaction data found in text: '{text}'")
            
            return False
            
        except Exception as e:
            logger.error(f"Error parsing transaction text: {e}", exc_info=True)
            return False

    async def _try_parse_management_command(self, chat_id: int, text: str, user: TelegramUser) -> bool:
        """Пытается распарсить текст как команду управления"""
        try:
            logger.info(f"Checking for management command: '{text}' for user {chat_id}")
            
            from ..services.text_parser_service import TextParserService
            
            parser = TextParserService()
            management_data = parser.parse_management_command(text, user.language)
            
            if management_data:
                logger.info(f"Management command detected: {management_data}")
                
                if management_data['type'] == 'change_language':
                    await self._handle_voice_language_change(chat_id, management_data['target_language'], user)
                    return True
                
                elif management_data['type'] == 'change_currency':
                    await self._handle_voice_currency_change(chat_id, management_data['target_currency'], user)
                    return True
                
                elif management_data['type'] == 'create_category':
                    await self._handle_voice_category_creation(chat_id, management_data['category_name'], user)
                    return True
                
                elif management_data['type'] == 'delete_category':
                    await self._handle_voice_category_deletion(chat_id, management_data['category_name'], user)
                    return True
                
                elif management_data['type'] == 'delete_transaction':
                    await self._handle_voice_transaction_deletion(chat_id, management_data['target'], user)
                    return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error parsing management command: {e}", exc_info=True)
            return False

    async def _handle_voice_language_change(self, chat_id: int, target_language: str, user: TelegramUser) -> None:
        """Обрабатывает голосовую команду смены языка"""
        try:
            # Обновляем язык
            await self.user_service.update_user_language(chat_id, target_language)
            
            # Подтверждение на новом языке
            confirmations = {
                'ru': '✅ Язык изменён на русский',
                'en': '✅ Language changed to English', 
                'uz': '✅ Til o\'zbekchaga o\'zgartirildi'
            }
            
            confirmation = confirmations.get(target_language, confirmations['ru'])
            
            await self.telegram_api.send_message(
                chat_id=chat_id,
                text=confirmation
            )
            
            logger.info(f"Language changed via voice command to {target_language} for user {chat_id}")
            
        except Exception as e:
            logger.error(f"Error handling voice language change: {e}")

    async def _handle_voice_currency_change(self, chat_id: int, target_currency: str, user: TelegramUser) -> None:
        """Обрабатывает голосовую команду смены валюты"""
        try:
            # Обновляем валюту
            await self.user_service.update_user_currency(chat_id, target_currency)
            
            # Получаем название валюты
            currency_names = {
                'USD': {'ru': 'доллары США', 'en': 'US Dollars', 'uz': 'AQSH dollarlari'},
                'EUR': {'ru': 'евро', 'en': 'Euro', 'uz': 'Evro'},
                'RUB': {'ru': 'российские рубли', 'en': 'Russian Rubles', 'uz': 'Rossiya rublari'},
                'UZS': {'ru': 'узбекские сумы', 'en': 'Uzbek Som', 'uz': 'O\'zbek so\'mi'}
            }
            
            currency_name = currency_names.get(target_currency, {}).get(user.language, target_currency)
            
            confirmations = {
                'ru': f'✅ Валюта изменена на {currency_name}',
                'en': f'✅ Currency changed to {currency_name}',
                'uz': f'✅ Valyuta {currency_name}ga o\'zgartirildi'
            }
            
            confirmation = confirmations.get(user.language, confirmations['ru'])
            
            await self.telegram_api.send_message(
                chat_id=chat_id,
                text=confirmation
            )
            
            logger.info(f"Currency changed via voice command to {target_currency} for user {chat_id}")
            
        except Exception as e:
            logger.error(f"Error handling voice currency change: {e}")

    async def _handle_voice_category_creation(self, chat_id: int, category_name: str, user: TelegramUser) -> None:
        """Обрабатывает голосовую команду создания категории"""
        try:
            # Получаем Django пользователя
            django_user = await self._get_or_create_django_user(user)
            
            # Создаем категорию
            category_created = await self._create_custom_category(django_user, category_name)
            
            if category_created:
                success_text = t.get_text('category_created', user.language)
                await self.telegram_api.send_message(
                    chat_id=chat_id,
                    text=f"✅ {success_text}: **{category_name}**",
                    parse_mode='Markdown'
                )
                logger.info(f"Category '{category_name}' created via voice command for user {chat_id}")
            else:
                error_text = t.get_text('category_exists', user.language)
                await self.telegram_api.send_message(
                    chat_id=chat_id,
                    text=f"⚠️ {error_text}: **{category_name}**",
                    parse_mode='Markdown'
                )
                
        except Exception as e:
            logger.error(f"Error handling voice category creation: {e}")
            error_text = t.get_text('processing_failed', user.language)
            await self.telegram_api.send_message(
                chat_id=chat_id,
                text=f"❌ {error_text}"
            )

    async def _handle_voice_category_deletion(self, chat_id: int, category_name: str, user: TelegramUser) -> None:
        """Обрабатывает голосовую команду удаления категории"""
        try:
            # Получаем Django пользователя
            django_user = await self._get_or_create_django_user(user)
            
            # Ищем и удаляем категорию
            category_deleted = await self._delete_user_category(django_user, category_name)
            
            if category_deleted:
                success_text = t.get_text('category_deleted', user.language) if hasattr(t, 'category_deleted') else 'Категория удалена'
                await self.telegram_api.send_message(
                    chat_id=chat_id,
                    text=f"✅ {success_text}: **{category_name}**",
                    parse_mode='Markdown'
                )
                logger.info(f"Category '{category_name}' deleted via voice command for user {chat_id}")
            else:
                error_text = t.get_text('category_not_found', user.language) if hasattr(t, 'category_not_found') else 'Категория не найдена'
                await self.telegram_api.send_message(
                    chat_id=chat_id,
                    text=f"⚠️ {error_text}: **{category_name}**",
                    parse_mode='Markdown'
                )
                
        except Exception as e:
            logger.error(f"Error handling voice category deletion: {e}")
            error_text = t.get_text('processing_failed', user.language)
            await self.telegram_api.send_message(
                chat_id=chat_id,
                text=f"❌ {error_text}"
            )

    async def _handle_voice_transaction_deletion(self, chat_id: int, target: str, user: TelegramUser) -> None:
        """Обрабатывает голосовую команду удаления транзакции"""
        try:
            # Получаем Django пользователя
            django_user = await self._get_or_create_django_user(user)
            
            # Ищем и удаляем транзакцию
            transaction_deleted = await self._delete_user_transaction(django_user, target)
            
            if transaction_deleted:
                success_text = t.get_text('transaction_deleted', user.language) if hasattr(t, 'transaction_deleted') else 'Транзакция удалена'
                await self.telegram_api.send_message(
                    chat_id=chat_id,
                    text=f"✅ {success_text}: **{target}**",
                    parse_mode='Markdown'
                )
                logger.info(f"Transaction '{target}' deleted via voice command for user {chat_id}")
            else:
                error_text = t.get_text('transaction_not_found', user.language) if hasattr(t, 'transaction_not_found') else 'Транзакция не найдена'
                await self.telegram_api.send_message(
                    chat_id=chat_id,
                    text=f"⚠️ {error_text}: **{target}**",
                    parse_mode='Markdown'
                )
                
        except Exception as e:
            logger.error(f"Error handling voice transaction deletion: {e}")
            error_text = t.get_text('processing_failed', user.language)
            await self.telegram_api.send_message(
                chat_id=chat_id,
                text=f"❌ {error_text}"
            )

    async def _get_or_create_django_user(self, telegram_user):
        """Получает или создает Django User"""
        try:
            from asgiref.sync import sync_to_async
            from apps.users.models import User
            
            @sync_to_async
            def get_user():
                if telegram_user.phone_number:
                    user, created = User.objects.get_or_create(
                        phone_number=telegram_user.phone_number,
                        defaults={
                            'first_name': telegram_user.first_name,
                            'last_name': telegram_user.last_name,
                            'username': telegram_user.username,
                        }
                    )
                else:
                    user, created = User.objects.get_or_create(
                        username=telegram_user.username or f"tg_{telegram_user.telegram_user_id}",
                        defaults={
                            'first_name': telegram_user.first_name,
                            'last_name': telegram_user.last_name,
                            'phone_number': telegram_user.phone_number or '',
                        }
                    )
                return user
            
            return await get_user()
            
        except Exception as e:
            logger.error(f"Error getting Django user: {e}")
            return None

    async def _create_custom_category(self, user, category_name: str):
        """Создает пользовательскую категорию"""
        try:
            from apps.categories.models import Category
            
            @sync_to_async
            def create_category():
                # Нормализуем название категории
                normalized_name = category_name.strip().title()
                
                # Используем get_or_create для предотвращения дублирования
                # Ищем по любому типу транзакции - если уже есть, не создаем
                existing = Category.objects.filter(
                    user=user,
                    name__iexact=normalized_name
                ).first()
                
                if existing:
                    logger.info(f"Категория '{normalized_name}' уже существует")
                    return None
                
                # Создаем новую категорию для расходов (по умолчанию)
                category, created = Category.objects.get_or_create(
                    user=user,
                    name=normalized_name,
                    type='expense',  # по умолчанию создаем категорию расходов
                    defaults={
                        'is_default': False
                    }
                )
                
                if created:
                    logger.info(f"Создана новая пользовательская категория: {category.name}")
                    return category
                else:
                    logger.info(f"Категория уже существует: {category.name}")
                    return None
            
            return await create_category()
            
        except Exception as e:
            logger.error(f"Error creating custom category: {e}")
            return None

    async def _delete_user_category(self, user, category_name: str) -> bool:
        """Удаляет пользовательскую категорию"""
        try:
            from apps.categories.models import Category
            
            @sync_to_async
            def delete_category():
                # Ищем категорию пользователя (только пользовательские, не системные)
                category = Category.objects.filter(
                    user=user,
                    name__iexact=category_name,
                    is_custom=True  # Можно удалять только пользовательские категории
                ).first()
                
                if category:
                    category.delete()
                    return True
                return False
            
            return await delete_category()
            
        except Exception as e:
            logger.error(f"Error deleting category: {e}")
            return False

    async def _delete_user_transaction(self, user, target: str) -> bool:
        """Удаляет транзакцию пользователя по описанию или ID"""
        try:
            from apps.transactions.models import Transaction
            
            @sync_to_async
            def delete_transaction():
                # Сначала пытаемся найти по точному описанию (последняя транзакция)
                transaction = Transaction.objects.filter(
                    user=user,
                    description__icontains=target
                ).order_by('-created_at').first()
                
                # Если не нашли по описанию, пытаемся найти по ID
                if not transaction and target.isdigit():
                    try:
                        transaction = Transaction.objects.filter(
                            user=user,
                            id=target
                        ).first()
                    except:
                        pass
                
                if transaction:
                    transaction.delete()
                    return True
                return False
            
            return await delete_transaction()
            
        except Exception as e:
            logger.error(f"Error deleting transaction: {e}")
            return False

    async def _send_text_transaction_confirmation(
        self, 
        chat_id: int, 
        transaction, 
        parsed_data: Dict[str, Any], 
        language: str
    ) -> None:
        """Отправляет подтверждение о транзакции из текста"""
        try:
            transaction_type = '💰 Доход' if transaction.type == 'income' else '💸 Расход'
            final_amount = f"{transaction.amount:,.0f} {transaction.category.user.telegramuser_set.first().preferred_currency if transaction.category and transaction.category.user and transaction.category.user.telegramuser_set.exists() else 'UZS'}"
            
            if transaction.category:
                category_text = transaction.category.name
            else:
                category_text = parsed_data.get('category', 'Без категории')
            
            # Базовый текст подтверждения
            confirmation_text = f"{transaction_type}\n💰 Сумма: **{final_amount}**\n📂 Категория: **{category_text}**"
            
            if transaction.description:
                confirmation_text += f"\n📝 Описание: **{transaction.description}**"
            
            # Добавляем информацию о конвертации если была
            if parsed_data.get('original_currency') and parsed_data.get('original_amount'):
                original_currency = parsed_data['original_currency']
                original_amount = parsed_data['original_amount']
                current_currency = parsed_data['currency']
                
                if original_currency != current_currency:
                    confirmation_text += f"\n\n💱 **Конвертировано:**\n{original_amount} {original_currency} → {transaction.amount:,.2f} {current_currency}"
            
            await self.telegram_api.send_message(
                chat_id=chat_id,
                text=f"📝 **Транзакция создана из текста:**\n\n{confirmation_text}",
                parse_mode='Markdown'
            )
            
        except Exception as e:
            logger.error(f"Error sending text transaction confirmation: {e}")
    
    async def _handle_language_selection(self, chat_id: int, callback_data: str, user: TelegramUser) -> None:
        """Обработка выбора языка"""
        language_map = {
            'lang_ru': 'ru',
            'lang_en': 'en', 
            'lang_uz': 'uz'
        }
        
        new_language = language_map.get(callback_data)
        if not new_language:
            return
        
        # Обновляем язык пользователя
        await self.user_service.update_user_language(chat_id, new_language)
        
        # Отправляем подтверждение на новом языке
        confirmation_text = t.get_text('language_set', new_language)
        await self.telegram_api.send_message(
            chat_id=chat_id,
            text=confirmation_text
        )
        
        # Отправляем приветственное сообщение на новом языке
        welcome_text = t.get_text('start_welcome', new_language)
        await self.telegram_api.send_message(
            chat_id=chat_id,
            text=welcome_text
        )
        
        logger.info(f"Language set to {new_language} for user {chat_id}")
    
    async def _handle_currency_selection(self, chat_id: int, callback_data: str, user: TelegramUser) -> None:
        """Обработка выбора валюты"""
        currency_map = {
            'curr_usd': 'USD',
            'curr_eur': 'EUR',
            'curr_uzs': 'UZS',
            'curr_rub': 'RUB'
        }
        
        new_currency = currency_map.get(callback_data)
        if not new_currency:
            return
        
        # Обновляем валюту пользователя
        await self.user_service.update_user_currency(chat_id, new_currency)
        
        # Отправляем подтверждение
        language = user.language
        currency_name = t.get_text(new_currency.lower(), language)
        confirmation_text = t.get_text('currency_set', language).format(currency_name)
        
        await self.telegram_api.send_message(
            chat_id=chat_id,
            text=confirmation_text
        )
        
        logger.info(f"Currency set to {new_currency} for user {chat_id}")
    
    async def _show_language_settings(self, chat_id: int, user: TelegramUser) -> None:
        """Показать настройки языка"""
        language = user.language
        choose_text = t.get_text('choose_language', language)
        
        await self.telegram_api.send_message(
            chat_id=chat_id,
            text=choose_text,
            reply_markup=t.get_language_keyboard()
        )
    
    async def _show_currency_settings(self, chat_id: int, user: TelegramUser) -> None:
        """Показать настройки валюты"""
        language = user.language
        
        await self.telegram_api.send_message(
            chat_id=chat_id,
            text=t.get_text('settings_currency', language),
            reply_markup=t.get_currency_keyboard(language)
        )
    
    async def _show_phone_settings(self, chat_id: int, user: TelegramUser) -> None:
        """Показать настройки номера телефона"""
        language = user.language
        
        # Устанавливаем состояние ожидания номера
        await self.user_service.set_user_state(chat_id, 'waiting_phone')
        
        # Запрашиваем номер
        phone_text = t.get_text('phone_request', language)
        await self.telegram_api.send_message(
            chat_id=chat_id,
            text=phone_text
        )
    
    async def _handle_phone_input(self, chat_id: int, phone: str, user: TelegramUser) -> None:
        """Обработка ввода номера телефона"""
        language = user.language
        
        # Простая валидация номера телефона
        if len(phone) >= 9 and (phone.startswith('+') or phone.startswith('998') or phone.isdigit()):
            # Сохраняем номер
            await self.user_service.update_user_phone(chat_id, phone)
            
            # Убираем состояние ожидания
            await self.user_service.set_user_state(chat_id, None)
            
            # Подтверждение
            confirmation_text = t.get_text('phone_set', language)
            await self.telegram_api.send_message(
                chat_id=chat_id,
                text=confirmation_text
            )
        else:
            # Ошибка валидации
            error_text = t.get_text('phone_request', language)
            await self.telegram_api.send_message(
                chat_id=chat_id,
                text=f"❌ {error_text}"
            )
    
    async def _show_main_menu(self, chat_id: int, user: TelegramUser) -> None:
        """Показать главное меню"""
        language = user.language
        menu_text = t.get_text('main_menu', language)
        
        await self.telegram_api.send_message(
            chat_id=chat_id,
            text=menu_text,
            reply_markup=t.get_main_menu_keyboard(language)
        )

    async def _show_balance(self, chat_id: int, user: TelegramUser) -> None:
        """Показать баланс пользователя"""
        language = user.language
        balance_title = t.get_text('balance_title', language)
        
        # Получаем реальный баланс пользователя
        balance, stats = await self.transaction_service.get_user_balance(chat_id)
        
        balance_text = f"{balance_title}\n\n💰 *{balance:,.0f}* {user.preferred_currency}"
        
        if stats.get('transactions_count', 0) > 0:
            balance_text += f"\n\n📊 *{t.get_text('statistics', language)}*"
            balance_text += f"\n💚 {t.get_text('income', language)}: {stats.get('total_income', 0):,.0f}"
            balance_text += f"\n💸 {t.get_text('expense', language)}: {stats.get('total_expense', 0):,.0f}"
            balance_text += f"\n📝 {t.get_text('transactions', language)}: {stats.get('transactions_count', 0)}"
        
        # Добавляем кнопку "Назад"
        back_keyboard = {
            'inline_keyboard': [
                [{'text': t.get_text('back_button', language), 'callback_data': 'back_to_menu'}]
            ]
        }
        
        await self.telegram_api.send_message(
            chat_id=chat_id,
            text=balance_text,
            parse_mode='Markdown',
            reply_markup=back_keyboard
        )

    async def _show_history(self, chat_id: int, user: TelegramUser) -> None:
        """Показать историю транзакций"""
        language = user.language
        feature_text = t.get_text('feature_not_implemented', language)
        
        back_keyboard = {
            'inline_keyboard': [
                [{'text': t.get_text('back_button', language), 'callback_data': 'back_to_menu'}]
            ]
        }
        
        await self.telegram_api.send_message(
            chat_id=chat_id,
            text=f"📊 История транзакций\n\n{feature_text}",
            reply_markup=back_keyboard
        )

    async def _show_categories(self, chat_id: int, user: TelegramUser) -> None:
        """Показать категории пользователя"""
        language = user.language
        
        try:
            # Получаем Django пользователя
            django_user = await self._get_or_create_django_user(user)
            
            if not django_user:
                back_keyboard = {
                    'inline_keyboard': [
                        [{'text': t.get_text('back_button', language), 'callback_data': 'back_to_menu'}]
                    ]
                }
                await self.telegram_api.send_message(
                    chat_id=chat_id,
                    text="❌ Ошибка получения категорий",
                    reply_markup=back_keyboard
                )
                return
            
            # Получаем категории пользователя
            categories = await self._get_user_categories(django_user)
            
            back_keyboard = {
                'inline_keyboard': [
                    [{'text': t.get_text('back_button', language), 'callback_data': 'back_to_menu'}]
                ]
            }
            
            if not categories:
                no_categories_text = f"📂 **{t.get_text('menu_categories', language)}**\n\n{t.get_text('no_categories', language)}\n\n💡 {t.get_text('create_category_hint', language)}"
                
                await self.telegram_api.send_message(
                    chat_id=chat_id,
                    text=no_categories_text,
                    parse_mode='Markdown',
                    reply_markup=back_keyboard
                )
                return
            
            # Создаем клавиатуру с кнопками категорий
            categories_keyboard = await self._create_categories_keyboard(categories, language)
            
            categories_text = f"📂 **{t.get_text('categories_title', language)}**\n\n💡 {t.get_text('create_category_hint', language)}"
            
            await self.telegram_api.send_message(
                chat_id=chat_id,
                text=categories_text,
                parse_mode='Markdown',
                reply_markup=categories_keyboard
            )
            
        except Exception as e:
            logger.error(f"Error showing categories: {e}")
            back_keyboard = {
                'inline_keyboard': [
                    [{'text': t.get_text('back_button', language), 'callback_data': 'back_to_menu'}]
                ]
            }
            await self.telegram_api.send_message(
                chat_id=chat_id,
                text=t.get_text('error_occurred', language),
                reply_markup=back_keyboard
            )

    async def _get_user_categories(self, user):
        """Получает категории пользователя"""
        try:
            from asgiref.sync import sync_to_async
            from apps.categories.models import Category
            
            @sync_to_async
            def get_categories():
                return list(Category.objects.filter(user=user).order_by('name'))
            
            return await get_categories()
            
        except Exception as e:
            logger.error(f"Error getting user categories: {e}")
            return []

    async def _create_categories_keyboard(self, categories, language: str):
        """Создаёт клавиатуру с категориями (ReplyKeyboard)"""
        try:
            if not categories:
                return t.get_main_menu_keyboard(language)
            
            # Группируем категории по 2 в ряд
            keyboard_rows = []
            temp_row = []
            
            for category in categories:
                emoji = '💸' if category.type == 'expense' else '💰'
                button_text = f"{emoji} {category.name}"
                temp_row.append(button_text)
                
                if len(temp_row) == 2:
                    keyboard_rows.append(temp_row)
                    temp_row = []
            
            # Добавляем оставшуюся кнопку
            if temp_row:
                keyboard_rows.append(temp_row)
            
            # Добавляем кнопку "Назад"
            keyboard_rows.append([t.get_text('back_button', language)])
            
            return {
                'keyboard': keyboard_rows,
                'resize_keyboard': True
            }
            
        except Exception as e:
            logger.error(f"Error creating categories keyboard: {e}")
            return t.get_main_menu_keyboard(language)

    async def _show_category_details(self, chat_id: int, category_name: str, user: TelegramUser) -> None:
        """Показывает детали категории и её транзакции (по названию)"""
        language = user.language
        
        try:
            # Получаем Django пользователя
            django_user = await self._get_or_create_django_user(user)
            if not django_user:
                await self.telegram_api.send_message(
                    chat_id=chat_id,
                    text="❌ Ошибка получения данных"
                )
                return
            
            # Получаем категорию по названию
            category, transactions = await self._get_category_by_name(django_user, category_name)
            
            if not category:
                await self.telegram_api.send_message(
                    chat_id=chat_id,
                    text="❌ Категория не найдена"
                )
                return
            
            # Формируем текст с деталями категории
            emoji = '💸' if category.type == 'expense' else '💰'
            
            if not transactions:
                no_transactions_texts = {
                    'ru': f"📂 **{category.name}** {emoji}\n\nВ этой категории пока нет транзакций\n\n💡 Создайте первую транзакцию командой:\n\"потратил 5000 сум на {category.name.lower()}\"",
                    'en': f"📂 **{category.name}** {emoji}\n\nNo transactions in this category yet\n\n💡 Create first transaction with command:\n\"spent 50 dollars on {category.name.lower()}\"",
                    'uz': f"📂 **{category.name}** {emoji}\n\nBu kategoriyada hali tranzaksiyalar yo'q\n\n💡 Birinchi tranzaksiya yarating:\n\"5000 so'm {category.name.lower()}ga sarfladim\""
                }
                
                text = no_transactions_texts.get(language, no_transactions_texts['ru'])
                
                await self.telegram_api.send_message(
                    chat_id=chat_id,
                    text=text,
                    parse_mode='Markdown',
                    reply_markup=t.get_main_menu_keyboard(language)
                )
                return
            
            # Вычисляем статистику
            total_amount = sum(t.amount for t in transactions)
            transactions_count = len(transactions)
            
            text = f"📂 **{category.name}** {emoji}\n\n"
            text += f"💰 Всего: {total_amount:,.0f} {user.preferred_currency}\n"
            text += f"📝 {t.get_text('transactions', language)}: {transactions_count}\n\n"
            text += f"**Последние транзакции:**\n"
            
            # Показываем последние 5 транзакций
            for transaction in transactions[:5]:
                date_str = transaction.created_at.strftime('%d.%m.%Y')
                text += f"• {date_str}: {transaction.amount:,.0f} {user.preferred_currency}"
                if transaction.description:
                    text += f" - {transaction.description}"
                text += "\n"
            
            if len(transactions) > 5:
                text += f"\n... и ещё {len(transactions) - 5} транзакций"
            
            await self.telegram_api.send_message(
                chat_id=chat_id,
                text=text,
                parse_mode='Markdown',
                reply_markup=t.get_main_menu_keyboard(language)
            )
            
        except Exception as e:
            logger.error(f"Error showing category details: {e}")
            await self.telegram_api.send_message(
                chat_id=chat_id,
                text=t.get_text('error_occurred', language)
            )

    async def _get_category_by_name(self, user, category_name: str):
        """Получает категорию по названию и её транзакции"""
        try:
            from asgiref.sync import sync_to_async
            from apps.categories.models import Category
            from apps.transactions.models import Transaction
            
            # Убираем emoji из названия
            clean_name = category_name
            for emoji in ['💸', '💰', '📂']:
                clean_name = clean_name.replace(emoji, '').strip()
            
            @sync_to_async
            def get_data():
                try:
                    category = Category.objects.filter(
                        user=user, 
                        name__icontains=clean_name
                    ).first()
                    
                    if category:
                        transactions = list(Transaction.objects.filter(
                            user=user, 
                            category=category
                        ).order_by('-created_at'))
                        return category, transactions
                    
                    return None, []
                except Exception as e:
                    logger.error(f"Error in get_data: {e}")
                    return None, []
            
            return await get_data()
            
        except Exception as e:
            logger.error(f"Error getting category by name: {e}")
            return None, []

    async def _show_goals(self, chat_id: int, user: TelegramUser) -> None:
        """Показать финансовые цели"""
        language = user.language
        feature_text = t.get_text('feature_not_implemented', language)
        
        await self.telegram_api.send_message(
            chat_id=chat_id,
            text=f"🎯 Финансовые цели\n\n{feature_text}",
            reply_markup=t.get_main_menu_keyboard(language)
        )

    async def _show_debts(self, chat_id: int, user: TelegramUser) -> None:
        """Показать долги"""
        language = user.language
        feature_text = t.get_text('feature_not_implemented', language)
        
        await self.telegram_api.send_message(
            chat_id=chat_id,
            text=f"💸 Долги\n\n{feature_text}",
            reply_markup=t.get_main_menu_keyboard(language)
        )

    async def _show_settings_menu(self, chat_id: int, user: TelegramUser) -> None:
        """Показать меню настроек"""
        language = user.language
        settings_title = t.get_text('settings_title', language)
        
        await self.telegram_api.send_message(
            chat_id=chat_id,
            text=settings_title,
            reply_markup=t.get_settings_keyboard(language)
        )

    async def _show_help_menu(self, chat_id: int, user: TelegramUser) -> None:
        """Показать справку"""
        language = user.language
        help_title = t.get_text('help_title', language)
        help_commands = t.get_text('help_commands', language)
        
        await self.telegram_api.send_message(
            chat_id=chat_id,
            text=f"{help_title}\n{help_commands}",
            reply_markup=t.get_main_menu_keyboard(language)
        )

    async def _send_error_message(self, chat_id: int, language: str = 'ru') -> None:
        """Отправка сообщения об ошибке"""
        try:
            error_text = t.get_text('error_occurred', language)
            await self.telegram_api.send_message(
                chat_id=chat_id,
                text=error_text
            )
        except Exception as e:
            logger.error(f"Failed to send error message: {e}") 