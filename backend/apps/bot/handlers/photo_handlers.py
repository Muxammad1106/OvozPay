"""
Обработчики фотографий и чеков для Telegram бота
Поддержка мультиязычности интерфейса
"""

import logging
import os
import tempfile
from typing import Dict, Any, Optional, List
from django.conf import settings

from ..models import PhotoReceipt
from ..services.telegram_api_service import TelegramAPIService
from ..services.user_service import UserService
from ..utils.translations import t
from services.ai_service_manager import AIServiceManager

logger = logging.getLogger(__name__)


class PhotoHandlers:
    """Обработчики фотографий и чеков"""
    
    def __init__(self):
        self.telegram_api = TelegramAPIService()
        self.user_service = UserService()
        self.ai_manager = AIServiceManager()
    
    async def handle_photo_message(self, update: Dict[str, Any]) -> None:
        """
        Обработка фотографий (чеков)
        """
        try:
            message = update.get('message', {})
            chat_id = message.get('chat', {}).get('id')
            photo = message.get('photo', [])
            
            if not chat_id or not photo:
                logger.error("No chat_id or photo in photo message")
                return
            
            # Получаем пользователя и язык
            user = await self.user_service.get_user_by_chat_id(chat_id)
            if not user:
                logger.error(f"User not found for chat_id {chat_id}")
                return
            
            language = user.language
            
            # Показываем сообщение о начале обработки
            processing_text = t.get_text('photo_processing', language)
            await self.telegram_api.send_message(
                chat_id=chat_id,
                text=processing_text
            )
            
            # Берём фото наилучшего качества (последнее в массиве)
            best_photo = photo[-1]
            file_id = best_photo.get('file_id', '')
            
            # Создаём запись в базе
            photo_receipt = await self._create_photo_receipt_record(
                user=user,
                file_id=file_id,
                file_size=best_photo.get('file_size', 0)
            )
            
            # Скачиваем и обрабатываем фото
            image_file_path = await self._download_photo_file(file_id)
            if not image_file_path:
                await self._handle_photo_error(chat_id, photo_receipt, language, "Failed to download photo")
                return
            
            try:
                # Извлекаем текст с помощью OCR
                extracted_text = await self._extract_text_from_image(image_file_path)
                if not extracted_text:
                    await self._handle_photo_error(chat_id, photo_receipt, language, "OCR failed")
                    return
                
                # Обновляем запись с извлечённым текстом
                await self._update_photo_receipt(photo_receipt, extracted_text=extracted_text)
                
                # Показываем извлечённый текст (если не слишком длинный)
                if len(extracted_text) <= 300:
                    extracted_text_msg = t.get_text('photo_text_extracted', language, extracted_text)
                    await self.telegram_api.send_message(
                        chat_id=chat_id,
                        text=extracted_text_msg
                    )
                
                # Парсим чек и создаём транзакции
                receipt_data = await self._parse_receipt_data(extracted_text, language)
                if receipt_data and receipt_data.get('items'):
                    await self._create_transactions_from_receipt(
                        chat_id, photo_receipt, receipt_data, user, language
                    )
                else:
                    # Чек не распознан
                    await self._handle_unrecognized_receipt(chat_id, extracted_text, language)
                
            finally:
                # Удаляем временный файл
                if os.path.exists(image_file_path):
                    os.remove(image_file_path)
            
        except Exception as e:
            logger.error(f"Error in handle_photo_message: {e}")
            user = await self.user_service.get_user_by_chat_id(chat_id)
            language = user.language if user else 'ru'
            await self._send_photo_error(chat_id, language)
    
    async def _create_photo_receipt_record(self, user, file_id: str, file_size: int) -> PhotoReceipt:
        """Создание записи фото чека в БД"""
        from asgiref.sync import sync_to_async
        
        @sync_to_async
        def create_record():
            return PhotoReceipt.objects.create(
                user=user,
                telegram_file_id=file_id,
                file_size_bytes=file_size,
                status='processing'
            )
        
        return await create_record()
    
    async def _update_photo_receipt(self, photo_receipt: PhotoReceipt, **kwargs) -> None:
        """Обновление записи фото чека"""
        from asgiref.sync import sync_to_async
        
        @sync_to_async
        def update_record():
            for key, value in kwargs.items():
                setattr(photo_receipt, key, value)
            photo_receipt.save()
        
        await update_record()
    
    async def _download_photo_file(self, file_id: str) -> Optional[str]:
        """Скачивание фото от Telegram"""
        try:
            # Получаем информацию о файле
            file_info = await self.telegram_api.get_file(file_id)
            if not file_info or 'file_path' not in file_info:
                return None
            
            # Скачиваем файл
            file_content = await self.telegram_api.download_file(file_info['file_path'])
            if not file_content:
                return None
            
            # Сохраняем во временный файл
            with tempfile.NamedTemporaryFile(delete=False, suffix='.jpg') as temp_file:
                temp_file.write(file_content)
                return temp_file.name
            
        except Exception as e:
            logger.error(f"Error downloading photo file {file_id}: {e}")
            return None
    
    async def _extract_text_from_image(self, image_file_path: str) -> Optional[str]:
        """Извлечение текста с изображения через OCR"""
        try:
            # Используем EasyOCR сервис
            result = await self.ai_manager.ocr_service.extract_text_from_image(
                image_path=image_file_path
            )
            
            if result and result.get('text'):
                return result['text'].strip()
            
            return None
            
        except Exception as e:
            logger.error(f"Error extracting text from image: {e}")
            return None
    
    async def _parse_receipt_data(self, text: str, language: str) -> Optional[Dict[str, Any]]:
        """Парсинг данных чека через NLP"""
        try:
            # Используем NLP сервис для парсинга чека
            result = await self.ai_manager.nlp_service.parse_receipt(
                text=text,
                language=language
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Error parsing receipt data: {e}")
            return None
    
    async def _create_transactions_from_receipt(
        self, 
        chat_id: int, 
        photo_receipt: PhotoReceipt, 
        receipt_data: Dict[str, Any],
        user,
        language: str
    ) -> None:
        """Создание транзакций из данных чека"""
        try:
            items = receipt_data.get('items', [])
            total_amount = receipt_data.get('total_amount', 0)
            currency = receipt_data.get('currency', user.preferred_currency)
            
            # Здесь будет вызов TransactionService для создания реальных транзакций
            
            # Обновляем запись с результатами
            await self._update_photo_receipt(
                photo_receipt,
                items_count=len(items),
                total_amount=total_amount,
                status='success'
            )
            
            # Отправляем подтверждение
            success_text = t.get_text('receipt_processed', language, len(items))
            
            # Добавляем информацию о сумме если есть
            if total_amount > 0:
                success_text += f"\n💰 {t.get_text('balance_title', language)}: {total_amount} {currency}"
            
            await self.telegram_api.send_message(
                chat_id=chat_id,
                text=success_text
            )
            
            # Если товаров немного, показываем список
            if len(items) <= 10 and items:
                items_text = "\n\n📋 Найденные товары:\n"
                for i, item in enumerate(items[:10], 1):
                    item_name = item.get('name', 'Товар')
                    item_price = item.get('price', 0)
                    items_text += f"{i}. {item_name} - {item_price} {currency}\n"
                
                await self.telegram_api.send_message(
                    chat_id=chat_id,
                    text=items_text
                )
            
            logger.info(f"Receipt processed for user {chat_id}: {len(items)} items, {total_amount} {currency}")
            
        except Exception as e:
            logger.error(f"Error creating transactions from receipt: {e}")
            await self._handle_photo_error(chat_id, photo_receipt, language, str(e))
    
    async def _handle_unrecognized_receipt(self, chat_id: int, text: str, language: str) -> None:
        """Обработка нераспознанного чека"""
        # Возможно, это не чек, а просто текст на изображении
        if len(text) > 10:  # Если есть какой-то текст
            message = f"📄 {t.get_text('photo_text_extracted', language, text[:200])}..."
            if len(text) > 200:
                message += f"\n\n{t.get_text('processing_failed', language)}"
            
            await self.telegram_api.send_message(
                chat_id=chat_id,
                text=message
            )
        else:
            # Совсем ничего не распознано
            error_text = t.get_text('photo_error', language)
            await self.telegram_api.send_message(
                chat_id=chat_id,
                text=error_text
            )
    
    async def _handle_photo_error(
        self, 
        chat_id: int, 
        photo_receipt: PhotoReceipt, 
        language: str, 
        error_message: str
    ) -> None:
        """Обработка ошибки фото"""
        # Обновляем запись с ошибкой
        await self._update_photo_receipt(
            photo_receipt,
            status='failed',
            error_message=error_message
        )
        
        # Отправляем сообщение об ошибке
        await self._send_photo_error(chat_id, language)
    
    async def _send_photo_error(self, chat_id: int, language: str) -> None:
        """Отправка сообщения об ошибке обработки фото"""
        try:
            error_text = t.get_text('photo_error', language)
            await self.telegram_api.send_message(
                chat_id=chat_id,
                text=error_text
            )
        except Exception as e:
            logger.error(f"Failed to send photo error message: {e}") 