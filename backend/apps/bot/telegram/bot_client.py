"""
Основной клиент Telegram бота для OvozPay
Поддержка мультиязычности и AI интеграции
"""

import logging
import asyncio
import threading
from typing import Dict, Any
from django.conf import settings

from ..services.telegram_api_service import TelegramAPIService
from ..services.user_service import UserService
from ..handlers.basic_handlers import BasicHandlers
from ..handlers.voice_handlers import VoiceHandlers
from ..handlers.photo_handlers import PhotoHandlers

logger = logging.getLogger(__name__)


class TelegramBotClient:
    """
    Основной клиент для обработки обновлений от Telegram
    """
    
    def __init__(self):
        self.telegram_api = TelegramAPIService()
        self.user_service = UserService()
        
        # Инициализируем обработчики
        self.basic_handlers = BasicHandlers()
        self.voice_handlers = VoiceHandlers()
        self.photo_handlers = PhotoHandlers()
        
        # Маппинг команд к обработчикам
        self.command_handlers = {
            '/start': self.basic_handlers.handle_start_command,
            '/menu': self.basic_handlers.handle_menu_command,
            '/help': self.basic_handlers.handle_help_command,
            '/balance': self.basic_handlers.handle_balance_command,
            '/settings': self.basic_handlers.handle_settings_command,
        }
    
    def handle_update(self, update: Dict[str, Any]) -> None:
        """
        Основной метод обработки обновлений
        """
        try:
            logger.info(f"Processing update: {update}")
            
            # Проверяем тип обновления
            if 'message' in update:
                self._handle_message(update)
            elif 'callback_query' in update:
                self._handle_callback_query(update)
            else:
                logger.warning(f"Unknown update type: {update}")
                
        except Exception as e:
            logger.error(f"Error processing update: {e}")
    
    def _handle_message(self, update: Dict[str, Any]) -> None:
        """
        Обрабатывает различные типы сообщений
        """
        try:
            message = update.get('message', {})
            
            # Обновляем активность пользователя
            chat_id = message.get('chat', {}).get('id')
            if chat_id:
                self._run_async_in_thread(self.user_service.update_user_activity(chat_id))
            
            # Определяем тип сообщения и запускаем соответствующий обработчик
            if 'text' in message:
                self._handle_text_message(update)
            elif 'voice' in message:
                self._handle_voice_message(update)
            elif 'photo' in message:
                self._handle_photo_message(update)
            elif 'contact' in message:
                self._handle_contact_message(update)
            else:
                # Неподдерживаемый тип сообщения
                self._handle_unsupported_message(update)
                    
        except Exception as e:
            logger.error(f"Error handling message: {e}")
    
    def _handle_text_message(self, update: Dict[str, Any]) -> None:
        """
        Обрабатывает текстовые сообщения и команды
        """
        try:
            message = update.get('message', {})
            text = message.get('text', '').strip()
            
            # Проверяем, является ли сообщение командой
            if text.startswith('/'):
                self._handle_command(update)
            else:
                # Обычное текстовое сообщение
                self._run_async_in_thread(
                    self.basic_handlers.handle_text_message(update)
                )
                
        except Exception as e:
            logger.error(f"Error handling text message: {e}")
    
    def _handle_command(self, update: Dict[str, Any]) -> None:
        """
        Обрабатывает команды бота
        """
        try:
            message = update.get('message', {})
            text = message.get('text', '').strip()
            command = text.split()[0].lower()
            
            if command in self.command_handlers:
                # Запускаем обработчик команды
                self._run_async_in_thread(
                    self.command_handlers[command](update)
                )
            else:
                # Неизвестная команда
                self._run_async_in_thread(
                    self.basic_handlers.handle_text_message(update)
                )
                
        except Exception as e:
            logger.error(f"Error handling command: {e}")
    
    def _handle_voice_message(self, update: Dict[str, Any]) -> None:
        """
        Обрабатывает голосовые сообщения
        """
        try:
            self._run_async_in_thread(
                self.voice_handlers.handle_voice_message(update)
            )
            
        except Exception as e:
            logger.error(f"Error handling voice message: {e}")
    
    def _handle_photo_message(self, update: Dict[str, Any]) -> None:
        """
        Обрабатывает фотографии
        """
        try:
            self._run_async_in_thread(
                self.photo_handlers.handle_photo_message(update)
            )
            
        except Exception as e:
            logger.error(f"Error handling photo message: {e}")
    
    def _handle_callback_query(self, update: Dict[str, Any]) -> None:
        """
        Обрабатывает callback queries (нажатия на inline кнопки)
        """
        try:
            self._run_async_in_thread(
                self.basic_handlers.handle_callback_query(update)
            )
            
        except Exception as e:
            logger.error(f"Error handling callback query: {e}")
    
    def _handle_contact_message(self, update: Dict[str, Any]) -> None:
        """
        Обрабатывает сообщения с контактами (номерами телефонов)
        """
        try:
            message = update.get('message', {})
            contact = message.get('contact', {})
            chat_id = message.get('chat', {}).get('id')
            
            if not chat_id or not contact:
                return
            
            phone_number = contact.get('phone_number', '')
            if phone_number:
                # Сохраняем номер телефона
                self._run_async_in_thread(
                    self.user_service.update_user_phone(chat_id, phone_number)
                )
                
                # Отправляем подтверждение
                self._run_async_in_thread(
                    self._send_phone_confirmation(chat_id)
                )
            
        except Exception as e:
            logger.error(f"Error handling contact message: {e}")
    
    def _handle_unsupported_message(self, update: Dict[str, Any]) -> None:
        """
        Обрабатывает неподдерживаемые типы сообщений
        """
        try:
            message = update.get('message', {})
            chat_id = message.get('chat', {}).get('id')
            
            if chat_id:
                self._run_async_in_thread(
                    self._send_unsupported_message_info(chat_id)
                )
            
        except Exception as e:
            logger.error(f"Error handling unsupported message: {e}")
    
    async def _send_phone_confirmation(self, chat_id: int) -> None:
        """Отправляет подтверждение сохранения номера телефона"""
        try:
            user = await self.user_service.get_user_by_chat_id(chat_id)
            language = user.language if user else 'ru'
            
            from ..utils.translations import t
            confirmation_text = t.get_text('phone_set', language)
            
            await self.telegram_api.send_message(
                chat_id=chat_id,
                text=confirmation_text
            )
            
        except Exception as e:
            logger.error(f"Error sending phone confirmation: {e}")
    
    async def _send_unsupported_message_info(self, chat_id: int) -> None:
        """Отправляет информацию о неподдерживаемом типе сообщения"""
        try:
            user = await self.user_service.get_user_by_chat_id(chat_id)
            language = user.language if user else 'ru'
            
            from ..utils.translations import t
            
            if language == 'ru':
                text = (
                    "❌ Неподдерживаемый тип сообщения.\n\n"
                    "Поддерживаются:\n"
                    "🎤 Голосовые сообщения\n"
                    "📸 Фотографии чеков\n"
                    "📝 Текстовые команды"
                )
            elif language == 'en':
                text = (
                    "❌ Unsupported message type.\n\n"
                    "Supported:\n"
                    "🎤 Voice messages\n"
                    "📸 Receipt photos\n"
                    "📝 Text commands"
                )
            else:  # uz
                text = (
                    "❌ Qo'llab-quvvatlanmaydigan xabar turi.\n\n"
                    "Qo'llab-quvvatlanadi:\n"
                    "🎤 Ovozli xabarlar\n"
                    "📸 Chek rasmlari\n"
                    "📝 Matnli buyruqlar"
                )
            
            await self.telegram_api.send_message(
                chat_id=chat_id,
                text=text
            )
            
        except Exception as e:
            logger.error(f"Error sending unsupported message info: {e}")
    
    def _run_async_in_thread(self, coro) -> None:
        """
        Запускает асинхронную функцию в отдельном потоке
        """
        def run_async():
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(coro)
                loop.close()
            except Exception as e:
                logger.error(f"Error in async thread: {e}")
        
        thread = threading.Thread(target=run_async)
        thread.start()
    
    def get_bot_info(self) -> Dict[str, Any]:
        """Возвращает информацию о боте"""
        return {
            'name': 'OvozPay Bot',
            'version': '2.0.0',
            'features': [
                'Multilingual interface (ru/en/uz)',
                'Voice command processing',
                'Receipt photo OCR',
                'Financial transaction management',
                'AI-powered text analysis'
            ],
            'supported_languages': ['ru', 'en', 'uz'],
            'supported_currencies': ['UZS', 'USD', 'EUR', 'RUB']
        } 