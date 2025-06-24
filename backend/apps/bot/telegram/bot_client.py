import logging
import asyncio
from typing import Dict, Any
from asgiref.sync import sync_to_async
from .handlers.basic_handlers import BasicCommandHandlers
from .services.telegram_api_service import TelegramAPIService

logger = logging.getLogger(__name__)


class TelegramBotClient:
    """
    Основной клиент для обработки обновлений от Telegram
    """
    
    def __init__(self):
        self.telegram_api = TelegramAPIService()
        self.basic_handlers = BasicCommandHandlers()
        
        # Маппинг команд к обработчикам
        self.command_handlers = {
            '/start': self.basic_handlers.handle_start_command,
            '/balance': self.basic_handlers.handle_balance_command,
            '/help': self.basic_handlers.handle_help_command,
            '/phone': self.basic_handlers.handle_phone_command,
        }
    
    def handle_update(self, update: Dict[str, Any]) -> None:
        """
        Основной метод обработки обновлений
        """
        try:
            logger.info(f"Обрабатываем обновление: {update}")
            
            # Проверяем тип обновления
            if 'message' in update:
                self._handle_message(update)
            elif 'callback_query' in update:
                self._handle_callback_query(update)
            else:
                logger.warning(f"Неизвестный тип обновления: {update}")
                
        except Exception as e:
            logger.error(f"Ошибка обработки обновления: {e}")
    
    def _handle_message(self, update: Dict[str, Any]) -> None:
        """
        Обрабатывает текстовые и голосовые сообщения
        """
        try:
            message = update.get('message', {})
            
            # Проверяем наличие контакта (номера телефона)
            if 'contact' in message:
                self._handle_contact_message(update)
            
            # Проверяем наличие текста (команды)
            elif 'text' in message:
                self._handle_text_message(update)
            
            # Проверяем наличие голосового сообщения
            elif 'voice' in message:
                self._handle_voice_message(update)
            
            # Проверяем наличие аудио
            elif 'audio' in message:
                self._handle_audio_message(update)
            
            else:
                # Неподдерживаемый тип сообщения
                chat_id = message.get('chat', {}).get('id')
                if chat_id:
                    self.telegram_api.send_message_sync(
                        chat_id=chat_id,
                        text="❌ Поддерживаются только текстовые и голосовые сообщения."
                    )
                    
        except Exception as e:
            logger.error(f"Ошибка обработки сообщения: {e}")
    
    def _handle_text_message(self, update: Dict[str, Any]) -> None:
        """
        Обрабатывает текстовые сообщения и команды
        """
        try:
            message = update.get('message', {})
            text = message.get('text', '').strip()
            chat_id = message.get('chat', {}).get('id')
            
            # Проверяем, является ли сообщение командой
            if text.startswith('/'):
                command = text.split()[0].lower()
                
                if command in self.command_handlers:
                    # Запускаем обработчик команды в отдельном потоке через threading
                    import threading
                    thread = threading.Thread(
                        target=self._run_command_sync, 
                        args=(command, update)
                    )
                    thread.start()
                else:
                    # Неизвестная команда
                    if chat_id:
                        self.telegram_api.send_message_sync(
                            chat_id=chat_id,
                            text=(
                                f"❌ Неизвестная команда: {command}\n"
                                f"Используйте /help для списка доступных команд."
                            )
                        )
            else:
                # Обычное текстовое сообщение
                self._handle_regular_text(update)
                
        except Exception as e:
            logger.error(f"Ошибка обработки текстового сообщения: {e}")
    
    def _run_command_sync(self, command: str, update: Dict[str, Any]) -> None:
        """
        Запускает обработчик команды синхронно в отдельном потоке
        """
        try:
            asyncio.run(self.command_handlers[command](update))
        except Exception as e:
            logger.error(f"Ошибка в синхронном обработчике команды {command}: {e}")
    
    def _handle_regular_text(self, update: Dict[str, Any]) -> None:
        """
        Обрабатывает обычные текстовые сообщения (не команды)
        """
        try:
            message = update.get('message', {})
            text = message.get('text', '').strip()
            chat_id = message.get('chat', {}).get('id')
            
            if not chat_id:
                return
            
            # Отправляем информационное сообщение
            response_text = (
                f"📝 Получено текстовое сообщение: \"{text[:50]}\"\n\n"
                f"💡 Для записи транзакций рекомендуется использовать голосовые сообщения.\n"
                f"🎙 Просто запишите голосовое сообщение с описанием дохода или расхода.\n\n"
                f"Пример: \"Потратил 25000 сум на продукты в магазине\""
            )
            
            self.telegram_api.send_message_sync(
                chat_id=chat_id,
                text=response_text
            )
            
        except Exception as e:
            logger.error(f"Ошибка обработки обычного текста: {e}")
    
    def _handle_voice_message(self, update: Dict[str, Any]) -> None:
        """
        Обрабатывает голосовые сообщения
        """
        try:
            message = update.get('message', {})
            voice = message.get('voice', {})
            chat_id = message.get('chat', {}).get('id')
            
            if not chat_id:
                return
            
            # Временная заглушка для голосовых сообщений
            response_text = (
                f"🎙 Получено голосовое сообщение!\n\n"
                f"⏱ Длительность: {voice.get('duration', 0)} сек.\n"
                f"📁 Размер: {voice.get('file_size', 0)} байт\n\n"
                f"🔄 Функция распознавания речи будет добавлена в следующих обновлениях.\n"
                f"📝 Пока используйте текстовые команды для управления финансами."
            )
            
            self.telegram_api.send_message_sync(
                chat_id=chat_id,
                text=response_text
            )
            
            logger.info(f"Обработано голосовое сообщение от {chat_id}")
            
        except Exception as e:
            logger.error(f"Ошибка обработки голосового сообщения: {e}")
    
    def _handle_audio_message(self, update: Dict[str, Any]) -> None:
        """
        Обрабатывает аудио сообщения
        """
        try:
            message = update.get('message', {})
            audio = message.get('audio', {})
            chat_id = message.get('chat', {}).get('id')
            
            if not chat_id:
                return
            
            response_text = (
                f"🎵 Получен аудио файл!\n\n"
                f"🎤 Для записи транзакций используйте голосовые сообщения (не аудио файлы).\n"
                f"📱 Просто нажмите и удерживайте кнопку записи в Telegram."
            )
            
            self.telegram_api.send_message_sync(
                chat_id=chat_id,
                text=response_text
            )
            
        except Exception as e:
            logger.error(f"Ошибка обработки аудио сообщения: {e}")
    
    def _handle_callback_query(self, update: Dict[str, Any]) -> None:
        """
        Обрабатывает callback запросы от inline клавиатур
        """
        try:
            callback_query = update.get('callback_query', {})
            data = callback_query.get('data', '')
            chat_id = callback_query.get('message', {}).get('chat', {}).get('id')
            
            if not chat_id:
                return
            
            # Временная заглушка для callback'ов
            response_text = f"🔄 Получен callback: {data}"
            
            self.telegram_api.send_message_sync(
                chat_id=chat_id,
                text=response_text
            )
            
        except Exception as e:
            logger.error(f"Ошибка обработки callback query: {e}")
    
    def _handle_contact_message(self, update: Dict[str, Any]) -> None:
        """
        Обрабатывает контакт (номер телефона)
        """
        message = update.get('message', {})
        contact = message.get('contact', {})
        chat_id = message.get('chat', {}).get('id')
        from_user = message.get('from', {})
        
        if not chat_id:
            return
        
        # Выполняем в отдельном потоке для избежания блокировки
        import threading
        thread = threading.Thread(
            target=self._process_contact_message,
            args=(contact, chat_id, from_user)
        )
        thread.start()
    
    def _process_contact_message(self, contact: Dict, chat_id: int, from_user: Dict) -> None:
        """
        Обрабатывает полученный контакт
        """
        try:
            phone_number = contact.get('phone_number', '')
            first_name = contact.get('first_name', from_user.get('first_name', ''))
            
            if not phone_number:
                self.telegram_api.send_message_sync(
                    chat_id=chat_id,
                    text="❌ Не удалось получить номер телефона. Попробуйте еще раз."
                )
                return
            
            # Обрабатываем номер телефона (добавляем + если нет)
            if not phone_number.startswith('+'):
                phone_number = '+' + phone_number
            
            # Обновляем пользователя с номером телефона
            from apps.users.models import User
            
            user, created = User.objects.get_or_create(
                telegram_chat_id=chat_id,
                defaults={
                    'phone_number': phone_number,
                    'first_name': first_name,
                    'last_name': from_user.get('last_name', ''),
                    'username': from_user.get('username', ''),
                }
            )
            
            if not created and user.phone_number != phone_number:
                # Обновляем номер телефона если изменился
                user.phone_number = phone_number
                user.save()
            
            # Отправляем подтверждение
            self.telegram_api.send_message_sync(
                chat_id=chat_id,
                text=(
                    f"✅ Отлично, {first_name}!\n\n"
                    f"📱 Ваш номер телефона {phone_number} сохранен.\n\n"
                    f"🎉 Теперь вы можете пользоваться всеми функциями OvozPay:\n\n"
                    f"📋 Команды:\n"
                    f"🔹 /balance - проверить баланс\n"
                    f"🔹 /help - справка по командам\n"
                    f"🔹 /phone +номер - обновить номер телефона\n\n"
                    f"🎙 Отправьте голосовое сообщение для записи транзакции!\n"
                    f"Пример: \"Потратил 50000 сум на продукты\""
                ),
                reply_markup={
                    "remove_keyboard": True
                }
            )
            
            logger.info(f"Сохранен номер телефона {phone_number} для пользователя {chat_id}")
            
        except Exception as e:
            logger.error(f"Ошибка при обработке контакта: {e}")
            self.telegram_api.send_message_sync(
                chat_id=chat_id,
                text="❌ Произошла ошибка при сохранении номера телефона. Попробуйте еще раз или свяжитесь с поддержкой."
            ) 