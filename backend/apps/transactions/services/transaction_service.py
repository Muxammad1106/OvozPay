from decimal import Decimal
from typing import Optional, Dict, Any
from django.db import transaction, models
from django.utils import timezone
from django.core.exceptions import ValidationError
from apps.transactions.models import Transaction, DebtTransaction
from apps.analytics.models import Balance
from apps.bot.models import BotSession
from apps.bot.telegram.services.telegram_api_service import TelegramAPIService
import logging

logger = logging.getLogger(__name__)


class TransactionService:
    """Сервис для работы с финансовыми транзакциями"""
    
    def __init__(self):
        self.telegram_service = TelegramAPIService()
    
    @transaction.atomic
    def create_income(
        self, 
        user, 
        amount: Decimal, 
        description: str = '', 
        category=None,
        source=None,
        date=None
    ) -> Transaction:
        """Создает доходную транзакцию"""
        
        if amount <= 0:
            raise ValidationError('Сумма дохода должна быть положительной')
        
        income_transaction = Transaction.objects.create(
            user=user,
            amount=amount,
            type='income',
            description=description,
            category=category,
            source=source,
            date=date or timezone.now()
        )
        
        # Обновляем баланс
        self._update_user_balance(user)
        
        # Отправляем уведомление в Telegram
        self._send_telegram_notification(
            user, 
            'income', 
            amount, 
            description,
            income_transaction
        )
        
        logger.info(f"Created income transaction {income_transaction.id} for user {user.id}")
        return income_transaction
    
    @transaction.atomic
    def create_expense(
        self, 
        user, 
        amount: Decimal, 
        description: str = '', 
        category=None,
        source=None,
        date=None,
        check_balance: bool = True
    ) -> Transaction:
        """Создает расходную транзакцию с проверкой баланса"""
        
        if amount <= 0:
            raise ValidationError('Сумма расхода должна быть положительной')
        
        # Проверяем баланс перед списанием
        if check_balance:
            current_balance = self._get_user_balance(user)
            if current_balance < amount:
                raise ValidationError(
                    f'Недостаточно средств. Баланс: {current_balance}, требуется: {amount}'
                )
        
        expense_transaction = Transaction.objects.create(
            user=user,
            amount=amount,
            type='expense',
            description=description,
            category=category,
            source=source,
            date=date or timezone.now()
        )
        
        # Обновляем баланс
        self._update_user_balance(user)
        
        # Отправляем уведомление в Telegram
        self._send_telegram_notification(
            user, 
            'expense', 
            amount, 
            description,
            expense_transaction
        )
        
        logger.info(f"Created expense transaction {expense_transaction.id} for user {user.id}")
        return expense_transaction
    
    @transaction.atomic
    def create_transfer(
        self,
        sender_user,
        receiver_user,
        amount: Decimal,
        description: str = '',
        category=None,
        check_balance: bool = True
    ) -> tuple[Transaction, Transaction]:
        """Создает перевод между пользователями"""
        
        if amount <= 0:
            raise ValidationError('Сумма перевода должна быть положительной')
        
        if sender_user == receiver_user:
            raise ValidationError('Нельзя переводить самому себе')
        
        # Проверяем баланс отправителя
        if check_balance:
            sender_balance = self._get_user_balance(sender_user)
            if sender_balance < amount:
                raise ValidationError(
                    f'Недостаточно средств для перевода. Баланс: {sender_balance}'
                )
        
        # Создаем транзакцию списания у отправителя
        sender_transaction = Transaction.objects.create(
            user=sender_user,
            amount=amount,
            type='transfer',
            description=f'Перевод для {receiver_user.phone_number}: {description}',
            category=category,
            related_user=receiver_user,
            date=timezone.now()
        )
        
        # Создаем транзакцию зачисления у получателя
        receiver_transaction = Transaction.objects.create(
            user=receiver_user,
            amount=amount,
            type='income',
            description=f'Перевод от {sender_user.phone_number}: {description}',
            category=category,
            related_user=sender_user,
            date=timezone.now()
        )
        
        # Обновляем балансы
        self._update_user_balance(sender_user)
        self._update_user_balance(receiver_user)
        
        # Отправляем уведомления
        self._send_telegram_notification(
            sender_user, 
            'transfer_sent', 
            amount, 
            f'Перевод для {receiver_user.phone_number}',
            sender_transaction
        )
        
        self._send_telegram_notification(
            receiver_user, 
            'transfer_received', 
            amount, 
            f'Перевод от {sender_user.phone_number}',
            receiver_transaction
        )
        
        logger.info(f"Created transfer from {sender_user.id} to {receiver_user.id}, amount: {amount}")
        return sender_transaction, receiver_transaction
    
    @transaction.atomic
    def create_debt(
        self,
        user,
        amount: Decimal,
        debtor_name: str,
        debt_direction: str,
        description: str = '',
        due_date: Optional[timezone.datetime] = None,
        category=None
    ) -> DebtTransaction:
        """Создает долговую транзакцию"""
        
        if amount <= 0:
            raise ValidationError('Сумма долга должна быть положительной')
        
        if not debtor_name or not debtor_name.strip():
            raise ValidationError('Имя должника обязательно')
        
        if debt_direction not in ['from_me', 'to_me']:
            raise ValidationError('Некорректное направление долга')
        
        debt_transaction = DebtTransaction.objects.create(
            user=user,
            amount=amount,
            debtor_name=debtor_name.strip(),
            debt_direction=debt_direction,
            description=description,
            due_date=due_date,
            category=category,
            date=timezone.now()
        )
        
        # Отправляем уведомление в Telegram
        self._send_telegram_notification(
            user, 
            'debt_created', 
            amount, 
            f'Долг: {debtor_name}',
            debt_transaction
        )
        
        logger.info(f"Created debt transaction {debt_transaction.id} for user {user.id}")
        return debt_transaction
    
    @transaction.atomic
    def close_debt(self, debt_transaction: DebtTransaction, description: str = '') -> bool:
        """Закрывает долг полностью"""
        
        if debt_transaction.status == 'closed':
            raise ValidationError('Долг уже закрыт')
        
        debt_transaction.close_debt()
        
        # Отправляем уведомление в Telegram
        self._send_telegram_notification(
            debt_transaction.user,
            'debt_closed',
            debt_transaction.amount,
            f'Долг закрыт: {debt_transaction.debtor_name}',
            debt_transaction
        )
        
        logger.info(f"Closed debt transaction {debt_transaction.id}")
        return True
    
    @transaction.atomic
    def add_debt_payment(
        self, 
        debt_transaction: DebtTransaction, 
        payment_amount: Decimal,
        description: str = ''
    ) -> bool:
        """Добавляет частичный платеж по долгу"""
        
        if debt_transaction.status == 'closed':
            raise ValidationError('Долг уже закрыт')
        
        old_status = debt_transaction.status
        is_fully_paid = debt_transaction.add_payment(payment_amount)
        
        # Отправляем уведомление
        if is_fully_paid:
            notification_type = 'debt_closed'
            message = f'Долг полностью погашен: {debt_transaction.debtor_name}'
        else:
            notification_type = 'debt_payment'
            message = f'Частичная оплата долга: {debt_transaction.debtor_name}'
        
        self._send_telegram_notification(
            debt_transaction.user,
            notification_type,
            payment_amount,
            message,
            debt_transaction
        )
        
        logger.info(f"Added payment {payment_amount} to debt {debt_transaction.id}")
        return is_fully_paid
    
    def get_user_stats(self, user) -> Dict[str, Any]:
        """Возвращает статистику транзакций пользователя"""
        
        transactions = Transaction.objects.filter(user=user)
        debts = DebtTransaction.objects.filter(user=user)
        
        total_income = transactions.filter(type='income').aggregate(
            total=models.Sum('amount')
        )['total'] or Decimal('0')
        
        total_expense = transactions.filter(type='expense').aggregate(
            total=models.Sum('amount')
        )['total'] or Decimal('0')
        
        total_debts = debts.aggregate(
            total=models.Sum('amount')
        )['total'] or Decimal('0')
        
        open_debts_count = debts.filter(status__in=['open', 'partial', 'overdue']).count()
        
        current_balance = self._get_user_balance(user)
        transactions_count = transactions.count()
        
        return {
            'total_income': total_income,
            'total_expense': total_expense,
            'total_debts': total_debts,
            'open_debts_count': open_debts_count,
            'current_balance': current_balance,
            'transactions_count': transactions_count
        }
    
    def _get_user_balance(self, user) -> Decimal:
        """Получает текущий баланс пользователя"""
        try:
            balance = Balance.objects.get(user=user)
            balance.update_balance()
            return balance.amount
        except Balance.DoesNotExist:
            balance = Balance.objects.create(user=user)
            balance.update_balance()
            return balance.amount
    
    def _update_user_balance(self, user):
        """Обновляет баланс пользователя"""
        try:
            balance = Balance.objects.get(user=user)
            balance.update_balance()
        except Balance.DoesNotExist:
            Balance.objects.create(user=user)
    
    def _send_telegram_notification(
        self, 
        user, 
        notification_type: str, 
        amount: Decimal, 
        description: str,
        transaction_obj: Transaction
    ):
        """Отправляет уведомление в Telegram"""
        
        try:
            # Получаем Telegram chat_id пользователя
            bot_session = BotSession.objects.filter(
                user=user,
                is_active=True
            ).first()
            
            if not bot_session:
                logger.info(f"No active Telegram session for user {user.id}")
                return
            
            # Формируем сообщение
            message = self._format_notification_message(
                notification_type, 
                amount, 
                description,
                transaction_obj
            )
            
            # Отправляем уведомление
            result = self.telegram_service.send_message(
                chat_id=bot_session.telegram_chat_id,
                text=message
            )
            
            if result:
                transaction_obj.telegram_notified = True
                transaction_obj.save(update_fields=['telegram_notified'])
                logger.info(f"Telegram notification sent for transaction {transaction_obj.id}")
            else:
                logger.error(f"Failed to send Telegram notification for transaction {transaction_obj.id}")
                
        except Exception as e:
            logger.error(f"Error sending Telegram notification: {str(e)}")
    
    def _format_notification_message(
        self, 
        notification_type: str, 
        amount: Decimal, 
        description: str,
        transaction_obj: Transaction
    ) -> str:
        """Форматирует сообщение для Telegram уведомления"""
        
        emoji_map = {
            'income': '💰',
            'expense': '💸',
            'transfer_sent': '📤',
            'transfer_received': '📥',
            'debt_created': '📋',
            'debt_closed': '✅',
            'debt_payment': '💵'
        }
        
        emoji = emoji_map.get(notification_type, '💼')
        
        if notification_type == 'income':
            message = f"{emoji} <b>Доход получен</b>\n\n"
            message += f"💵 Сумма: <b>{amount:,.0f} UZS</b>\n"
            
        elif notification_type == 'expense':
            message = f"{emoji} <b>Расход создан</b>\n\n"
            message += f"💸 Сумма: <b>{amount:,.0f} UZS</b>\n"
            
        elif notification_type == 'transfer_sent':
            message = f"{emoji} <b>Перевод отправлен</b>\n\n"
            message += f"💸 Сумма: <b>{amount:,.0f} UZS</b>\n"
            
        elif notification_type == 'transfer_received':
            message = f"{emoji} <b>Перевод получен</b>\n\n"
            message += f"💰 Сумма: <b>{amount:,.0f} UZS</b>\n"
            
        elif notification_type == 'debt_created':
            message = f"{emoji} <b>Долг создан</b>\n\n"
            message += f"💰 Сумма: <b>{amount:,.0f} UZS</b>\n"
            
        elif notification_type == 'debt_closed':
            message = f"{emoji} <b>Долг закрыт</b>\n\n"
            message += f"💰 Сумма: <b>{amount:,.0f} UZS</b>\n"
            
        elif notification_type == 'debt_payment':
            message = f"{emoji} <b>Платеж по долгу</b>\n\n"
            message += f"💰 Сумма: <b>{amount:,.0f} UZS</b>\n"
            
        else:
            message = f"{emoji} <b>Финансовая операция</b>\n\n"
            message += f"💰 Сумма: <b>{amount:,.0f} UZS</b>\n"
        
        if description:
            message += f"📝 Описание: {description}\n"
        
        message += f"📅 Дата: {transaction_obj.date.strftime('%d.%m.%Y %H:%M')}\n"
        
        # Добавляем текущий баланс для доходов и расходов
        if notification_type in ['income', 'expense']:
            try:
                current_balance = self._get_user_balance(transaction_obj.user)
                message += f"💳 Баланс: <b>{current_balance:,.0f} UZS</b>"
            except:
                pass
        
        return message 