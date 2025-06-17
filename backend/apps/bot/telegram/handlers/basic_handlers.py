from typing import Dict, Any
from apps.users.models import User
from apps.analytics.models import Balance
from apps.bot.telegram.services.telegram_api_service import TelegramAPIService
from apps.bot.models import BotSession
import logging

logger = logging.getLogger(__name__)


class BasicHandlers:
    def __init__(self):
        self.telegram_service = TelegramAPIService()
    
    async def start_handler(self, update_data: Dict[str, Any]) -> None:
        message = update_data.get('message', {})
        chat_id = message.get('chat', {}).get('id')
        from_user = message.get('from', {})
        telegram_user_id = from_user.get('id')
        username = from_user.get('username', '')
        first_name = from_user.get('first_name', '')
        
        if not chat_id or not telegram_user_id:
            return
        
        try:
            session, created = BotSession.objects.get_or_create(
                telegram_chat_id=chat_id,
                defaults={
                    'is_active': True,
                    'session_type': 'text'
                }
            )
            
            if created:
                session.user = await self._get_or_create_user_by_telegram_id(telegram_user_id)
                session.save()
            
            session.add_message()
            
            welcome_text = f"""
🎉 <b>Добро пожаловать в OvozPay!</b>

Привет, {first_name}! 👋

Я ваш голосовой помощник для управления финансами. 
С моей помощью вы можете:

💰 Отслеживать доходы и расходы
🎯 Управлять целями накопления  
📊 Получать аналитику по тратам
💳 Контролировать долги

<b>Основные команды:</b>
/balance - показать баланс
/help - справка по командам

Для полного функционала зарегистрируйтесь через наше приложение!
"""
            
            await self.telegram_service.send_message_async(
                chat_id=chat_id,
                text=welcome_text
            )
            
        except Exception as e:
            logger.error(f"Error in start_handler: {str(e)}")
            await self.telegram_service.send_message_async(
                chat_id=chat_id,
                text="Произошла ошибка. Попробуйте позже."
            )
    
    async def balance_handler(self, update_data: Dict[str, Any]) -> None:
        message = update_data.get('message', {})
        chat_id = message.get('chat', {}).get('id')
        from_user = message.get('from', {})
        telegram_user_id = from_user.get('id')
        
        if not chat_id or not telegram_user_id:
            return
        
        try:
            user = await self._get_user_by_telegram_id(telegram_user_id)
            
            if not user:
                await self.telegram_service.send_message_async(
                    chat_id=chat_id,
                    text="❌ Пользователь не найден. Используйте команду /start для регистрации."
                )
                return
            
            balance = Balance.get_or_create_for_user(user)
            balance.update_balance()
            
            balance_text = f"""
💰 <b>Ваш баланс</b>

Текущий баланс: <b>{balance.amount} UZS</b>

📱 Для просмотра подробной статистики используйте наше приложение.
"""
            
            await self.telegram_service.send_message_async(
                chat_id=chat_id,
                text=balance_text
            )
            
            session = BotSession.objects.filter(
                telegram_chat_id=chat_id,
                is_active=True
            ).first()
            
            if session:
                session.add_message()
                session.add_command()
            
        except Exception as e:
            logger.error(f"Error in balance_handler: {str(e)}")
            await self.telegram_service.send_message_async(
                chat_id=chat_id,
                text="❌ Произошла ошибка при получении баланса."
            )
    
    async def help_handler(self, update_data: Dict[str, Any]) -> None:
        message = update_data.get('message', {})
        chat_id = message.get('chat', {}).get('id')
        
        if not chat_id:
            return
        
        help_text = """
🤖 <b>Справка по командам OvozPay</b>

<b>Основные команды:</b>
/start - начать работу с ботом
/balance - показать текущий баланс
/help - показать эту справку

<b>Голосовые команды:</b>
🎤 Отправьте голосовое сообщение для:
• Добавления трат: "Потратил 50000 на продукты"
• Добавления доходов: "Получил зарплату 2000000"
• Создания целей: "Хочу накопить на телефон 5000000"

<b>Дополнительные функции:</b>
📊 Детальная аналитика в приложении
🎯 Управление целями накопления
💳 Отслеживание долгов

Для полного доступа к функциям зарегистрируйтесь в приложении!
"""
        
        try:
            await self.telegram_service.send_message_async(
                chat_id=chat_id,
                text=help_text
            )
            
            session = BotSession.objects.filter(
                telegram_chat_id=chat_id,
                is_active=True
            ).first()
            
            if session:
                session.add_message()
                
        except Exception as e:
            logger.error(f"Error in help_handler: {str(e)}")
    
    async def _get_user_by_telegram_id(self, telegram_id: int) -> User:
        try:
            session = BotSession.objects.filter(
                telegram_chat_id=telegram_id,
                user__isnull=False
            ).first()
            
            return session.user if session else None
        except Exception:
            return None
    
    async def _get_or_create_user_by_telegram_id(self, telegram_id: int) -> User:
        user = await self._get_user_by_telegram_id(telegram_id)
        
        if not user:
            user = User.objects.create(
                phone_number=f"+{telegram_id}",
                language='ru'
            )
            
        return user


start_handler = BasicHandlers().start_handler
balance_handler = BasicHandlers().balance_handler
help_handler = BasicHandlers().help_handler 