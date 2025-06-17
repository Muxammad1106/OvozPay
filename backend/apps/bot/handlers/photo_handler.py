"""
Обработчик фото сообщений для Telegram Bot
Интеграция с AI OCR модулем для автоматического сканирования чеков
"""

import logging
import os
import tempfile
from typing import Dict, Any
from decimal import Decimal

from telegram import Update
from telegram.ext import CallbackContext
from django.core.files.uploadedfile import InMemoryUploadedFile

from apps.users.models import User
from apps.ai.services.ocr.tesseract_service import TesseractOCRService
from apps.ai.services.nlp.receipt_matcher import ReceiptVoiceMatcher
from apps.ai.models import OCRResult, VoiceResult, ReceiptVoiceMatch
from apps.transactions.services.transaction_service import TransactionService
from apps.categories.models import Category
from datetime import timedelta


logger = logging.getLogger(__name__)


class PhotoMessageHandler:
    """Обработчик фото сообщений в Telegram"""
    
    def __init__(self):
        self.ocr_service = TesseractOCRService()
        self.transaction_service = TransactionService()
        self.receipt_matcher = ReceiptVoiceMatcher()
    
    async def handle_photo_message(self, update: Update, context: CallbackContext) -> None:
        """
        Обрабатывает фото сообщение пользователя (сканирование чека)
        
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
                "📸 Обрабатываю фото чека...\n🔍 Распознаю текст и товары..."
            )
            
            # Получаем самое большое фото
            photo = update.message.photo[-1]
            photo_file = await photo.get_file()
            
            # Создаем временный файл для фото
            with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as temp_file:
                temp_path = temp_file.name
                await photo_file.download_to_drive(temp_path)
            
            try:
                # Обрабатываем чек через OCR
                ocr_result = await self._process_receipt_ocr(temp_path, user, processing_message)
                
                if not ocr_result or ocr_result.status == 'failed':
                    await processing_message.edit_text(
                        f"❌ Ошибка распознавания чека: {ocr_result.error_message if ocr_result else 'Неизвестная ошибка'}\n\n"
                        "💡 Попробуйте:\n"
                        "• Сделать фото при хорошем освещении\n"
                        "• Держать камеру ровно\n"
                        "• Убедиться что текст четко виден"
                    )
                    return
                
                # Автоматически создаем транзакции
                transactions_created = await self._create_transactions_from_receipt(
                    ocr_result, user, processing_message
                )
                
                # Отправляем результат пользователю
                await self._send_receipt_result(
                    update, ocr_result, transactions_created, processing_message
                )
                
                # Пытаемся автоматически сопоставить с недавними голосовыми сообщениями
                await self._try_auto_match_with_voice(update, ocr_result, user)
                
            finally:
                # Удаляем временный файл
                if os.path.exists(temp_path):
                    os.unlink(temp_path)
                    
        except Exception as e:
            logger.error(f"Ошибка обработки фото сообщения: {e}")
            
            try:
                await update.message.reply_text(
                    "❌ Произошла ошибка при обработке фото. Попробуйте еще раз."
                )
            except Exception:
                pass
    
    async def _get_or_create_user(self, telegram_user) -> User:
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
    
    async def _process_receipt_ocr(self, image_path: str, user: User, 
                                 processing_message) -> OCRResult:
        """
        Обрабатывает изображение чека через OCR
        
        Args:
            image_path: Путь к изображению
            user: Пользователь
            processing_message: Сообщение о процессе обработки
            
        Returns:
            OCRResult: Результат OCR обработки
        """
        try:
            # Создаем Django UploadedFile объект из локального файла
            with open(image_path, 'rb') as f:
                file_data = f.read()
                
            # Создаем InMemoryUploadedFile для OCR сервиса
            uploaded_file = InMemoryUploadedFile(
                file=None,
                field_name='image',
                name='receipt.jpg',
                content_type='image/jpeg',
                size=len(file_data),
                charset=None
            )
            uploaded_file._file = tempfile.BytesIO(file_data)
            
            # Обновляем статус
            await processing_message.edit_text(
                "📸 Фото получено\n🔍 Распознаю текст с помощью OCR..."
            )
            
            # Обрабатываем изображение
            ocr_result = self.ocr_service.process_receipt_image(
                user=user,
                image_file=uploaded_file,
                recognition_type='receipt'
            )
            
            # Обновляем статус
            await processing_message.edit_text(
                f"✅ OCR завершен\n📝 Найдено товаров: {ocr_result.items_count}\n"
                f"🏪 Магазин: {ocr_result.shop_name or 'Не определен'}\n"
                f"💰 Сумма: {ocr_result.total_amount} сум\n"
                "🔄 Создаю транзакции..."
            )
            
            return ocr_result
            
        except Exception as e:
            logger.error(f"Ошибка OCR обработки: {e}")
            return None
    
    async def _create_transactions_from_receipt(self, ocr_result: OCRResult, user: User,
                                              processing_message) -> list:
        """
        Создает транзакции на основе данных чека
        
        Args:
            ocr_result: Результат OCR
            user: Пользователь
            processing_message: Сообщение о процессе
            
        Returns:
            list: Список созданных транзакций
        """
        created_transactions = []
        
        try:
            # Создаем основную транзакцию расхода по общей сумме чека
            if ocr_result.total_amount > 0:
                # Определяем или создаем категорию "Покупки"
                category, created = Category.objects.get_or_create(
                    user=user,
                    name='Покупки',
                    defaults={
                        'description': 'Покупки в магазинах (из чеков)',
                        'category_type': 'expense'
                    }
                )
                
                # Создаем транзакцию расхода
                transaction = self.transaction_service.create_expense(
                    user=user,
                    amount=ocr_result.total_amount,
                    description=f"Покупки в {ocr_result.shop_name or 'магазине'} (чек #{ocr_result.receipt_number})",
                    category=category,
                    date=ocr_result.receipt_date,
                    check_balance=False  # Не проверяем баланс для чеков
                )
                
                created_transactions.append(transaction)
                
                logger.info(f"Создана транзакция расхода {transaction.id} из чека {ocr_result.id}")
            
            return created_transactions
            
        except Exception as e:
            logger.error(f"Ошибка создания транзакций из чека: {e}")
            return []
    
    async def _send_receipt_result(self, update: Update, ocr_result: OCRResult,
                                 transactions_created: list, processing_message) -> None:
        """
        Отправляет результат обработки чека пользователю
        
        Args:
            update: Telegram Update объект
            ocr_result: Результат OCR
            transactions_created: Созданные транзакции
            processing_message: Сообщение о процессе обработки
        """
        try:
            if transactions_created:
                # Успешная обработка
                message = f"✅ **Чек успешно обработан!**\n\n"
                message += f"🏪 **Магазин:** {ocr_result.shop_name or 'Не определен'}\n"
                
                if ocr_result.receipt_date:
                    message += f"📅 **Дата:** {ocr_result.receipt_date.strftime('%d.%m.%Y %H:%M')}\n"
                
                if ocr_result.receipt_number:
                    message += f"🧾 **Номер чека:** {ocr_result.receipt_number}\n"
                
                message += f"💰 **Общая сумма:** {ocr_result.total_amount:,.0f} сум\n"
                message += f"📦 **Товаров найдено:** {ocr_result.items_count}\n\n"
                
                message += f"💸 **Создано транзакций:** {len(transactions_created)}\n"
                
                # Добавляем список товаров если их немного
                if ocr_result.items_count <= 5:
                    message += "\n📝 **Товары:**\n"
                    for item in ocr_result.items.all()[:5]:
                        message += f"• {item.name} — {item.total_price:,.0f} сум\n"
                elif ocr_result.items_count > 5:
                    message += f"\n📝 **Товары (показано 5 из {ocr_result.items_count}):**\n"
                    for item in ocr_result.items.all()[:5]:
                        message += f"• {item.name} — {item.total_price:,.0f} сум\n"
                    message += f"... и еще {ocr_result.items_count - 5} товаров\n"
                
                # Показываем текущий баланс
                try:
                    current_balance = self.transaction_service._get_user_balance(ocr_result.user)
                    message += f"\n💳 **Текущий баланс:** {current_balance:,.0f} сум"
                except:
                    pass
                
                await processing_message.edit_text(message, parse_mode='Markdown')
                
            else:
                # Ошибка создания транзакций
                message = f"⚠️ **Чек распознан, но транзакции не созданы**\n\n"
                message += f"🏪 **Магазин:** {ocr_result.shop_name or 'Не определен'}\n"
                message += f"💰 **Сумма:** {ocr_result.total_amount} сум\n"
                message += f"📦 **Товаров:** {ocr_result.items_count}\n\n"
                message += "❌ Проверьте настройки или попробуйте еще раз"
                
                await processing_message.edit_text(message, parse_mode='Markdown')
                
        except Exception as e:
            logger.error(f"Ошибка отправки результата чека: {e}")
            try:
                await processing_message.edit_text("❌ Ошибка отправки результата")
            except Exception:
                pass
    
    async def _try_auto_match_with_voice(self, update: Update, ocr_result: OCRResult, user: User) -> None:
        """
        Пытается автоматически сопоставить чек с недавними голосовыми сообщениями
        
        Args:
            update: Telegram Update объект
            ocr_result: Результат OCR обработки
            user: Пользователь
        """
        try:
            # Ищем недавние голосовые сообщения (в течение 5 минут)
            recent_voice_results = VoiceResult.objects.filter(
                user=user,
                status='completed',
                created_at__gte=ocr_result.created_at - timedelta(minutes=5)
            ).order_by('-created_at')[:3]
            
            if not recent_voice_results.exists():
                return
            
            best_match = None
            best_confidence = 0.0
            
            # Проверяем каждое голосовое сообщение на совпадение
            for voice_result in recent_voice_results:
                try:
                    match = self.receipt_matcher.match_voice_with_receipt(
                        voice_result, ocr_result
                    )
                    
                    if match and match.confidence_score > best_confidence and match.confidence_score > 0.6:
                        best_confidence = match.confidence_score
                        best_match = match
                        
                except Exception as e:
                    logger.error(f"Ошибка сопоставления с голосом {voice_result.id}: {e}")
                    continue
            
            # Если найдено хорошее сопоставление, уведомляем пользователя
            if best_match and best_match.confidence_score > 0.7:
                await self._send_auto_match_notification(update, best_match)
                
        except Exception as e:
            logger.error(f"Ошибка автоматического сопоставления: {e}")
    
    async def _send_auto_match_notification(self, update: Update, match: ReceiptVoiceMatch) -> None:
        """
        Отправляет уведомление об автоматическом сопоставлении
        
        Args:
            update: Telegram Update объект
            match: Результат сопоставления
        """
        try:
            # Сокращаем текст голосового сообщения для отображения
            voice_text = match.voice_result.recognized_text
            if len(voice_text) > 100:
                voice_text = voice_text[:100] + "..."
            
            message = "🎯 **Автоматическое сопоставление найдено!**\n\n"
            message += f"🎤 **Голосовое сообщение:**\n_{voice_text}_\n\n"
            message += f"🧾 **Чек:** {match.ocr_result.shop_name or 'Неизвестный магазин'}\n"
            message += f"💰 **Сумма чека:** {match.total_amount_receipt:,.0f} сум\n"
            message += f"🎯 **Точность сопоставления:** {match.confidence_score * 100:.0f}%\n"
            
            if match.matched_items_count > 0:
                message += f"🛍️ **Совпадающих товаров:** {match.matched_items_count}\n"
            
            if match.amount_match_percentage > 80:
                message += f"💯 **Суммы совпадают:** {match.amount_match_percentage:.0f}%\n"
            
            message += f"\n⏰ **Разница во времени:** {match.time_difference_minutes} мин"
            
            await update.message.reply_text(
                message,
                parse_mode='Markdown'
            )
            
        except Exception as e:
            logger.error(f"Ошибка отправки уведомления о сопоставлении: {e}")

    def _get_command_suggestions(self, language: str = 'ru') -> list:
        """Возвращает предложения команд"""
        if language == 'ru':
            return [
                "Попробуйте сфотографировать чек еще раз",
                "Убедитесь что освещение хорошее",
                "Отправьте голосовое сообщение с описанием покупки"
            ]
        elif language == 'uz':
            return [
                "Chekni yana suratga oling",
                "Yoritish yaxshi ekanligini tekshiring", 
                "Ovozli xabar jo'nating"
            ]
        else:
            return [
                "Try taking the receipt photo again",
                "Make sure lighting is good",
                "Send a voice message with purchase description"
            ]


# Создаем глобальный экземпляр обработчика
photo_handler = PhotoMessageHandler() 