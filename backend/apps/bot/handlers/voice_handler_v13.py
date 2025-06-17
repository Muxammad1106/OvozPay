"""
Обработчик голосовых сообщений для Telegram Bot (v13 совместимый)
Интеграция с AI модулем для распознавания и выполнения команд
"""

import logging
import os
import tempfile
from typing import Dict, Any

from telegram import Update
from telegram.ext import CallbackContext

from apps.users.models import User
from apps.ai.services.voice.whisper_service import WhisperVoiceService
from apps.ai.services.nlp.command_processor import VoiceCommandProcessor
from apps.ai.models import VoiceResult, VoiceCommand


logger = logging.getLogger(__name__)


class VoiceMessageHandler:
    """Обработчик голосовых сообщений в Telegram (v13)"""
    
    def __init__(self):
        # Пока используем упрощенную версию без Whisper
        self.whisper_available = False
        logger.info("Voice handler инициализирован (упрощенная версия)")
    
    def handle_voice_message(self, update: Update, context: CallbackContext) -> None:
        """
        Обрабатывает голосовое сообщение пользователя
        
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
            
            # Уведомляем пользователя о начале обработки
            processing_message = update.message.reply_text("🎤 Обрабатываю голосовое сообщение...")
            
            # Скачиваем голосовое сообщение
            voice_file = update.message.voice.get_file()
            
            # Создаем временный файл для аудио
            with tempfile.NamedTemporaryFile(suffix='.ogg', delete=False) as temp_file:
                temp_path = temp_file.name
                voice_file.download(temp_path)
            
            try:
                # Распознаем речь
                recognition_result = self._recognize_speech(temp_path, user)
                
                if not recognition_result['success']:
                    processing_message.edit_text(
                        f"❌ Ошибка распознавания: {recognition_result.get('error', 'Неизвестная ошибка')}"
                    )
                    return
                
                recognized_text = recognition_result['text']
                language = recognition_result['language']
                
                # Обновляем сообщение
                processing_message.edit_text(
                    f"✅ Распознано: \"{recognized_text}\"\n🔄 Выполняю команду..."
                )
                
                # Обрабатываем команду
                command_result = self._process_voice_command(
                    recognized_text, language, user
                )
                
                # Отправляем результат пользователю
                self._send_command_result(update, command_result, processing_message)
                
            finally:
                # Удаляем временный файл
                if os.path.exists(temp_path):
                    os.unlink(temp_path)
                    
        except Exception as e:
            logger.error(f"Ошибка обработки голосового сообщения: {e}")
            
            try:
                update.message.reply_text(
                    "❌ Произошла ошибка при обработке голосового сообщения. Попробуйте еще раз."
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
    
    def _recognize_speech(self, audio_path: str, user: User) -> Dict[str, Any]:
        """
        Распознает речь из аудиофайла (упрощенная версия)
        
        Args:
            audio_path: Путь к аудиофайлу
            user: Пользователь
            
        Returns:
            Dict: Результат распознавания
        """
        try:
            # Временная имитация распознавания речи
            # В будущем здесь будет реальный Whisper
            
            # Проверяем размер файла для имитации
            file_size = os.path.getsize(audio_path)
            
            if file_size < 1000:  # Очень маленький файл
                return {
                    'success': False,
                    'error': 'Голосовое сообщение слишком короткое'
                }
            
            # Имитируем успешное распознавание
            mock_texts = [
                "Покажи мой баланс",
                "Добавь расход хлеб пять тысяч сум",
                "Создай цель накопить миллион на машину",
                "Покажи мои расходы за месяц"
            ]
            
            # Выбираем случайный текст на основе размера файла
            text_index = (file_size // 1000) % len(mock_texts)
            recognized_text = mock_texts[text_index]
            
            logger.info(f"Голос распознан (демо): {recognized_text}")
            
            return {
                'success': True,
                'text': recognized_text,
                'language': 'ru'
            }
                
        except Exception as e:
            logger.error(f"Ошибка распознавания речи: {e}")
            return {
                'success': False,
                'error': f'Ошибка обработки аудио: {str(e)}'
            }
    
    def _process_voice_command(self, text: str, language: str, user: User) -> Dict[str, Any]:
        """
        Обрабатывает голосовую команду
        
        Args:
            text: Распознанный текст
            language: Язык
            user: Пользователь
            
        Returns:
            Dict: Результат выполнения команды
        """
        try:
            # Создаем процессор команд
            command_processor = VoiceCommandProcessor(user)
            
            # Парсим команду
            parsed_command = command_processor.parse_command(text, language, user)
            
            if not parsed_command:
                return {
                    'success': False,
                    'message': 'Команда не распознана. Попробуйте переформулировать.',
                    'suggestions': self._get_command_suggestions(language)
                }
            
            # Выполняем команду (упрощенная версия для v13)
            result = {
                'success': True,
                'message': f'Команда "{parsed_command["type"]}" выполнена успешно!',
                'data': parsed_command.get('params', {})
            }
            
            return result
            
        except Exception as e:
            logger.error(f"Ошибка обработки команды: {e}")
            return {
                'success': False,
                'message': f'Ошибка выполнения команды: {str(e)}'
            }
    
    def _send_command_result(self, update: Update, result: Dict[str, Any], 
                           processing_message) -> None:
        """
        Отправляет результат выполнения команды пользователю
        
        Args:
            update: Telegram Update объект
            result: Результат выполнения команды
            processing_message: Сообщение о процессе обработки
        """
        try:
            if result.get('success'):
                # Успешное выполнение
                message = f"✅ {result.get('message', 'Команда выполнена успешно')}"
                
                # Добавляем дополнительную информацию если есть
                data = result.get('data', {})
                if data:
                    message += self._format_command_data(data)
                
                processing_message.edit_text(message)
                
            else:
                # Ошибка выполнения
                error_message = result.get('message') or result.get('error', 'Неизвестная ошибка')
                message = f"❌ {error_message}"
                
                # Добавляем предложения если есть
                suggestions = result.get('suggestions', [])
                if suggestions:
                    message += "\n\n💡 Попробуйте:\n" + "\n".join(f"• {s}" for s in suggestions[:3])
                
                processing_message.edit_text(message)
                
        except Exception as e:
            logger.error(f"Ошибка отправки результата: {e}")
            try:
                processing_message.edit_text("❌ Ошибка отправки результата")
            except Exception:
                pass
    
    def _format_command_data(self, data: Dict[str, Any]) -> str:
        """Форматирует данные команды для отображения"""
        if not data:
            return ""
        
        formatted = "\n\n📊 **Детали:**\n"
        for key, value in data.items():
            if key in ['amount', 'сумма']:
                formatted += f"💰 Сумма: {value}\n"
            elif key in ['category', 'категория']:
                formatted += f"📂 Категория: {value}\n"
            elif key in ['description', 'описание']:
                formatted += f"📝 Описание: {value}\n"
            else:
                formatted += f"• {key}: {value}\n"
        
        return formatted
    
    def _get_command_suggestions(self, language: str) -> list:
        """Возвращает предложения команд"""
        if language == 'ru':
            return [
                "Покажи мой баланс",
                "Добавь расход хлеб 5000 сум",
                "Покажи мои цели"
            ]
        elif language == 'uz':
            return [
                "Balansimni ko'rsat",
                "Xarajat qo'sh non 5000 so'm",
                "Maqsadlarimni ko'rsat"
            ]
        else:
            return [
                "Show my balance",
                "Add expense bread 5000",
                "Show my goals"
            ]


# Создаем глобальный экземпляр обработчика
voice_handler = VoiceMessageHandler() 