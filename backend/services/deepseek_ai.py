"""
DeepSeek AI API интеграция для OvozPay
Сервис для обработки голосовых сообщений и изображений через DeepSeek API
"""

import os
import base64
import httpx
import asyncio
from typing import Optional, Dict, Any
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

class DeepSeekAIService:
    """Сервис для работы с DeepSeek AI API"""
    
    def __init__(self):
        self.api_key = getattr(settings, 'DEEPSEEK_API_KEY', None)
        self.base_url = "https://api.deepseek.com/v1"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
    
    async def speech_to_text(self, audio_file_path: str) -> Optional[str]:
        """
        Преобразование голосового сообщения в текст
        
        Args:
            audio_file_path: Путь к аудио файлу
            
        Returns:
            Распознанный текст или None при ошибке
        """
        try:
            # Читаем аудио файл
            with open(audio_file_path, 'rb') as audio_file:
                audio_data = audio_file.read()
                audio_base64 = base64.b64encode(audio_data).decode('utf-8')
            
            # Подготавливаем запрос
            payload = {
                "model": "deepseek-reasoner",
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": "Преобразуй это голосовое сообщение в текст. Отвечай только текстом без дополнительных комментариев:"
                            },
                            {
                                "type": "audio",
                                "audio": {
                                    "data": audio_base64,
                                    "format": "ogg"  # или другой формат
                                }
                            }
                        ]
                    }
                ],
                "max_tokens": 1000,
                "temperature": 0.1
            }
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers=self.headers,
                    json=payload
                )
                
                if response.status_code == 200:
                    result = response.json()
                    text = result['choices'][0]['message']['content'].strip()
                    logger.info(f"Speech-to-text успешно: {len(text)} символов")
                    return text
                else:
                    logger.error(f"DeepSeek API ошибка: {response.status_code} - {response.text}")
                    return None
                    
        except Exception as e:
            logger.error(f"Ошибка в speech_to_text: {str(e)}")
            return None
    
    async def image_to_text(self, image_file_path: str, prompt: str = None) -> Optional[str]:
        """
        Извлечение текста из изображения (OCR)
        
        Args:
            image_file_path: Путь к изображению
            prompt: Дополнительная инструкция для обработки
            
        Returns:
            Извлечённый текст или None при ошибке
        """
        try:
            # Читаем изображение
            with open(image_file_path, 'rb') as image_file:
                image_data = image_file.read()
                image_base64 = base64.b64encode(image_data).decode('utf-8')
            
            # Базовый промпт для OCR
            base_prompt = "Извлеки весь текст с этого изображения. Если это чек или документ, сохрани структуру и форматирование. Отвечай только извлечённым текстом:"
            
            if prompt:
                base_prompt = f"{base_prompt}\n\nДополнительная инструкция: {prompt}"
            
            # Подготавливаем запрос
            payload = {
                "model": "deepseek-reasoner",
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": base_prompt
                            },
                            {
                                "type": "image",
                                "image": {
                                    "data": image_base64
                                }
                            }
                        ]
                    }
                ],
                "max_tokens": 2000,
                "temperature": 0.1
            }
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers=self.headers,
                    json=payload
                )
                
                if response.status_code == 200:
                    result = response.json()
                    text = result['choices'][0]['message']['content'].strip()
                    logger.info(f"Image-to-text успешно: {len(text)} символов")
                    return text
                else:
                    logger.error(f"DeepSeek API ошибка: {response.status_code} - {response.text}")
                    return None
                    
        except Exception as e:
            logger.error(f"Ошибка в image_to_text: {str(e)}")
            return None
    
    def sync_speech_to_text(self, audio_file_path: str) -> Optional[str]:
        """Синхронная версия speech_to_text"""
        return asyncio.run(self.speech_to_text(audio_file_path))
    
    def sync_image_to_text(self, image_file_path: str, prompt: str = None) -> Optional[str]:
        """Синхронная версия image_to_text"""
        return asyncio.run(self.image_to_text(image_file_path, prompt))


# Глобальный экземпляр сервиса
deepseek_service = DeepSeekAIService()


# Функции-обёртки для удобства использования
def process_voice_message(audio_file_path: str) -> Optional[str]:
    """
    Обработка голосового сообщения
    
    Args:
        audio_file_path: Путь к аудио файлу
        
    Returns:
        Распознанный текст или None
    """
    return deepseek_service.sync_speech_to_text(audio_file_path)


def process_receipt_image(image_file_path: str) -> Optional[str]:
    """
    Обработка изображения чека
    
    Args:
        image_file_path: Путь к изображению
        
    Returns:
        Извлечённый текст или None
    """
    prompt = "Это чек или документ. Извлеки всю информацию: сумму, дату, товары, магазин и т.д."
    return deepseek_service.sync_image_to_text(image_file_path, prompt)


def process_document_image(image_file_path: str) -> Optional[str]:
    """
    Обработка изображения документа
    
    Args:
        image_file_path: Путь к изображению
        
    Returns:
        Извлечённый текст или None
    """
    prompt = "Это документ. Извлеки весь текст максимально точно, сохраняя структуру."
    return deepseek_service.sync_image_to_text(image_file_path, prompt) 