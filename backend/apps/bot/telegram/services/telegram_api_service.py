import aiohttp
import asyncio
import logging
from typing import Optional, Dict, Any
from django.conf import settings

logger = logging.getLogger(__name__)


class TelegramAPIService:
    """
    Сервис для работы с Telegram Bot API
    """
    
    def __init__(self):
        self.bot_token = settings.TELEGRAM_BOT_TOKEN
        self.base_url = f"https://api.telegram.org/bot{self.bot_token}"
    
    async def send_message(
        self, 
        chat_id: int, 
        text: str, 
        parse_mode: str = 'HTML',
        reply_markup: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Отправляет сообщение пользователю
        
        Args:
            chat_id: ID чата
            text: Текст сообщения
            parse_mode: Режим парсинга (HTML, Markdown)
            reply_markup: Клавиатура
            
        Returns:
            Ответ от Telegram API
        """
        url = f"{self.base_url}/sendMessage"
        data = {
            'chat_id': chat_id,
            'text': text,
            'parse_mode': parse_mode
        }
        
        if reply_markup:
            data['reply_markup'] = reply_markup
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=data) as response:
                    result = await response.json()
                    
                    if response.status == 200 and result.get('ok'):
                        logger.info(f"Сообщение отправлено в чат {chat_id}")
                        return result
                    else:
                        logger.error(f"Ошибка отправки сообщения: {result}")
                        return result
                        
        except Exception as e:
            logger.error(f"Ошибка при отправке сообщения: {e}")
            return {'ok': False, 'error': str(e)}
    
    def send_message_sync(
        self, 
        chat_id: int, 
        text: str, 
        parse_mode: str = 'HTML',
        reply_markup: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Синхронная версия отправки сообщения
        """
        try:
            loop = asyncio.get_event_loop()
            return loop.run_until_complete(
                self.send_message(chat_id, text, parse_mode, reply_markup)
            )
        except RuntimeError:
            # Если цикл событий не запущен, создаем новый
            return asyncio.run(
                self.send_message(chat_id, text, parse_mode, reply_markup)
            )
    
    async def send_group_message(
        self, 
        chat_id: str, 
        text: str, 
        parse_mode: str = 'HTML'
    ) -> Dict[str, Any]:
        """
        Отправляет сообщение в группу/канал
        
        Args:
            chat_id: ID группы/канала (может начинаться с @)
            text: Текст сообщения
            parse_mode: Режим парсинга
            
        Returns:
            Ответ от Telegram API
        """
        return await self.send_message(chat_id, text, parse_mode)
    
    async def get_chat_member(self, chat_id: int, user_id: int) -> Dict[str, Any]:
        """
        Получает информацию о участнике чата
        """
        url = f"{self.base_url}/getChatMember"
        data = {
            'chat_id': chat_id,
            'user_id': user_id
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=data) as response:
                    result = await response.json()
                    return result
                    
        except Exception as e:
            logger.error(f"Ошибка получения информации о участнике: {e}")
            return {'ok': False, 'error': str(e)}
    
    async def set_webhook(self, webhook_url: str) -> Dict[str, Any]:
        """
        Устанавливает webhook URL
        """
        url = f"{self.base_url}/setWebhook"
        data = {'url': webhook_url}
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=data) as response:
                    result = await response.json()
                    
                    if result.get('ok'):
                        logger.info(f"Webhook установлен: {webhook_url}")
                    else:
                        logger.error(f"Ошибка установки webhook: {result}")
                    
                    return result
                    
        except Exception as e:
            logger.error(f"Ошибка при установке webhook: {e}")
            return {'ok': False, 'error': str(e)}
    
    async def delete_webhook(self) -> Dict[str, Any]:
        """
        Удаляет webhook
        """
        url = f"{self.base_url}/deleteWebhook"
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url) as response:
                    result = await response.json()
                    
                    if result.get('ok'):
                        logger.info("Webhook удален")
                    else:
                        logger.error(f"Ошибка удаления webhook: {result}")
                    
                    return result
                    
        except Exception as e:
            logger.error(f"Ошибка при удалении webhook: {e}")
            return {'ok': False, 'error': str(e)} 