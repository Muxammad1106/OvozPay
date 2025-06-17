"""
Обработчик голосовых сообщений в Telegram боте
Интеграция с Whisper AI для распознавания речи и обработки команд
"""

import logging
import tempfile
import os
from typing import Dict, Any, Optional
from datetime import timedelta

from telegram import Update
from telegram.ext import CallbackContext
from django.core.files.uploadedfile import InMemoryUploadedFile

from apps.users.models import User
from apps.ai.services.voice.whisper_service import WhisperVoiceService
from apps.ai.services.nlp.receipt_matcher import ReceiptVoiceMatcher
from apps.ai.models import VoiceResult, OCRResult, ReceiptVoiceMatch
from apps.bot.services.voice_command_processor import VoiceCommandProcessor
from apps.transactions.services.transaction_service import TransactionService


logger = logging.getLogger(__name__)


class VoiceMessageHandler:
    """Обработчик голосовых сообщений в Telegram"""
    
    def __init__(self):
        self.whisper_service = WhisperVoiceService()
        self.voice_processor = VoiceCommandProcessor()
        self.receipt_matcher = ReceiptVoiceMatcher()
        self.transaction_service = TransactionService()
    
    async def handle_voice_message(self, update: Update, context: CallbackContext) -> None:
        """
        Обрабатывает голосовое сообщение пользователя
        
        Args:
            update: Telegram Update объект
            context: Telegram Context объект
        """
        try:
            # Получаем пользователя
            telegram_user = update.effective_user
            user = await self._get_or_create_user(telegram_user)
            
            if not user:
                await update.message.reply_text("❌ Ошибка авторизации. Попробуйте позже.")
                return
            
            # Уведомляем пользователя о начале обработки
            processing_message = await update.message.reply_text(
                "🎤 Обрабатываю голосовое сообщение...\n🔊 Распознаю речь..."
            )
            
            # Получаем голосовое сообщение
            voice = update.message.voice
            voice_file = await voice.get_file()
            
            # Создаем временный файл для аудио
            with tempfile.NamedTemporaryFile(suffix='.ogg', delete=False) as temp_file:
                temp_path = temp_file.name
                await voice_file.download_to_drive(temp_path)
            
            try:
                # Обрабатываем голосовое сообщение
                voice_result = await self._process_voice_recognition(
                    temp_path, user, processing_message
                )
                
                if not voice_result or voice_result.status == 'failed':
                    await processing_message.edit_text(
                        f"❌ Ошибка распознавания голоса: {voice_result.error_message if voice_result else 'Неизвестная ошибка'}\n\n"
                        "💡 Попробуйте:\n"
                        "• Говорить четче и громче\n"
                        "• Записать сообщение в тихом месте\n"
                        "• Повторить команду другими словами"
                    )
                    return
                
                # Обрабатываем команду из распознанного текста
                command_result = await self._process_voice_command(
                    voice_result, user, processing_message
                )
                
                # Отправляем результат пользователю
                await self._send_voice_result(
                    update, voice_result, command_result, processing_message
                )
                
                # Пытаемся автоматически сопоставить с недавними чеками
                await self._try_auto_match_with_receipts(update, voice_result, user)
                
            finally:
                # Удаляем временный файл
                if os.path.exists(temp_path):
                    os.unlink(temp_path)
                    
        except Exception as e:
            logger.error(f"Ошибка обработки голосового сообщения: {e}")
            
            try:
                await update.message.reply_text(
                    "❌ Произошла ошибка при обработке голосового сообщения. Попробуйте еще раз."
                )
            except Exception:
                pass
    
    async def _get_or_create_user(self, telegram_user) -> Optional[User]:
        """Получает или создает пользователя"""
        try:
            # Пытаемся найти пользователя по Telegram ID
            user = User.objects.filter(telegram_id=telegram_user.id).first()
            
            if not user:
                # Создаем нового пользователя
                user = User.objects.create(
                    telegram_id=telegram_user.id,
                    username=telegram_user.username or f"user_{telegram_user.id}",
                    first_name=telegram_user.first_name or "",
                    last_name=telegram_user.last_name or "",
                    is_active=True
                )
                logger.info(f"Создан новый пользователь: {user.username} (ID: {user.telegram_id})")
            
            return user
            
        except Exception as e:
            logger.error(f"Ошибка получения/создания пользователя: {e}")
            return None
    
    async def _process_voice_recognition(
        self, 
        audio_path: str, 
        user: User, 
        processing_message
    ) -> Optional[VoiceResult]:
        """
        Обрабатывает голосовое сообщение через Whisper AI
        
        Args:
            audio_path: Путь к аудио файлу
            user: Пользователь
            processing_message: Сообщение о процессе обработки
            
        Returns:
            VoiceResult: Результат распознавания речи
        """
        try:
            # Создаем Django UploadedFile объект из локального файла
            with open(audio_path, 'rb') as f:
                file_data = f.read()
                
            # Создаем InMemoryUploadedFile для Whisper сервиса
            uploaded_file = InMemoryUploadedFile(
                file=None,
                field_name='audio',
                name='voice_message.ogg',
                content_type='audio/ogg',
                size=len(file_data),
                charset=None
            )
            uploaded_file._file = tempfile.BytesIO(file_data)
            
            # Обновляем статус
            await processing_message.edit_text(
                "🎤 Голосовое сообщение получено\n🤖 Распознаю речь с помощью Whisper AI..."
            )
            
            # Определяем язык пользователя (по умолчанию русский)
            user_language = getattr(user, 'language', 'ru')
            
            # Обрабатываем аудио
            voice_result = self.whisper_service.recognize_voice(
                user=user,
                audio_file=uploaded_file,
                language=user_language,
                task='transcribe'
            )
            
            # Обновляем статус
            detected_lang_emoji = {
                'ru': '🇷🇺',
                'uz': '🇺🇿', 
                'en': '🇺🇸'
            }.get(voice_result.detected_language, '🌍')
            
            await processing_message.edit_text(
                f"✅ Речь распознана {detected_lang_emoji}\n"
                f"📝 Текст: _{voice_result.recognized_text[:50]}..._\n"
                f"🎯 Уверенность: {voice_result.confidence_score * 100:.0f}%\n"
                "🔄 Обрабатываю команду..."
            )
            
            return voice_result
            
        except Exception as e:
            logger.error(f"Ошибка распознавания голоса: {e}")
            return None
    
    async def _process_voice_command(
        self, 
        voice_result: VoiceResult, 
        user: User,
        processing_message
    ) -> Optional[Dict[str, Any]]:
        """
        Обрабатывает команду из распознанного текста
        
        Args:
            voice_result: Результат распознавания речи
            user: Пользователь
            processing_message: Сообщение о процессе
            
        Returns:
            Dict: Результат выполнения команды
        """
        try:
            # Обрабатываем команду через VoiceCommandProcessor
            command_result = self.voice_processor.process_voice_command(
                text=voice_result.recognized_text,
                user=user,
                language=voice_result.detected_language or 'ru'
            )
            
            # Сохраняем результат команды в VoiceResult
            if command_result and voice_result.command:
                voice_result.command.execution_status = command_result.get('status', 'completed')
                voice_result.command.execution_result = command_result.get('data', {})
                voice_result.command.execution_error = command_result.get('error', '')
                voice_result.command.save()
            
            return command_result
            
        except Exception as e:
            logger.error(f"Ошибка обработки команды: {e}")
            return {
                'status': 'error',
                'error': str(e),
                'message': 'Ошибка выполнения команды'
            }
    
    async def _send_voice_result(
        self, 
        update: Update, 
        voice_result: VoiceResult,
        command_result: Optional[Dict[str, Any]], 
        processing_message
    ) -> None:
        """
        Отправляет результат обработки голосового сообщения
        
        Args:
            update: Telegram Update объект
            voice_result: Результат распознавания
            command_result: Результат выполнения команды
            processing_message: Сообщение о процессе обработки
        """
        try:
            # Определяем emoji для языка
            lang_emoji = {
                'ru': '🇷🇺',
                'uz': '🇺🇿',
                'en': '🇺🇸'
            }.get(voice_result.detected_language, '🌍')
            
            message_lines = [
                f"✅ **Голосовое сообщение обработано** {lang_emoji}\n"
            ]
            
            # Показываем распознанный текст
            message_lines.append(f"📝 **Распознанный текст:**")
            message_lines.append(f"_{voice_result.recognized_text}_\n")
            
            # Показываем уверенность распознавания
            confidence_emoji = "🟢" if voice_result.confidence_score > 0.8 else "🟡" if voice_result.confidence_score > 0.5 else "🔴"
            message_lines.append(f"{confidence_emoji} **Точность:** {voice_result.confidence_score * 100:.0f}%")
            
            # Показываем результат выполнения команды
            if command_result:
                status = command_result.get('status', 'unknown')
                
                if status == 'success':
                    message_lines.append(f"\n✅ **Команда выполнена:**")
                    message_lines.append(command_result.get('message', 'Команда успешно выполнена'))
                    
                    # Показываем дополнительные данные если есть
                    if 'data' in command_result:
                        data = command_result['data']
                        if isinstance(data, dict):
                            if 'transaction' in data:
                                trans = data['transaction']
                                message_lines.append(f"💰 Сумма: {trans.get('amount', 0):,.0f} сум")
                                message_lines.append(f"📂 Категория: {trans.get('category', 'Не указана')}")
                
                elif status == 'error':
                    message_lines.append(f"\n❌ **Ошибка выполнения:**")
                    message_lines.append(command_result.get('message', 'Неизвестная ошибка'))
                
                elif status == 'no_command':
                    message_lines.append(f"\n💬 **Команда не распознана**")
                    message_lines.append("Это обычное сообщение, не команда")
                    
                else:
                    message_lines.append(f"\n⚠️ **Статус:** {status}")
                    if 'message' in command_result:
                        message_lines.append(command_result['message'])
            
            # Показываем информацию о сегментах если есть
            if hasattr(voice_result, 'segments_count') and voice_result.segments_count > 1:
                message_lines.append(f"\n📊 **Сегментов речи:** {voice_result.segments_count}")
            
            final_message = "\n".join(message_lines)
            
            await processing_message.edit_text(
                final_message,
                parse_mode='Markdown'
            )
                
        except Exception as e:
            logger.error(f"Ошибка отправки результата голосового сообщения: {e}")
            try:
                await processing_message.edit_text("❌ Ошибка отправки результата")
            except Exception:
                pass
    
    async def _try_auto_match_with_receipts(
        self, 
        update: Update, 
        voice_result: VoiceResult, 
        user: User
    ) -> None:
        """
        Пытается автоматически сопоставить голосовое сообщение с недавними чеками
        
        Args:
            update: Telegram Update объект
            voice_result: Результат распознавания голоса
            user: Пользователь
        """
        try:
            # Ищем недавние чеки (в течение 5 минут)
            recent_ocr_results = OCRResult.objects.filter(
                user=user,
                status='completed',
                created_at__gte=voice_result.created_at - timedelta(minutes=5)
            ).order_by('-created_at')[:3]
            
            if not recent_ocr_results.exists():
                return
            
            best_match = None
            best_confidence = 0.0
            
            # Проверяем каждый чек на совпадение
            for ocr_result in recent_ocr_results:
                try:
                    match = self.receipt_matcher.match_voice_with_receipt(
                        voice_result, ocr_result
                    )
                    
                    if match and match.confidence_score > best_confidence and match.confidence_score > 0.6:
                        best_confidence = match.confidence_score
                        best_match = match
                        
                except Exception as e:
                    logger.error(f"Ошибка сопоставления с чеком {ocr_result.id}: {e}")
                    continue
            
            # Если найдено хорошее сопоставление, уведомляем пользователя
            if best_match and best_match.confidence_score > 0.7:
                await self._send_auto_match_notification(update, best_match)
                
        except Exception as e:
            logger.error(f"Ошибка автоматического сопоставления: {e}")
    
    async def _send_auto_match_notification(
        self, 
        update: Update, 
        match: ReceiptVoiceMatch
    ) -> None:
        """
        Отправляет уведомление об автоматическом сопоставлении
        
        Args:
            update: Telegram Update объект
            match: Результат сопоставления
        """
        try:
            message = "🎯 **Найдено сопоставление с чеком!**\n\n"
            message += f"🧾 **Чек:** {match.ocr_result.shop_name or 'Неизвестный магазин'}\n"
            message += f"💰 **Сумма чека:** {match.total_amount_receipt:,.0f} сум\n"
            
            if match.total_amount_voice > 0:
                message += f"🎤 **Сумма из голоса:** {match.total_amount_voice:,.0f} сум\n"
            
            message += f"🎯 **Точность сопоставления:** {match.confidence_score * 100:.0f}%\n"
            
            if match.matched_items_count > 0:
                message += f"🛍️ **Совпадающих товаров:** {match.matched_items_count}\n"
            
            if match.amount_match_percentage > 80:
                message += f"💯 **Суммы совпадают:** {match.amount_match_percentage:.0f}%\n"
            
            message += f"⏰ **Разница во времени:** {match.time_difference_minutes} мин\n\n"
            
            # Показываем несколько сопоставленных товаров
            if match.matched_items and len(match.matched_items) > 0:
                message += "🛍️ **Сопоставленные товары:**\n"
                for item in match.matched_items[:3]:  # Показываем первые 3
                    voice_item = item.get('voice_item', {})
                    receipt_item = item.get('receipt_item', {})
                    similarity = item.get('similarity', 0) * 100
                    
                    message += f"• {voice_item.get('name', 'N/A')} ↔ {receipt_item.get('name', 'N/A')} ({similarity:.0f}%)\n"
                
                if len(match.matched_items) > 3:
                    message += f"... и еще {len(match.matched_items) - 3} совпадений"
            
            await update.message.reply_text(
                message,
                parse_mode='Markdown'
            )
            
        except Exception as e:
            logger.error(f"Ошибка отправки уведомления о сопоставлении: {e}")


# Создаем глобальный экземпляр обработчика
voice_handler = VoiceMessageHandler() 