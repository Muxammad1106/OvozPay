"""
Сервис для работы с транзакциями через Telegram бота
"""

import logging
from decimal import Decimal
from typing import Dict, Any, Optional, Tuple
from django.utils import timezone
from asgiref.sync import sync_to_async

from apps.transactions.models import Transaction
from apps.categories.models import Category
from apps.users.models import User
from .user_service import UserService

logger = logging.getLogger(__name__)


class TransactionService:
    """Сервис для создания транзакций из голосовых команд"""
    
    def __init__(self):
        self.user_service = UserService()
    
    @sync_to_async
    def create_transaction_from_voice(
        self,
        user_telegram_id: int,
        parsed_data: Dict[str, Any]
    ) -> Optional[Transaction]:
        """
        Создает транзакцию из распознанного голосового сообщения
        
        Args:
            user_telegram_id: Telegram ID пользователя
            parsed_data: Данные, извлеченные из голосового сообщения
                        {
                            'type': 'expense'|'income',
                            'amount': Decimal,
                            'category': str,
                            'description': str,
                            'confidence': float
                        }
        
        Returns:
            Transaction: Созданная транзакция или None при ошибке
        """
        try:
            # Получаем пользователя Telegram
            telegram_user = self.user_service.get_user_by_chat_id_sync(user_telegram_id)
            if not telegram_user:
                logger.error(f"TelegramUser не найден для chat_id: {user_telegram_id}")
                return None
            
            # Получаем связанного User
            user = self._get_or_create_user(telegram_user)
            if not user:
                logger.error(f"Не удалось получить User для {user_telegram_id}")
                return None
            
            # Получаем категорию
            category = self._get_or_create_category(
                user=user,
                category_name=parsed_data.get('category', 'другое'),
                transaction_type=parsed_data['type']
            )
            
            # Создаем транзакцию
            transaction = Transaction.objects.create(
                user=user,
                type=parsed_data['type'],
                amount=parsed_data['amount'],
                category=category,
                description=parsed_data.get('description', ''),
                date=timezone.now()
            )
            
            logger.info(f"Создана транзакция {transaction.id} для пользователя {user_telegram_id}")
            return transaction
            
        except Exception as e:
            logger.error(f"Ошибка создания транзакции: {e}")
            return None
    
    @sync_to_async
    def create_transaction_from_text(
        self,
        user_telegram_id: int,
        parsed_data: Dict[str, Any]
    ) -> Optional[Transaction]:
        """
        Создает транзакцию из распознанного текстового сообщения
        
        Args:
            user_telegram_id: Telegram ID пользователя
            parsed_data: Данные, извлеченные из текстового сообщения
                        {
                            'type': 'expense'|'income',
                            'amount': Decimal,
                            'currency': str,
                            'category': str,
                            'description': str,
                            'source': 'text'
                        }
        
        Returns:
            Transaction: Созданная транзакция или None при ошибке
        """
        try:
            # Получаем пользователя Telegram
            telegram_user = self.user_service.get_user_by_chat_id_sync(user_telegram_id)
            if not telegram_user:
                logger.error(f"TelegramUser не найден для chat_id: {user_telegram_id}")
                return None
            
            # Получаем связанного User
            user = self._get_or_create_user(telegram_user)
            if not user:
                logger.error(f"Не удалось получить User для {user_telegram_id}")
                return None
            
            # Конвертируем валюту в валюту пользователя, если нужно
            amount = self._convert_currency(
                amount=parsed_data['amount'],
                from_currency=parsed_data.get('currency', 'UZS'),
                to_currency=telegram_user.preferred_currency
            )
            
            # Получаем или создаем категорию
            category = self._get_or_create_category(
                user=user,
                category_name=parsed_data.get('category', 'прочее'),
                transaction_type=parsed_data['type']
            )
            
            # Создаем транзакцию
            transaction = Transaction.objects.create(
                user=user,
                type=parsed_data['type'],
                amount=amount,
                category=category,
                description=parsed_data.get('description', ''),
                date=timezone.now()
            )
            
            logger.info(f"Создана транзакция из текста {transaction.id} для пользователя {user_telegram_id}")
            return transaction
            
        except Exception as e:
            logger.error(f"Ошибка создания транзакции из текста: {e}")
            return None

    def _convert_currency(self, amount: Decimal, from_currency: str, to_currency: str) -> Decimal:
        """
        Конвертирует сумму из одной валюты в другую
        
        TODO: Интеграция с API курсов валют ЦБ Узбекистана
        Пока используем примерные курсы
        """
        if from_currency == to_currency:
            return amount
        
        # Примерные курсы (в сумах за 1 единицу валюты)
        exchange_rates = {
            'USD': Decimal('12000'),
            'EUR': Decimal('13000'), 
            'RUB': Decimal('130'),
            'UZS': Decimal('1')
        }
        
        try:
            # Конвертируем в сумы, затем в целевую валюту
            amount_in_uzs = amount * exchange_rates.get(from_currency, Decimal('1'))
            result = amount_in_uzs / exchange_rates.get(to_currency, Decimal('1'))
            
            logger.info(f"Конвертировано {amount} {from_currency} в {result} {to_currency}")
            return result
            
        except Exception as e:
            logger.error(f"Ошибка конвертации валюты: {e}")
            return amount
    
    def _get_or_create_user(self, telegram_user) -> Optional[User]:
        """Получает или создает User на основе TelegramUser"""
        try:
            # Ищем User по номеру телефона
            if telegram_user.phone_number:
                user, created = User.objects.get_or_create(
                    phone_number=telegram_user.phone_number,
                    defaults={
                        'first_name': telegram_user.first_name,
                        'last_name': telegram_user.last_name,
                        'username': telegram_user.username,
                    }
                )
            else:
                # Если нет номера телефона, ищем по username
                user, created = User.objects.get_or_create(
                    username=telegram_user.username or f"tg_{telegram_user.telegram_user_id}",
                    defaults={
                        'first_name': telegram_user.first_name,
                        'last_name': telegram_user.last_name,
                        'phone_number': telegram_user.phone_number or '',
                    }
                )
            
            if created:
                logger.info(f"Создан новый User: {user.id}")
                # Создаем категории по умолчанию
                Category.create_default_categories_for_user(user)
            
            return user
            
        except Exception as e:
            logger.error(f"Ошибка создания/получения User: {e}")
            return None
    
    def _get_or_create_category(
        self,
        user: User,
        category_name: str,
        transaction_type: str
    ) -> Optional[Category]:
        """Получает или создает категорию"""
        try:
            # Ищем существующую категорию (нечувствительно к регистру)
            category = Category.objects.filter(
                user=user,
                name__iexact=category_name,
                type=transaction_type
            ).first()
            
            if category:
                return category
            
            # Создаем новую категорию
            category = Category.objects.create(
                user=user,
                name=category_name.title(),
                type=transaction_type,
                is_default=False
            )
            
            logger.info(f"Создана новая категория: {category.name}")
            return category
            
        except Exception as e:
            logger.error(f"Ошибка создания/получения категории: {e}")
            
            # Возвращаем дефолтную категорию
            default_category = Category.objects.filter(
                user=user,
                type=transaction_type,
                is_default=True
            ).first()
            
            return default_category
    
    @sync_to_async
    def get_user_balance(self, user_telegram_id: int) -> Tuple[Decimal, Dict[str, Any]]:
        """
        Получает баланс пользователя и статистику
        
        Returns:
            Tuple[Decimal, Dict]: (balance, stats)
        """
        try:
            telegram_user = self.user_service.get_user_by_chat_id_sync(user_telegram_id)
            if not telegram_user:
                return Decimal('0'), {}
            
            user = self._get_or_create_user(telegram_user)
            if not user:
                return Decimal('0'), {}
            
            # Считаем баланс
            transactions = Transaction.objects.filter(user=user)
            
            total_income = sum(
                t.amount for t in transactions.filter(type='income')
            )
            total_expense = sum(
                t.amount for t in transactions.filter(type='expense')
            )
            
            balance = total_income - total_expense
            
            stats = {
                'total_income': total_income,
                'total_expense': total_expense,
                'balance': balance,
                'transactions_count': transactions.count()
            }
            
            return balance, stats
            
        except Exception as e:
            logger.error(f"Ошибка получения баланса: {e}")
            return Decimal('0'), {} 