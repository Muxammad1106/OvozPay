"""
Сервис для работы с целями и накоплениями OvozPay
Этап 6: Goals & Savings API
"""

import logging
from decimal import Decimal
from datetime import datetime, timedelta
from django.utils import timezone
from django.db import transaction
from django.core.exceptions import ValidationError
from django.db.models import Sum, Count, Q, Avg
from apps.goals.models import Goal, GoalTransaction
from apps.users.models import User
from apps.analytics.models import Balance
from apps.transactions.services import TransactionService
from apps.bot.telegram.services.telegram_api_service import TelegramAPIService

logger = logging.getLogger(__name__)


def send_telegram_message(user, message):
    """Обертка для отправки Telegram сообщений"""
    try:
        if hasattr(user, 'telegram_chat_id') and user.telegram_chat_id:
            telegram_service = TelegramAPIService()
            return telegram_service.send_message(user.telegram_chat_id, message)
        else:
            logger.warning(f"Пользователь {user.phone_number} не имеет telegram_chat_id")
            return None
    except Exception as e:
        logger.error(f"Ошибка отправки Telegram сообщения: {str(e)}")
        return None


class GoalService:
    """Сервис для управления целями и накоплениями"""
    
    @staticmethod
    def create_goal(user, title, target_amount, deadline, description="", reminder_interval="weekly"):
        """
        Создает новую цель для пользователя
        
        Args:
            user: Пользователь
            title: Название цели
            target_amount: Целевая сумма
            deadline: Дата достижения
            description: Описание цели
            reminder_interval: Интервал напоминаний
            
        Returns:
            Goal: Созданная цель
        """
        try:
            with transaction.atomic():
                goal = Goal.objects.create(
                    user=user,
                    title=title,
                    target_amount=Decimal(str(target_amount)),
                    deadline=deadline,
                    description=description,
                    reminder_interval=reminder_interval
                )
                
                # Отправляем Telegram уведомление
                GoalService._send_goal_created_notification(goal)
                
                logger.info(f"Создана новая цель: {goal.title} для пользователя {user.phone_number}")
                return goal
                
        except Exception as e:
            logger.error(f"Ошибка создания цели: {str(e)}")
            raise
    
    @staticmethod
    def add_progress_to_goal(goal, amount, description="", withdraw_from_balance=True):
        """
        Добавляет прогресс к цели
        
        Args:
            goal: Цель
            amount: Сумма пополнения
            description: Описание операции
            withdraw_from_balance: Списывать ли с баланса пользователя
            
        Returns:
            GoalTransaction: Транзакция пополнения
        """
        try:
            with transaction.atomic():
                # Проверяем баланс пользователя, если нужно списать
                if withdraw_from_balance:
                    user_balance = GoalService._get_user_balance(goal.user)
                    if user_balance < Decimal(str(amount)):
                        raise ValidationError(
                            f"Недостаточно средств на балансе. "
                            f"Доступно: {user_balance}, требуется: {amount}"
                        )
                
                # Добавляем прогресс к цели (создает GoalTransaction автоматически)
                goal_transaction = goal.add_progress(amount, description)
                
                # Списываем с баланса, если требуется
                if withdraw_from_balance:
                    # Создаем expense транзакцию через TransactionService
                    TransactionService.create_expense(
                        user=goal.user,
                        amount=amount,
                        category=None,  # Можно создать категорию "Накопления"
                        source=None,
                        description=f"Пополнение цели: {goal.title}"
                    )
                
                # Отправляем уведомления
                GoalService._send_goal_progress_notification(goal, goal_transaction)
                
                # Проверяем, завершена ли цель
                if goal.is_completed:
                    GoalService._send_goal_completed_notification(goal)
                
                logger.info(
                    f"Добавлен прогресс {amount} к цели {goal.title} "
                    f"пользователя {goal.user.phone_number}"
                )
                
                return goal_transaction
                
        except Exception as e:
            logger.error(f"Ошибка добавления прогресса к цели: {str(e)}")
            raise
    
    @staticmethod
    def complete_goal(goal, force=False, reason=""):
        """
        Завершает цель
        
        Args:
            goal: Цель
            force: Принудительное завершение
            reason: Причина завершения
        """
        try:
            with transaction.atomic():
                old_status = goal.status
                goal.complete_goal(force=force)
                
                # Отправляем уведомление о завершении
                if old_status != 'completed':
                    GoalService._send_goal_completed_notification(goal, reason)
                
                logger.info(f"Цель {goal.title} завершена пользователем {goal.user.phone_number}")
                
        except Exception as e:
            logger.error(f"Ошибка завершения цели: {str(e)}")
            raise
    
    @staticmethod
    def fail_goal(goal, reason=""):
        """
        Отмечает цель как проваленную
        
        Args:
            goal: Цель
            reason: Причина провала
        """
        try:
            with transaction.atomic():
                old_status = goal.status
                goal.fail_goal(reason)
                
                # Отправляем уведомление о провале
                if old_status != 'failed':
                    GoalService._send_goal_failed_notification(goal, reason)
                
                logger.info(f"Цель {goal.title} провалена пользователем {goal.user.phone_number}")
                
        except Exception as e:
            logger.error(f"Ошибка провала цели: {str(e)}")
            raise
    
    @staticmethod
    def get_user_goals_stats(user):
        """
        Получает статистику целей пользователя
        
        Args:
            user: Пользователь
            
        Returns:
            dict: Статистика целей
        """
        try:
            goals = Goal.objects.filter(user=user)
            
            # Базовая статистика
            total_goals = goals.count()
            active_goals = goals.filter(status='active').count()
            completed_goals = goals.filter(status='completed').count()
            failed_goals = goals.filter(status='failed').count()
            paused_goals = goals.filter(status='paused').count()
            overdue_goals = goals.filter(
                status='active', 
                deadline__lt=timezone.now().date()
            ).count()
            
            # Финансовая статистика
            total_target = goals.aggregate(
                total=Sum('target_amount')
            )['total'] or Decimal('0.00')
            
            total_saved = goals.aggregate(
                total=Sum('current_amount')
            )['total'] or Decimal('0.00')
            
            # Средний прогресс
            avg_progress = goals.aggregate(
                avg=Avg('current_amount')
            )['avg'] or 0
            
            # Статистика за период
            now = timezone.now()
            this_month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            this_year_start = now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
            
            this_month_transactions = GoalTransaction.objects.filter(
                goal__user=user,
                created_at__gte=this_month_start
            )
            
            this_year_transactions = GoalTransaction.objects.filter(
                goal__user=user,
                created_at__gte=this_year_start
            )
            
            this_month_saved = this_month_transactions.aggregate(
                total=Sum('amount')
            )['total'] or Decimal('0.00')
            
            this_year_saved = this_year_transactions.aggregate(
                total=Sum('amount')
            )['total'] or Decimal('0.00')
            
            # Последние цели
            recent_goals = goals.order_by('-created_at')[:5]
            
            return {
                'total_goals': total_goals,
                'active_goals': active_goals,
                'completed_goals': completed_goals,
                'failed_goals': failed_goals,
                'paused_goals': paused_goals,
                'overdue_goals_count': overdue_goals,
                'total_target_amount': total_target,
                'total_saved_amount': total_saved,
                'average_progress_percentage': float(avg_progress) if avg_progress else 0.0,
                'this_month_saved': this_month_saved,
                'this_year_saved': this_year_saved,
                'recent_goals': recent_goals
            }
            
        except Exception as e:
            logger.error(f"Ошибка получения статистики целей: {str(e)}")
            raise
    
    @staticmethod
    def check_and_update_overdue_goals():
        """
        Проверяет и обновляет просроченные цели
        
        Returns:
            int: Количество обновленных целей
        """
        try:
            overdue_goals = Goal.objects.filter(
                status='active',
                deadline__lt=timezone.now().date()
            )
            
            updated_count = 0
            for goal in overdue_goals:
                goal.fail_goal("Истек срок достижения цели")
                GoalService._send_goal_failed_notification(
                    goal, 
                    "Цель автоматически провалена из-за истечения срока"
                )
                updated_count += 1
            
            if updated_count > 0:
                logger.info(f"Обновлено {updated_count} просроченных целей")
            
            return updated_count
            
        except Exception as e:
            logger.error(f"Ошибка обновления просроченных целей: {str(e)}")
            return 0
    
    @staticmethod
    def send_goal_reminders():
        """
        Отправляет напоминания по активным целям
        
        Returns:
            int: Количество отправленных напоминаний
        """
        try:
            now = timezone.now()
            sent_count = 0
            
            # Получаем цели, которым нужно отправить напоминания
            for interval in ['daily', 'weekly', 'monthly']:
                goals = GoalService._get_goals_for_reminder(interval, now)
                
                for goal in goals:
                    GoalService._send_goal_reminder_notification(goal)
                    goal.last_reminder_sent = now
                    goal.save(update_fields=['last_reminder_sent'])
                    sent_count += 1
            
            if sent_count > 0:
                logger.info(f"Отправлено {sent_count} напоминаний по целям")
            
            return sent_count
            
        except Exception as e:
            logger.error(f"Ошибка отправки напоминаний: {str(e)}")
            return 0
    
    # Приватные методы
    
    @staticmethod
    def _get_user_balance(user):
        """Получает баланс пользователя"""
        try:
            balance = Balance.objects.get(user=user)
            return balance.current_balance
        except Balance.DoesNotExist:
            return Decimal('0.00')
    
    @staticmethod
    def _get_goals_for_reminder(interval, now):
        """Получает цели для отправки напоминаний по интервалу"""
        if interval == 'daily':
            last_reminder_threshold = now - timedelta(days=1)
        elif interval == 'weekly':
            last_reminder_threshold = now - timedelta(weeks=1)
        elif interval == 'monthly':
            last_reminder_threshold = now - timedelta(days=30)
        else:
            return Goal.objects.none()
        
        return Goal.objects.filter(
            status='active',
            reminder_interval=interval,
            deadline__gt=now.date()
        ).filter(
            Q(last_reminder_sent__isnull=True) |
            Q(last_reminder_sent__lt=last_reminder_threshold)
        )
    
    # Методы для Telegram уведомлений
    
    @staticmethod
    def _send_goal_created_notification(goal):
        """Отправляет уведомление о создании цели"""
        try:
            message = GoalService._format_goal_created_message(goal)
            send_telegram_message(goal.user, message)
            
            goal.telegram_notified = True
            goal.save(update_fields=['telegram_notified'])
            
        except Exception as e:
            logger.error(f"Ошибка отправки уведомления о создании цели: {str(e)}")
    
    @staticmethod
    def _send_goal_progress_notification(goal, transaction):
        """Отправляет уведомление о пополнении цели"""
        try:
            message = GoalService._format_goal_progress_message(goal, transaction)
            send_telegram_message(goal.user, message)
            
            transaction.telegram_notified = True
            transaction.save(update_fields=['telegram_notified'])
            
        except Exception as e:
            logger.error(f"Ошибка отправки уведомления о пополнении цели: {str(e)}")
    
    @staticmethod
    def _send_goal_completed_notification(goal, reason=""):
        """Отправляет уведомление о завершении цели"""
        try:
            message = GoalService._format_goal_completed_message(goal, reason)
            send_telegram_message(goal.user, message)
            
        except Exception as e:
            logger.error(f"Ошибка отправки уведомления о завершении цели: {str(e)}")
    
    @staticmethod
    def _send_goal_failed_notification(goal, reason=""):
        """Отправляет уведомление о провале цели"""
        try:
            message = GoalService._format_goal_failed_message(goal, reason)
            send_telegram_message(goal.user, message)
            
        except Exception as e:
            logger.error(f"Ошибка отправки уведомления о провале цели: {str(e)}")
    
    @staticmethod
    def _send_goal_reminder_notification(goal):
        """Отправляет напоминание о цели"""
        try:
            message = GoalService._format_goal_reminder_message(goal)
            send_telegram_message(goal.user, message)
            
        except Exception as e:
            logger.error(f"Ошибка отправки напоминания о цели: {str(e)}")
    
    # Методы форматирования сообщений
    
    @staticmethod
    def _format_goal_created_message(goal):
        """Форматирует сообщение о создании цели"""
        return (
            f"🎯 <b>Новая цель создана!</b>\n\n"
            f"📝 <b>Название:</b> {goal.title}\n"
            f"💰 <b>Целевая сумма:</b> {goal.target_amount:,.0f} UZS\n"
            f"📅 <b>Срок:</b> {goal.deadline.strftime('%d.%m.%Y')}\n"
            f"📊 <b>Прогресс:</b> 0% (0 / {goal.target_amount:,.0f} UZS)\n"
            f"⏰ <b>Дней осталось:</b> {goal.days_left}\n\n"
            f"💪 Начинайте откладывать средства для достижения цели!"
        )
    
    @staticmethod
    def _format_goal_progress_message(goal, transaction):
        """Форматирует сообщение о пополнении цели"""
        return (
            f"💵 <b>Цель пополнена!</b>\n\n"
            f"🎯 <b>Цель:</b> {goal.title}\n"
            f"➕ <b>Пополнено:</b> {transaction.amount:,.0f} UZS\n"
            f"💰 <b>Накоплено:</b> {goal.current_amount:,.0f} UZS\n"
            f"🎯 <b>Цель:</b> {goal.target_amount:,.0f} UZS\n"
            f"📊 <b>Прогресс:</b> {goal.progress_percentage:.1f}%\n"
            f"📈 <b>Осталось:</b> {goal.remaining_amount:,.0f} UZS\n"
            f"📅 <b>До срока:</b> {goal.days_left} дней\n\n"
            f"{'🎉 Поздравляем! Цель достигнута!' if goal.is_completed else '💪 Продолжайте в том же духе!'}"
        )
    
    @staticmethod
    def _format_goal_completed_message(goal, reason=""):
        """Форматирует сообщение о завершении цели"""
        message = (
            f"🎉 <b>Цель достигнута!</b>\n\n"
            f"🎯 <b>Цель:</b> {goal.title}\n"
            f"💰 <b>Сумма:</b> {goal.target_amount:,.0f} UZS\n"
            f"📅 <b>Завершено:</b> {timezone.now().strftime('%d.%m.%Y %H:%M')}\n"
            f"⏱ <b>Потребовалось дней:</b> {(timezone.now().date() - goal.created_at.date()).days}\n\n"
            f"🏆 Поздравляем с достижением цели! Вы большой молодец!"
        )
        
        if reason:
            message += f"\n\n📝 <b>Примечание:</b> {reason}"
        
        return message
    
    @staticmethod
    def _format_goal_failed_message(goal, reason=""):
        """Форматирует сообщение о провале цели"""
        message = (
            f"😔 <b>Цель не достигнута</b>\n\n"
            f"🎯 <b>Цель:</b> {goal.title}\n"
            f"💰 <b>Целевая сумма:</b> {goal.target_amount:,.0f} UZS\n"
            f"💵 <b>Накоплено:</b> {goal.current_amount:,.0f} UZS\n"
            f"📊 <b>Прогресс:</b> {goal.progress_percentage:.1f}%\n"
            f"📅 <b>Срок истек:</b> {goal.deadline.strftime('%d.%m.%Y')}\n\n"
            f"💪 Не расстраивайтесь! Создайте новую цель и попробуйте снова!"
        )
        
        if reason:
            message += f"\n\n📝 <b>Причина:</b> {reason}"
        
        return message
    
    @staticmethod
    def _format_goal_reminder_message(goal):
        """Форматирует напоминание о цели"""
        return (
            f"⏰ <b>Напоминание о цели</b>\n\n"
            f"🎯 <b>Цель:</b> {goal.title}\n"
            f"💰 <b>Накоплено:</b> {goal.current_amount:,.0f} UZS\n"
            f"🎯 <b>Цель:</b> {goal.target_amount:,.0f} UZS\n"
            f"📊 <b>Прогресс:</b> {goal.progress_percentage:.1f}%\n"
            f"📈 <b>Осталось:</b> {goal.remaining_amount:,.0f} UZS\n"
            f"📅 <b>До срока:</b> {goal.days_left} дней\n\n"
            f"💡 Не забывайте откладывать средства для достижения цели!"
        ) 