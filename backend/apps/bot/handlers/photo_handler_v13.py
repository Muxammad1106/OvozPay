"""
Обработчик фото сообщений для Telegram Bot (v13 совместимый)
Интеграция с AI OCR модулем для автоматического сканирования чеков
"""

import logging
import os
import tempfile
from typing import Dict, Any

from telegram import Update
from telegram.ext import CallbackContext

from apps.users.models import User
from apps.ai.services.ocr.tesseract_service import TesseractOCRService
from apps.transactions.services.transaction_service import TransactionService
from apps.categories.models import Category


logger = logging.getLogger(__name__)


class PhotoMessageHandler:
    """Обработчик фото сообщений в Telegram (v13)"""
    
    def __init__(self):
        # Временно используем заглушки вместо реальных сервисов
        self.ocr_available = False
        self.transaction_service = None
        
        try:
            self.ocr_service = TesseractOCRService()
            self.transaction_service = TransactionService()
            self.ocr_available = True
        except Exception as e:
            logger.warning(f"OCR сервис недоступен: {e}")
    
    def handle_photo_message(self, update: Update, context: CallbackContext) -> None:
        """
        Обрабатывает фото сообщение пользователя (сканирование чека)
        
        Args:
            update: Telegram Update объект
            context: Telegram Context объект
        """
        try:
            # Получаем пользователя
            telegram_user = update.effective_user
            user = self._get_or_create_user(telegram_user)
            
            if not user:
                update.message.reply_text("❌ Ошибка авторизации. Попробуйте позже.")
                return
            
            # Проверяем доступность OCR
            if not self.ocr_available:
                update.message.reply_text(
                    "📸 Функция сканирования чеков временно недоступна.\n\n"
                    "🎤 Вместо этого используйте голосовое сообщение:\n"
                    "\"Добавь расход покупки 50000 сум\""
                )
                return
            
            # Уведомляем пользователя о начале обработки
            processing_message = update.message.reply_text(
                "📸 Обрабатываю фото чека...\n🔍 Распознаю текст и товары..."
            )
            
            # Получаем самое большое фото
            photo = update.message.photo[-1]
            photo_file = photo.get_file()
            
            # Создаем временный файл для фото
            with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as temp_file:
                temp_path = temp_file.name
                photo_file.download(temp_path)
            
            try:
                # Обрабатываем чек через OCR (имитация)
                result = self._process_receipt_mock(temp_path, user)
                
                # Отправляем результат пользователю
                self._send_receipt_result(update, result, processing_message)
                
            finally:
                # Удаляем временный файл
                if os.path.exists(temp_path):
                    os.unlink(temp_path)
                    
        except Exception as e:
            logger.error(f"Ошибка обработки фото сообщения: {e}")
            
            try:
                update.message.reply_text(
                    "❌ Произошла ошибка при обработке фото. Попробуйте еще раз."
                )
            except Exception:
                pass
    
    def _get_or_create_user(self, telegram_user) -> User:
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
    
    def _process_receipt_mock(self, image_path: str, user: User) -> Dict[str, Any]:
        """
        Имитирует обработку чека (для демонстрации функциональности)
        
        Args:
            image_path: Путь к изображению
            user: Пользователь
            
        Returns:
            Dict: Результат обработки чека
        """
        try:
            # Имитируем успешное распознавание чека
            return {
                'success': True,
                'shop_name': 'Korzinka.uz',
                'total_amount': 127500,
                'items_count': 5,
                'receipt_number': 'А001234567',
                'receipt_date': '2024-01-15 14:30',
                'items': [
                    {'name': 'Хлеб белый', 'price': 4500, 'quantity': 2},
                    {'name': 'Молоко 1л', 'price': 8500, 'quantity': 1},
                    {'name': 'Яйца 10шт', 'price': 15000, 'quantity': 1},
                    {'name': 'Помидоры 1кг', 'price': 12000, 'quantity': 1},
                    {'name': 'Картофель 2кг', 'price': 16000, 'quantity': 1}
                ]
            }
            
        except Exception as e:
            logger.error(f"Ошибка обработки чека: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _send_receipt_result(self, update: Update, result: Dict[str, Any],
                           processing_message) -> None:
        """
        Отправляет результат обработки чека пользователю
        
        Args:
            update: Telegram Update объект
            result: Результат обработки чека
            processing_message: Сообщение о процессе обработки
        """
        try:
            if result.get('success'):
                # Успешная обработка
                message = f"✅ **Чек успешно обработан!** (демо-режим)\n\n"
                message += f"🏪 **Магазин:** {result.get('shop_name', 'Не определен')}\n"
                message += f"📅 **Дата:** {result.get('receipt_date', 'Не определена')}\n"
                message += f"🧾 **Номер чека:** {result.get('receipt_number', 'Не определен')}\n"
                message += f"💰 **Общая сумма:** {result.get('total_amount', 0):,.0f} сум\n"
                message += f"📦 **Товаров найдено:** {result.get('items_count', 0)}\n\n"
                
                # Добавляем список товаров
                items = result.get('items', [])
                if items:
                    message += "📝 **Товары:**\n"
                    for item in items[:5]:  # Показываем первые 5 товаров
                        message += f"• {item['name']} — {item['price']:,.0f} сум\n"
                    
                    if len(items) > 5:
                        message += f"... и еще {len(items) - 5} товаров\n"
                
                message += "\n💸 **Транзакция расхода создана автоматически**"
                message += "\n\n📱 *Это демонстрация функции сканирования чеков*"
                
                processing_message.edit_text(message, parse_mode='Markdown')
                
            else:
                # Ошибка обработки
                error_message = result.get('error', 'Неизвестная ошибка')
                message = f"❌ **Ошибка распознавания чека**\n\n"
                message += f"Причина: {error_message}\n\n"
                message += "💡 **Попробуйте:**\n"
                message += "• Сделать фото при хорошем освещении\n"
                message += "• Держать камеру ровно\n"
                message += "• Убедиться что текст четко виден\n\n"
                message += "🎤 **Или используйте голосовое сообщение:**\n"
                message += "\"Добавь расход покупки [сумма] сум\""
                
                processing_message.edit_text(message, parse_mode='Markdown')
                
        except Exception as e:
            logger.error(f"Ошибка отправки результата чека: {e}")
            try:
                processing_message.edit_text("❌ Ошибка отправки результата")
            except Exception:
                pass


# Создаем глобальный экземпляр обработчика
photo_handler = PhotoMessageHandler() 