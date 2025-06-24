"""
Сервис для работы с Telegram Bot API
"""

import logging
import asyncio
import aiohttp
from typing import Dict, Any, Optional
from django.conf import settings

logger = logging.getLogger(__name__)


class TelegramAPIService:
    """Сервис для работы с Telegram Bot API"""
    
    def __init__(self):
        self.token = getattr(settings, 'TELEGRAM_BOT_TOKEN', '')
        self.base_url = f"https://api.telegram.org/bot{self.token}"
        self.file_url = f"https://api.telegram.org/file/bot{self.token}"
    
    async def send_message(
        self, 
        chat_id: int, 
        text: str, 
        reply_markup: Optional[Dict[str, Any]] = None,
        parse_mode: str = 'HTML'
    ) -> Optional[Dict[str, Any]]:
        """Отправка сообщения"""
        url = f"{self.base_url}/sendMessage"
        data = {
            'chat_id': chat_id,
            'text': text,
            'parse_mode': parse_mode
        }
        
        if reply_markup:
            data['reply_markup'] = reply_markup
        
        return await self._make_request('POST', url, data)
    
    async def edit_message_text(
        self, 
        chat_id: int, 
        message_id: int, 
        text: str, 
        reply_markup: Optional[Dict[str, Any]] = None,
        parse_mode: str = 'HTML'
    ) -> Optional[Dict[str, Any]]:
        """Редактирование сообщения"""
        url = f"{self.base_url}/editMessageText"
        data = {
            'chat_id': chat_id,
            'message_id': message_id,
            'text': text,
            'parse_mode': parse_mode
        }
        
        if reply_markup:
            data['reply_markup'] = reply_markup
        
        return await self._make_request('POST', url, data)
    
    async def get_file(self, file_id: str) -> Optional[Dict[str, Any]]:
        """Получение информации о файле"""
        url = f"{self.base_url}/getFile"
        data = {'file_id': file_id}
        
        return await self._make_request('POST', url, data)
    
    async def download_file(self, file_path: str) -> Optional[bytes]:
        """Скачивание файла"""
        url = f"{self.file_url}/{file_path}"
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        return await response.read()
                    return None
        except Exception as e:
            logger.error(f"Error downloading file {file_path}: {e}")
            return None
    
    async def answer_callback_query(
        self, 
        callback_query_id: str, 
        text: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Ответ на callback query"""
        url = f"{self.base_url}/answerCallbackQuery"
        data = {'callback_query_id': callback_query_id}
        
        if text:
            data['text'] = text
        
        return await self._make_request('POST', url, data)
    
    async def set_webhook(self, webhook_url: str) -> Optional[Dict[str, Any]]:
        """Установка webhook"""
        url = f"{self.base_url}/setWebhook"
        data = {'url': webhook_url}
        
        return await self._make_request('POST', url, data)
    
    async def get_webhook_info(self) -> Optional[Dict[str, Any]]:
        """Получение информации о webhook"""
        url = f"{self.base_url}/getWebhookInfo"
        
        return await self._make_request('GET', url)
    
    async def get_file_info(self, file_id: str) -> Optional[Dict[str, Any]]:
        """Получение информации о файле"""
        return await self.get_file(file_id)
    
    async def _make_request(
        self, 
        method: str, 
        url: str, 
        data: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        """Выполнение HTTP запроса к Telegram API"""
        try:
            async with aiohttp.ClientSession() as session:
                if method.upper() == 'GET':
                    async with session.get(url, params=data) as response:
                        result = await response.json()
                else:
                    async with session.post(url, json=data) as response:
                        result = await response.json()
                
                if result.get('ok'):
                    return result.get('result')
                else:
                    logger.error(f"Telegram API error: {result}")
                    return None
                
        except Exception as e:
            logger.error(f"Error making request to {url}: {e}")
            return None 