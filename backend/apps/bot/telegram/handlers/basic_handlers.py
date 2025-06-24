import logging
from typing import Dict, Any
from asgiref.sync import sync_to_async
from django.conf import settings
from django.core.exceptions import ValidationError
from apps.users.models import User
from apps.transactions.models import Transaction
from ..services.telegram_api_service import TelegramAPIService

logger = logging.getLogger(__name__)


class BasicCommandHandlers:
    """
    Базовые обработчики команд бота
    """
    
    def __init__(self):
        self.telegram_api = TelegramAPIService()
    
    async def handle_start_command(self, update: Dict[str, Any]) -> None:
        """
        Обработчик команды /start
        Регистрирует пользователя или приветствует существующего
        """
        try:
            message = update.get('message', {})
            chat = message.get('chat', {})
            chat_id = chat.get('id')
            from_user = message.get('from', {})
            
            if not chat_id:
                logger.error("Не найден chat_id в сообщении /start")
                return
            
            # Создаем или получаем пользователя асинхронно
            user = await self._get_or_create_user(
                telegram_chat_id=chat_id,
                first_name=from_user.get('first_name', ''),
                last_name=from_user.get('last_name', ''),
                username=from_user.get('username', '')
            )
            
            if user:
                # Определяем имя пользователя для приветствия
                display_name = from_user.get('first_name', 'Пользователь')
                
                # Проверяем, есть ли у пользователя номер телефона
                if user.phone_number and not user.phone_number.startswith('tg_'):
                    # У пользователя уже есть номер телефона
                    welcome_text = (
                        f"👋 С возвращением, {display_name}!\n\n"
                        f"💰 Ваш финансовый помощник OvozPay готов к работе.\n\n"
                        f"📋 Доступные команды:\n"
                        f"🔹 /balance - проверить баланс\n"
                        f"🔹 /help - справка по командам\n"
                        f"🔹 /phone +номер - обновить номер телефона\n\n"
                        f"🎙 Отправьте голосовое сообщение для записи транзакции!"
                    )
                    
                    await self.telegram_api.send_message(
                        chat_id=chat_id,
                        text=welcome_text
                    )
                else:
                    # Новый пользователь - запрашиваем номер телефона
                    welcome_text = (
                        f"👋 Привет, {display_name}!\n\n"
                        f"Добро пожаловать в OvozPay - ваш персональный финансовый помощник! 💰\n\n"
                        f"📱 Для начала работы поделитесь своим номером телефона.\n"
                        f"Нажмите кнопку ниже ⬇️"
                    )
                    
                    # Создаем клавиатуру с кнопкой запроса контакта
                    keyboard = {
                        "keyboard": [
                            [
                                {
                                    "text": "📱 Отправить номер телефона",
                                    "request_contact": True
                                }
                            ]
                        ],
                        "resize_keyboard": True,
                        "one_time_keyboard": True
                    }
                    
                    await self.telegram_api.send_message(
                        chat_id=chat_id,
                        text=welcome_text,
                        reply_markup=keyboard
                    )
                
                logger.info(f"Пользователь {chat_id} успешно зарегистрирован/авторизован")
            else:
                error_text = (
                    "❌ Произошла ошибка при регистрации.\n"
                    "Попробуйте еще раз через несколько секунд."
                )
                
                await self.telegram_api.send_message(
                    chat_id=chat_id,
                    text=error_text
                )
                
        except Exception as e:
            logger.error(f"Ошибка в обработчике /start: {e}")
    
    async def handle_balance_command(self, update: Dict[str, Any]) -> None:
        """
        Обработчик команды /balance
        Показывает текущий баланс пользователя
        """
        try:
            message = update.get('message', {})
            chat_id = message.get('chat', {}).get('id')
            
            if not chat_id:
                logger.error("Не найден chat_id в сообщении /balance")
                return
            
            # Получаем пользователя асинхронно
            user = await self._get_user_by_chat_id(chat_id)
            
            if not user:
                await self.telegram_api.send_message(
                    chat_id=chat_id,
                    text=(
                        "❌ Пользователь не найден.\n"
                        "Выполните /start для регистрации."
                    )
                )
                return
            
            # Получаем транзакции пользователя асинхронно
            transactions = await self._get_user_transactions(user)
            
            # Вычисляем баланс
            total_income = sum(t.amount for t in transactions if t.transaction_type == 'income')
            total_expense = sum(t.amount for t in transactions if t.transaction_type == 'expense')
            balance = total_income - total_expense
            
            # Форматируем сообщение с балансом
            balance_text = (
                f"💰 Ваш текущий баланс\n\n"
                f"📈 Доходы: {total_income:,} сум\n"
                f"📉 Расходы: {total_expense:,} сум\n"
                f"💵 Баланс: {balance:,} сум\n\n"
                f"📊 Всего транзакций: {len(transactions)}"
            )
            
            await self.telegram_api.send_message(
                chat_id=chat_id,
                text=balance_text
            )
            
            logger.info(f"Отправлен баланс пользователю {chat_id}: {balance}")
            
        except Exception as e:
            logger.error(f"Ошибка в обработчике /balance: {e}")
    
    async def handle_help_command(self, update: Dict[str, Any]) -> None:
        """
        Обработчик команды /help
        Показывает справку по доступным командам
        """
        try:
            message = update.get('message', {})
            chat_id = message.get('chat', {}).get('id')
            
            if not chat_id:
                logger.error("Не найден chat_id в сообщении /help")
                return
            
            help_text = (
                "📋 Справка по командам OvozPay\n\n"
                "🔹 /start - начать работу с ботом\n"
                "🔹 /balance - проверить текущий баланс\n"
                "🔹 /help - показать эту справку\n"
                "🔹 /phone +номер - обновить номер телефона\n\n"
                "🎙 **Голосовые сообщения:**\n"
                "Отправьте голосовое сообщение для записи транзакции.\n\n"
                "📝 **Примеры фраз:**\n"
                "• \"Потратил 25000 сум на продукты\"\n"
                "• \"Заработал 150000 сум за проект\"\n"
                "• \"Купил кофе за 12000 сум\"\n\n"
                "💡 **Советы:**\n"
                "• Говорите четко и медленно\n"
                "• Указывайте сумму и описание\n"
                "• Используйте слова \"потратил\" или \"заработал\"\n\n"
                "🆘 Если возникли проблемы, обратитесь к администратору."
            )
            
            await self.telegram_api.send_message(
                chat_id=chat_id,
                text=help_text
            )
            
            logger.info(f"Отправлена справка пользователю {chat_id}")
            
        except Exception as e:
            logger.error(f"Ошибка в обработчике /help: {e}")
    
    async def handle_phone_command(self, update: Dict[str, Any]) -> None:
        """
        Обработчик команды /phone
        Обновляет номер телефона пользователя
        """
        try:
            message = update.get('message', {})
            chat_id = message.get('chat', {}).get('id')
            text = message.get('text', '').strip()
            
            if not chat_id:
                logger.error("Не найден chat_id в сообщении /phone")
                return
            
            # Извлекаем номер телефона из команды
            command_parts = text.split()
            if len(command_parts) < 2:
                await self.telegram_api.send_message(
                    chat_id=chat_id,
                    text=(
                        "📱 Укажите номер телефона после команды.\n\n"
                        "Пример: /phone +998901234567"
                    )
                )
                return
            
            phone_number = command_parts[1]
            
            # Простая валидация номера телефона
            if not phone_number.startswith('+') or len(phone_number) < 10:
                await self.telegram_api.send_message(
                    chat_id=chat_id,
                    text=(
                        "❌ Неверный формат номера телефона.\n\n"
                        "Используйте международный формат: +998901234567"
                    )
                )
                return
            
            # Получаем пользователя и обновляем номер асинхронно
            user = await self._get_user_by_chat_id(chat_id)
            
            if not user:
                await self.telegram_api.send_message(
                    chat_id=chat_id,
                    text=(
                        "❌ Пользователь не найден.\n"
                        "Выполните /start для регистрации."
                    )
                )
                return
            
            # Обновляем номер телефона
            success = await self._update_user_phone(user, phone_number)
            
            if success:
                await self.telegram_api.send_message(
                    chat_id=chat_id,
                    text=f"✅ Номер телефона успешно обновлен: {phone_number}"
                )
                logger.info(f"Обновлен номер телефона для пользователя {chat_id}: {phone_number}")
            else:
                await self.telegram_api.send_message(
                    chat_id=chat_id,
                    text="❌ Ошибка при обновлении номера телефона. Попробуйте позже."
                )
                
        except Exception as e:
            logger.error(f"Ошибка в обработчике /phone: {e}")
    
    @sync_to_async
    def _get_or_create_user(self, telegram_chat_id: int, first_name: str, 
                          last_name: str, username: str):
        """
        Создает или получает пользователя по telegram_chat_id
        """
        try:
            user, created = User.get_or_create_by_telegram(
                telegram_chat_id=telegram_chat_id,
                first_name=first_name,
                last_name=last_name,
                username=username
            )
            
            return user
        except Exception as e:
            logger.error(f"Ошибка создания/получения пользователя: {e}")
            return None
    
    @sync_to_async
    def _get_user_by_chat_id(self, chat_id: int):
        """
        Получает пользователя по telegram_chat_id
        """
        try:
            return User.objects.filter(telegram_chat_id=chat_id).first()
        except Exception as e:
            logger.error(f"Ошибка получения пользователя по chat_id {chat_id}: {e}")
            return None
    
    @sync_to_async
    def _get_user_transactions(self, user):
        """
        Получает все транзакции пользователя
        """
        try:
            return list(Transaction.objects.filter(user=user).order_by('-created_at'))
        except Exception as e:
            logger.error(f"Ошибка получения транзакций пользователя {user.id}: {e}")
            return []
    
    @sync_to_async
    def _update_user_phone(self, user, phone_number: str) -> bool:
        """
        Обновляет номер телефона пользователя
        """
        try:
            user.phone_number = phone_number
            user.save()
            return True
        except Exception as e:
            logger.error(f"Ошибка обновления номера телефона: {e}")
            return False 