"""
Обработчики голосовых сообщений для Telegram бота
Поддержка мультиязычности интерфейса
"""

import logging
import os
import tempfile
from typing import Dict, Any, Optional
from django.conf import settings

from ..models import TelegramUser, VoiceCommand
from ..services.telegram_api_service import TelegramAPIService
from ..services.user_service import UserService
from ..services.transaction_service import TransactionService
from ..services.voice_parser_service import VoiceParserService
from ..utils.translations import t
from services.ai.voice_recognition.whisper_service import WhisperService

logger = logging.getLogger(__name__)


class VoiceHandlers:
    """Обработчики голосовых сообщений бота"""
    
    def __init__(self):
        self.telegram_api = TelegramAPIService()
        self.user_service = UserService()
        self.transaction_service = TransactionService()
        self.voice_parser = VoiceParserService()
        self.whisper_service = WhisperService()
    
    async def handle_voice_message(self, update: Dict[str, Any]) -> None:
        """
        Полный обработчик голосовых сообщений с распознаванием и созданием транзакций
        
        Args:
            update: Обновление от Telegram с голосовым сообщением
        """
        chat_id = None
        voice_log = None
        
        try:
            message = update.get('message', {})
            chat_id = message.get('chat', {}).get('id')
            voice = message.get('voice', {})
            
            if not chat_id or not voice:
                logger.error("Invalid voice message format")
                return
            
            # Получаем пользователя и язык
            user = await self.user_service.get_user_by_chat_id(chat_id)
            if not user:
                logger.error(f"User not found for chat_id: {chat_id}")
                return
            
            language = user.language
            
            # Создаём запись о голосовой команде
            voice_log = await VoiceCommand.objects.acreate(
                user=user,
                telegram_file_id=voice.get('file_id', ''),
                duration_seconds=voice.get('duration', 0),
                status='processing'
            )
            
            # Отправляем сообщение о начале обработки
            processing_text = t.get_text('voice_processing', language)
            processing_message = await self.telegram_api.send_message(
                chat_id=chat_id,
                text=processing_text
            )
            processing_message_id = processing_message.get('result', {}).get('message_id')
            
            # 1. Скачиваем аудио файл
            audio_file_path = await self._download_voice_file(voice.get('file_id'), chat_id)
            if not audio_file_path:
                raise Exception("Не удалось скачать аудио файл")
            
            try:
                # 2. Распознаём речь с помощью Whisper
                transcription_result = await self.whisper_service.transcribe_audio(
                    audio_file_path, 
                    language=language
                )
                
                if not transcription_result or not transcription_result.get('text'):
                    raise Exception("Не удалось распознать речь")
                
                transcription = transcription_result['text']
                
                # Обновляем транскрипцию
                voice_log.transcription = transcription
                await voice_log.asave()
                
                logger.info(f"Transcribed: '{transcription}' for user {chat_id}")
                
                # 3. Парсим транзакцию из текста
                parsed_data = self.voice_parser.parse_voice_text(transcription, language)
                
                if not parsed_data:
                    # Если не удалось распознать транзакцию - просто сохраняем текст
                    voice_log.status = 'success'
                    voice_log.command_type = 'unknown'
                    await voice_log.asave()
                    
                    no_transaction_text = t.get_text('voice_no_transaction', language)
                    final_text = f"{no_transaction_text}\n\n📝 *Распознано:* {transcription}"
                    
                    # Обновляем исходное сообщение
                    if processing_message_id:
                        await self.telegram_api.edit_message_text(
                            chat_id=chat_id,
                            message_id=processing_message_id,
                            text=final_text,
                            parse_mode='Markdown'
                        )
                    else:
                        await self.telegram_api.send_message(
                            chat_id=chat_id,
                            text=final_text,
                            parse_mode='Markdown'
                        )
                    return
                
                # 4. Создаём транзакцию
                transaction = await self.transaction_service.create_transaction_from_voice(
                    chat_id, parsed_data
                )
                
                if transaction:
                    # Успешно создана транзакция
                    voice_log.status = 'success'
                    voice_log.command_type = parsed_data['type']
                    voice_log.extracted_amount = parsed_data['amount']
                    voice_log.created_transaction_id = transaction.id
                    await voice_log.asave()
                    
                    # Отправляем подтверждение (обновляем исходное сообщение)
                    await self._send_transaction_confirmation(
                        chat_id, transaction, parsed_data, language, processing_message_id
                    )
                    
                else:
                    raise Exception("Не удалось создать транзакцию")
                
            finally:
                # Удаляем временный файл
                if audio_file_path and os.path.exists(audio_file_path):
                    os.unlink(audio_file_path)
            
            logger.info(f"Successfully processed voice message for user {chat_id}")
            
        except Exception as e:
            logger.error(f"Error in handle_voice_message: {e}")
            
            # Обновляем статус ошибки
            if voice_log:
                voice_log.status = 'failed'
                voice_log.error_message = str(e)
                await voice_log.asave()
            
            # Отправляем сообщение об ошибке
            if chat_id:
                user = await self.user_service.get_user_by_chat_id(chat_id)
                language = user.language if user else 'ru'
                await self._send_error_message(chat_id, language)
    
    async def _download_voice_file(self, file_id: str, chat_id: int) -> Optional[str]:
        """Скачивает голосовой файл от Telegram"""
        try:
            # Получаем информацию о файле
            file_info = await self.telegram_api.get_file_info(file_id)
            if not file_info:
                return None
            
            # Скачиваем файл
            file_content = await self.telegram_api.download_file(file_info['file_path'])
            if not file_content:
                return None
            
            # Сохраняем во временный файл
            with tempfile.NamedTemporaryFile(suffix='.ogg', delete=False) as temp_file:
                temp_file.write(file_content)
                return temp_file.name
                
        except Exception as e:
            logger.error(f"Error downloading voice file: {e}")
            return None
    
    async def _send_transaction_confirmation(
        self, 
        chat_id: int, 
        transaction, 
        parsed_data: Dict[str, Any], 
        language: str,
        processing_message_id: Optional[int] = None
    ) -> None:
        """Отправляет подтверждение о созданной транзакции"""
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
            
            # Обновляем исходное сообщение или отправляем новое
            if processing_message_id:
                await self.telegram_api.edit_message_text(
                    chat_id=chat_id,
                    message_id=processing_message_id,
                    text=confirmation_text,
                    parse_mode='Markdown'
                )
            else:
                await self.telegram_api.send_message(
                    chat_id=chat_id,
                    text=confirmation_text,
                    parse_mode='Markdown'
                )
            
        except Exception as e:
            logger.error(f"Error sending transaction confirmation: {e}")
    
    async def _send_error_message(self, chat_id: int, language: str = 'ru') -> None:
        """
        Отправляет сообщение об ошибке пользователю
        
        Args:
            chat_id: ID чата
            language: Язык сообщения
        """
        try:
            error_text = t.get_text('voice_error', language)
            await self.telegram_api.send_message(
                chat_id=chat_id,
                text=error_text
            )
        except Exception as e:
            logger.error(f"Failed to send error message: {e}") 