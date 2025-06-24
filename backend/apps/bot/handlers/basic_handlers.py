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
        """Обработчик callback queries (нажатий на inline кнопки)"""
        try:
            callback_query = update.get('callback_query', {})
            message = callback_query.get('message', {})
            chat_id = message.get('chat', {}).get('id')
            callback_data = callback_query.get('data', '')
            
            if not chat_id or not callback_data:
                return
            
            # Получаем пользователя
            user = await self.user_service.get_user_by_chat_id(chat_id)
            if not user:
                return
            
            # Обрабатываем выбор языка
            if callback_data.startswith('lang_'):
                await self._handle_language_selection(chat_id, callback_data, user)
            
            # Обрабатываем выбор валюты
            elif callback_data.startswith('curr_'):
                await self._handle_currency_selection(chat_id, callback_data, user)
            
            # Обрабатываем главное меню
            elif callback_data == 'show_balance':
                await self._show_balance(chat_id, user)
            elif callback_data == 'show_history':
                await self._show_history(chat_id, user)
            elif callback_data == 'show_categories':
                await self._show_categories(chat_id, user)
            elif callback_data == 'show_goals':
                await self._show_goals(chat_id, user)
            elif callback_data == 'show_debts':
                await self._show_debts(chat_id, user)
            elif callback_data == 'show_settings':
                await self._show_settings_menu(chat_id, user)
            elif callback_data == 'show_help':
                await self._show_help_menu(chat_id, user)
            elif callback_data == 'back_to_menu':
                await self._show_main_menu(chat_id, user)
            
            # Обрабатываем настройки
            elif callback_data == 'set_language':
                await self._show_language_settings(chat_id, user)
            elif callback_data == 'set_currency':
                await self._show_currency_settings(chat_id, user)
            elif callback_data == 'set_phone':
                await self._show_phone_settings(chat_id, user)
            
            # Отвечаем на callback query
            await self.telegram_api.answer_callback_query(
                callback_query_id=callback_query.get('id', '')
            )
            
        except Exception as e:
            logger.error(f"Error in handle_callback_query: {e}")
    
    async def handle_text_message(self, update: Dict[str, Any]) -> None:
        """Обработчик текстовых сообщений"""
        try:
            message = update.get('message', {})
            chat_id = message.get('chat', {}).get('id')
            text = message.get('text', '')
            
            if not chat_id or not text:
                return
            
            # Получаем пользователя и язык
            user = await self.user_service.get_user_by_chat_id(chat_id)
            if not user:
                await self.handle_start_command(update)
                return
            
            language = user.language
            
            # Обрабатываем номер телефона, если пользователь в режиме ввода
            session = await self.user_service.get_user_session(chat_id)
            if session and session.state == 'waiting_phone':
                await self._handle_phone_input(chat_id, text, user)
                return
            
            # Попытка обработать как транзакцию
            transaction_created = await self._try_parse_transaction_text(chat_id, text, user)
            
            if not transaction_created:
                # Если не удалось создать транзакцию - показываем справку
                invalid_text = t.get_text('invalid_command', language)
                help_hint = t.get_text('help_commands', language)
                
                await self.telegram_api.send_message(
                    chat_id=chat_id,
                    text=f"{invalid_text}\n\n💡 **Примеры команд:**\n{help_hint}",
                    parse_mode='Markdown'
                )
            
        except Exception as e:
            logger.error(f"Error in handle_text_message: {e}")
            user = await self.user_service.get_user_by_chat_id(chat_id)
            language = user.language if user else 'ru'
            await self._send_error_message(chat_id, language)

    async def _try_parse_transaction_text(self, chat_id: int, text: str, user: TelegramUser) -> bool:
        """Пытается распарсить текст как транзакцию"""
        try:
            logger.info(f"Attempting to parse text: '{text}' for user {chat_id} (language: {user.language})")
            
            from ..services.text_parser_service import TextParserService
            
            parser = TextParserService()
            parsed_data = parser.parse_transaction_text(text, user.language)
            
            logger.info(f"Parser result: {parsed_data}")
            
            if parsed_data:
                # Создаем транзакцию
                logger.info(f"Creating transaction from parsed data: {parsed_data}")
                transaction = await self.transaction_service.create_transaction_from_text(
                    chat_id, parsed_data
                )
                
                if transaction:
                    logger.info(f"Transaction created successfully: {transaction.id}")
                    # Отправляем подтверждение
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
            amount_text = f"{transaction.amount:,.0f}"
            
            if transaction.category:
                category_text = transaction.category.name
            else:
                category_text = parsed_data.get('category', 'Без категории')
            
            confirmation_text = t.get_text('voice_transaction_created', language).format(
                type=transaction_type,
                amount=amount_text,
                category=category_text,
                description=transaction.description or ''
            )
            
            await self.telegram_api.send_message(
                chat_id=chat_id,
                text=f"📝 **Создано из текста:**\n\n{confirmation_text}",
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
            balance_text += f"\n\n📊 *Статистика:*"
            balance_text += f"\n💚 Доходы: {stats.get('total_income', 0):,.0f}"
            balance_text += f"\n💸 Расходы: {stats.get('total_expense', 0):,.0f}"
            balance_text += f"\n📝 Транзакций: {stats.get('transactions_count', 0)}"
        
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
        """Показать категории"""
        language = user.language
        feature_text = t.get_text('feature_not_implemented', language)
        
        back_keyboard = {
            'inline_keyboard': [
                [{'text': t.get_text('back_button', language), 'callback_data': 'back_to_menu'}]
            ]
        }
        
        await self.telegram_api.send_message(
            chat_id=chat_id,
            text=f"📂 Категории\n\n{feature_text}",
            reply_markup=back_keyboard
        )

    async def _show_goals(self, chat_id: int, user: TelegramUser) -> None:
        """Показать финансовые цели"""
        language = user.language
        feature_text = t.get_text('feature_not_implemented', language)
        
        back_keyboard = {
            'inline_keyboard': [
                [{'text': t.get_text('back_button', language), 'callback_data': 'back_to_menu'}]
            ]
        }
        
        await self.telegram_api.send_message(
            chat_id=chat_id,
            text=f"🎯 Финансовые цели\n\n{feature_text}",
            reply_markup=back_keyboard
        )

    async def _show_debts(self, chat_id: int, user: TelegramUser) -> None:
        """Показать долги"""
        language = user.language
        feature_text = t.get_text('feature_not_implemented', language)
        
        back_keyboard = {
            'inline_keyboard': [
                [{'text': t.get_text('back_button', language), 'callback_data': 'back_to_menu'}]
            ]
        }
        
        await self.telegram_api.send_message(
            chat_id=chat_id,
            text=f"💸 Долги\n\n{feature_text}",
            reply_markup=back_keyboard
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
        
        back_keyboard = {
            'inline_keyboard': [
                [{'text': t.get_text('back_button', language), 'callback_data': 'back_to_menu'}]
            ]
        }
        
        await self.telegram_api.send_message(
            chat_id=chat_id,
            text=f"{help_title}\n{help_commands}",
            reply_markup=back_keyboard
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