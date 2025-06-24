"""
Сервис для работы с пользователями бота
"""

import logging
from typing import Dict, Any, Optional
from asgiref.sync import sync_to_async

from ..models import TelegramUser, BotSession

logger = logging.getLogger(__name__)


class UserService:
    """Сервис для управления пользователями"""
    
    async def get_or_create_user(self, chat_id: int, user_data: Dict[str, Any]) -> TelegramUser:
        """Получить или создать пользователя"""
        try:
            @sync_to_async
            def get_or_create():
                user, created = TelegramUser.objects.get_or_create(
                    telegram_chat_id=chat_id,
                    defaults={
                        'telegram_user_id': user_data.get('id', 0),
                        'username': user_data.get('username', ''),
                        'first_name': user_data.get('first_name', ''),
                        'last_name': user_data.get('last_name', ''),
                        'language': 'ru',  # По умолчанию русский
                        'preferred_currency': 'UZS',  # По умолчанию узбекский сум
                        'is_active': True
                    }
                )
                
                if created:
                    logger.info(f"Created new user {chat_id}")
                
                return user
            
            return await get_or_create()
            
        except Exception as e:
            logger.error(f"Error getting or creating user {chat_id}: {e}")
            raise
    
    async def get_user_by_chat_id(self, chat_id: int) -> Optional[TelegramUser]:
        """Получить пользователя по chat_id"""
        try:
            @sync_to_async
            def get_user():
                try:
                    return TelegramUser.objects.get(telegram_chat_id=chat_id)
                except TelegramUser.DoesNotExist:
                    return None
            
            return await get_user()
            
        except Exception as e:
            logger.error(f"Error getting user {chat_id}: {e}")
            return None
    
    async def update_user_language(self, chat_id: int, language: str) -> bool:
        """Обновляет язык пользователя"""
        try:
            @sync_to_async
            def update_language():
                user = TelegramUser.objects.get(telegram_chat_id=chat_id)
                user.language = language
                user.save()
                return True
            
            return await update_language()
            
        except TelegramUser.DoesNotExist:
            logger.error(f"User not found for chat_id {chat_id}")
            return False
        except Exception as e:
            logger.error(f"Error updating user language: {e}")
            return False
    
    async def update_user_currency(self, chat_id: int, currency: str) -> bool:
        """Обновляет валюту пользователя"""
        try:
            @sync_to_async
            def update_currency():
                user = TelegramUser.objects.get(telegram_chat_id=chat_id)
                user.preferred_currency = currency
                user.save()
                return True
            
            return await update_currency()
            
        except TelegramUser.DoesNotExist:
            logger.error(f"User not found for chat_id {chat_id}")
            return False
        except Exception as e:
            logger.error(f"Error updating user currency: {e}")
            return False
    
    async def update_user_phone(self, chat_id: int, phone: str) -> bool:
        """Обновляет номер телефона пользователя"""
        try:
            @sync_to_async
            def update_phone():
                user = TelegramUser.objects.get(telegram_chat_id=chat_id)
                user.phone_number = phone
                user.save()
                return True
            
            return await update_phone()
            
        except TelegramUser.DoesNotExist:
            logger.error(f"User not found for chat_id {chat_id}")
            return False
        except Exception as e:
            logger.error(f"Error updating user phone: {e}")
            return False
    
    async def set_user_state(self, chat_id: int, state: Optional[str]) -> bool:
        """Устанавливает состояние пользователя"""
        try:
            @sync_to_async
            def set_state():
                session, created = BotSession.objects.get_or_create(
                    user__telegram_chat_id=chat_id,
                    defaults={'state': state}
                )
                if not created:
                    session.state = state
                    session.save()
                return True
            
            return await set_state()
            
        except Exception as e:
            logger.error(f"Error setting user state: {e}")
            return False
    
    async def get_user_session(self, chat_id: int) -> Optional[BotSession]:
        """Получает сессию пользователя"""
        try:
            @sync_to_async
            def get_session():
                try:
                    return BotSession.objects.get(user__telegram_chat_id=chat_id)
                except BotSession.DoesNotExist:
                    return None
            
            return await get_session()
            
        except Exception as e:
            logger.error(f"Error getting user session: {e}")
            return None
    
    async def update_user_activity(self, chat_id: int) -> bool:
        """Обновляет время последней активности пользователя"""
        try:
            @sync_to_async
            def update_activity():
                user = TelegramUser.objects.get(telegram_chat_id=chat_id)
                user.save()  # updated_at обновится автоматически
                return True
            
            return await update_activity()
            
        except TelegramUser.DoesNotExist:
            logger.error(f"User not found for chat_id {chat_id}")
            return False
        except Exception as e:
            logger.error(f"Error updating user activity: {e}")
            return False
    
    def get_user_by_chat_id_sync(self, chat_id: int) -> Optional[TelegramUser]:
        """Синхронный метод получения пользователя по chat_id"""
        try:
            return TelegramUser.objects.get(telegram_chat_id=chat_id)
        except TelegramUser.DoesNotExist:
            return None
        except Exception as e:
            logger.error(f"Error getting user sync {chat_id}: {e}")
            return None 