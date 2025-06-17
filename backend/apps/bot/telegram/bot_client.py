from typing import Dict, Any
from apps.bot.telegram.handlers.basic_handlers import start_handler, balance_handler, help_handler
from apps.bot.telegram.services.telegram_api_service import TelegramAPIService
from apps.bot.models import VoiceCommandLog, BotSession
import logging
import asyncio

logger = logging.getLogger(__name__)


class OvozPayBot:
    def __init__(self):
        self.telegram_service = TelegramAPIService()
        self.handlers = {
            '/start': start_handler,
            '/balance': balance_handler,
            '/help': help_handler
        }
    
    async def process_update(self, update_data: Dict[str, Any]) -> None:
        try:
            if 'message' in update_data:
                await self._process_message(update_data)
            elif 'voice' in update_data.get('message', {}):
                await self._process_voice_message(update_data)
        except Exception as e:
            logger.error(f"Error processing update: {str(e)}")
    
    async def _process_message(self, update_data: Dict[str, Any]) -> None:
        message = update_data.get('message', {})
        text = message.get('text', '').strip()
        chat_id = message.get('chat', {}).get('id')
        from_user = message.get('from', {})
        
        if not text or not chat_id:
            return
        
        command = text.split()[0] if text.startswith('/') else None
        
        if command and command in self.handlers:
            try:
                await self.handlers[command](update_data)
            except Exception as e:
                logger.error(f"Error executing command {command}: {str(e)}")
                await self.telegram_service.send_message_async(
                    chat_id=chat_id,
                    text="Произошла ошибка при выполнении команды."
                )
        else:
            await self._handle_text_message(update_data)
    
    async def _handle_text_message(self, update_data: Dict[str, Any]) -> None:
        message = update_data.get('message', {})
        text = message.get('text', '')
        chat_id = message.get('chat', {}).get('id')
        
        try:
            session = BotSession.objects.filter(
                telegram_chat_id=chat_id,
                is_active=True
            ).first()
            
            if session:
                session.add_message()
            
            if any(keyword in text.lower() for keyword in ['потратил', 'купил', 'заплатил']):
                await self._suggest_expense_creation(chat_id, text)
            elif any(keyword in text.lower() for keyword in ['получил', 'заработал', 'зарплата']):
                await self._suggest_income_creation(chat_id, text)
            elif any(keyword in text.lower() for keyword in ['накопить', 'цель', 'копить']):
                await self._suggest_goal_creation(chat_id, text)
            else:
                await self._send_help_suggestion(chat_id)
                
        except Exception as e:
            logger.error(f"Error handling text message: {str(e)}")
    
    async def _process_voice_message(self, update_data: Dict[str, Any]) -> None:
        message = update_data.get('message', {})
        voice = message.get('voice', {})
        chat_id = message.get('chat', {}).get('id')
        from_user = message.get('from', {})
        
        if not voice or not chat_id:
            return
        
        try:
            session = BotSession.objects.filter(
                telegram_chat_id=chat_id,
                is_active=True
            ).first()
            
            if session and session.user:
                voice_log = VoiceCommandLog.objects.create(
                    user=session.user,
                    text="Голосовое сообщение получено",
                    original_audio_duration=voice.get('duration', 0),
                    status='processing'
                )
                
                session.add_message(is_voice=True)
                
                await self.telegram_service.send_message_async(
                    chat_id=chat_id,
                    text="🎤 Голосовое сообщение получено! В данный момент обработка голосовых команд находится в разработке."
                )
                
                voice_log.mark_as_failed("Voice processing not implemented yet")
            else:
                await self.telegram_service.send_message_async(
                    chat_id=chat_id,
                    text="Для использования голосовых команд используйте /start для регистрации."
                )
                
        except Exception as e:
            logger.error(f"Error processing voice message: {str(e)}")
    
    async def _suggest_expense_creation(self, chat_id: int, text: str) -> None:
        suggestion_text = f"""
💸 Похоже, вы хотите добавить расход!

Текст: "{text}"

📱 Для добавления транзакций используйте наше приложение или API.
Команда /help покажет все доступные функции.
"""
        await self.telegram_service.send_message_async(
            chat_id=chat_id,
            text=suggestion_text
        )
    
    async def _suggest_income_creation(self, chat_id: int, text: str) -> None:
        suggestion_text = f"""
💰 Похоже, вы хотите добавить доход!

Текст: "{text}"

📱 Для добавления транзакций используйте наше приложение или API.
Команда /help покажет все доступные функции.
"""
        await self.telegram_service.send_message_async(
            chat_id=chat_id,
            text=suggestion_text
        )
    
    async def _suggest_goal_creation(self, chat_id: int, text: str) -> None:
        suggestion_text = f"""
🎯 Отлично! Хотите создать цель накопления!

Текст: "{text}"

📱 Для создания и управления целями используйте наше приложение.
Команда /help покажет все доступные функции.
"""
        await self.telegram_service.send_message_async(
            chat_id=chat_id,
            text=suggestion_text
        )
    
    async def _send_help_suggestion(self, chat_id: int) -> None:
        help_text = """
🤖 Не понял вашу команду.

Используйте:
/help - для просмотра всех команд
/balance - для проверки баланса
/start - для начала работы

Или отправьте голосовое сообщение! 🎤
"""
        await self.telegram_service.send_message_async(
            chat_id=chat_id,
            text=help_text
        )
    
    def get_bot_info(self) -> Dict[str, Any]:
        return self.telegram_service.get_me()


bot_client = OvozPayBot() 