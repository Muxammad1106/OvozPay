import aiohttp
import asyncio
import requests
from django.conf import settings
from typing import Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)


class TelegramAPIService:
    def __init__(self, bot_token: str = None):
        self.bot_token = bot_token or settings.TELEGRAM_BOT_TOKEN
        self.base_url = f"https://api.telegram.org/bot{self.bot_token}"
    
    async def send_message_async(
        self, 
        chat_id: int, 
        text: str, 
        parse_mode: str = "HTML",
        reply_markup: Optional[Dict] = None
    ) -> Optional[Dict[str, Any]]:
        url = f"{self.base_url}/sendMessage"
        
        payload = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": parse_mode
        }
        
        if reply_markup:
            payload["reply_markup"] = reply_markup
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload) as response:
                    if response.status == 200:
                        result = await response.json()
                        logger.info(f"Message sent successfully to {chat_id}")
                        return result
                    else:
                        error_text = await response.text()
                        logger.error(f"Failed to send message to {chat_id}: {error_text}")
                        return None
        except Exception as e:
            logger.error(f"Error sending message to {chat_id}: {str(e)}")
            return None
    
    def send_message(
        self, 
        chat_id: int, 
        text: str, 
        parse_mode: str = "HTML",
        reply_markup: Optional[Dict] = None
    ) -> Optional[Dict[str, Any]]:
        url = f"{self.base_url}/sendMessage"
        
        payload = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": parse_mode
        }
        
        if reply_markup:
            payload["reply_markup"] = reply_markup
        
        try:
            response = requests.post(url, json=payload, timeout=10)
            
            if response.status_code == 200:
                logger.info(f"Message sent successfully to {chat_id}")
                return response.json()
            else:
                logger.error(f"Failed to send message to {chat_id}: {response.text}")
                return None
        except Exception as e:
            logger.error(f"Error sending message to {chat_id}: {str(e)}")
            return None
    
    def send_message_to_group(
        self,
        group_chat_id: str,
        text: str,
        parse_mode: str = "HTML"
    ) -> Optional[Dict[str, Any]]:
        return self.send_message(group_chat_id, text, parse_mode)
    
    async def set_webhook(self, webhook_url: str) -> bool:
        url = f"{self.base_url}/setWebhook"
        payload = {"url": webhook_url}
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload) as response:
                    if response.status == 200:
                        result = await response.json()
                        logger.info(f"Webhook set successfully: {result}")
                        return True
                    else:
                        error_text = await response.text()
                        logger.error(f"Failed to set webhook: {error_text}")
                        return False
        except Exception as e:
            logger.error(f"Error setting webhook: {str(e)}")
            return False
    
    async def get_webhook_info(self) -> Optional[Dict[str, Any]]:
        url = f"{self.base_url}/getWebhookInfo"
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        result = await response.json()
                        return result
                    else:
                        error_text = await response.text()
                        logger.error(f"Failed to get webhook info: {error_text}")
                        return None
        except Exception as e:
            logger.error(f"Error getting webhook info: {str(e)}")
            return None
    
    def get_me(self) -> Optional[Dict[str, Any]]:
        url = f"{self.base_url}/getMe"
        
        try:
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Failed to get bot info: {response.text}")
                return None
        except Exception as e:
            logger.error(f"Error getting bot info: {str(e)}")
            return None 