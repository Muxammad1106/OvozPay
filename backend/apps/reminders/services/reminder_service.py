"""
Сервис для работы с напоминаниями и планировщиком OvozPay
Этап 7: Reminders & Scheduler API
"""

import logging
from decimal import Decimal
from datetime import datetime, timedelta
from django.utils import timezone
from django.db import transaction
from django.core.exceptions import ValidationError
from django.db.models import Count, Q
from apps.reminders.models import Reminder, ReminderHistory
from apps.users.models import User
from apps.goals.models import Goal
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


class ReminderService:
    """Сервис для управления напоминаниями"""
    
    @staticmethod
    def create_reminder(user, title, reminder_type, scheduled_time, description="", 
                       repeat="once", amount=None, goal=None):
        """
        Создает новое напоминание для пользователя
        
        Args:
            user: Пользователь
            title: Название события
            reminder_type: Тип напоминания (payment, debt, goal, custom)
            scheduled_time: Время срабатывания
            description: Описание (опционально)
            repeat: Периодичность (once, daily, weekly, monthly)
            amount: Сумма (для платежей/долгов)
            goal: Связанная цель (для напоминаний о целях)
            
        Returns:
            Reminder: Созданное напоминание
        """
        try:
            with transaction.atomic():
                reminder = Reminder.objects.create(
                    user=user,
                    title=title,
                    description=description,
                    reminder_type=reminder_type,
                    scheduled_time=scheduled_time,
                    repeat=repeat,
                    amount=Decimal(str(amount)) if amount else None,
                    goal=goal
                )
                
                # Отправляем уведомление о создании напоминания
                ReminderService._send_reminder_created_notification(reminder)
                
                logger.info(f"Создано новое напоминание: {reminder.title} для пользователя {user.phone_number}")
                return reminder
                
        except Exception as e:
            logger.error(f"Ошибка создания напоминания: {str(e)}")
            raise
    
    @staticmethod
    def send_reminder_notification(reminder, manual=False):
        """
        Отправляет уведомление по напоминанию
        
        Args:
            reminder: Напоминание
            manual: Отправлено ли вручную
            
        Returns:
            ReminderHistory: Запись истории
        """
        try:
            with transaction.atomic():
                # Формируем сообщение в зависимости от типа
                if reminder.reminder_type == 'payment':
                    message = ReminderService._format_payment_reminder_message(reminder)
                elif reminder.reminder_type == 'debt':
                    message = ReminderService._format_debt_reminder_message(reminder)
                elif reminder.reminder_type == 'goal':
                    message = ReminderService._format_goal_reminder_message(reminder)
                else:
                    message = ReminderService._format_custom_reminder_message(reminder)
                
                # Отправляем сообщение в Telegram
                telegram_response = send_telegram_message(reminder.user, message)
                
                # Создаем запись в истории
                history = ReminderHistory.objects.create(
                    reminder=reminder,
                    status='manual' if manual else 'sent',
                    telegram_message_id=telegram_response.get('message_id') if telegram_response else None,
                    error_message=None if telegram_response else "Ошибка отправки Telegram сообщения"
                )
                
                # Обновляем статус напоминания
                if not manual:
                    reminder.mark_as_sent()
                
                logger.info(
                    f"Отправлено напоминание {reminder.title} "
                    f"пользователю {reminder.user.phone_number}"
                )
                
                return history
                
        except Exception as e:
            logger.error(f"Ошибка отправки напоминания: {str(e)}")
            # Создаем запись об ошибке в истории
            try:
                history = ReminderHistory.objects.create(
                    reminder=reminder,
                    status='failed',
                    error_message=str(e)
                )
                return history
            except:
                pass
            raise
    
    @staticmethod
    def get_scheduled_reminders():
        """
        Получает напоминания, которые нужно отправить
        
        Returns:
            QuerySet: Напоминания для отправки
        """
        now = timezone.now()
        
        # Получаем напоминания, время которых наступило
        return Reminder.objects.filter(
            Q(
                # Первоначальные напоминания
                Q(scheduled_time__lte=now, last_sent__isnull=True) |
                # Повторные напоминания
                Q(next_reminder__lte=now, next_reminder__isnull=False)
            ),
            is_active=True
        ).select_related('user', 'goal')
    
    @staticmethod
    def process_scheduled_reminders():
        """
        Обрабатывает все запланированные напоминания
        
        Returns:
            dict: Статистика обработки
        """
        reminders = ReminderService.get_scheduled_reminders()
        
        stats = {
            'total_processed': 0,
            'sent_successfully': 0,
            'failed': 0,
            'errors': []
        }
        
        for reminder in reminders:
            try:
                stats['total_processed'] += 1
                ReminderService.send_reminder_notification(reminder)
                stats['sent_successfully'] += 1
                
            except Exception as e:
                stats['failed'] += 1
                stats['errors'].append({
                    'reminder_id': str(reminder.id),
                    'error': str(e)
                })
                logger.error(f"Ошибка обработки напоминания {reminder.id}: {str(e)}")
        
        logger.info(
            f"Обработано напоминаний: {stats['total_processed']}, "
            f"отправлено: {stats['sent_successfully']}, "
            f"ошибок: {stats['failed']}"
        )
        
        return stats
    
    @staticmethod
    def get_user_reminders_stats(user):
        """
        Получает статистику напоминаний пользователя
        
        Args:
            user: Пользователь
            
        Returns:
            dict: Статистика напоминаний
        """
        try:
            reminders = Reminder.objects.filter(user=user)
            now = timezone.now()
            
            # Базовая статистика
            total_reminders = reminders.count()
            active_reminders = reminders.filter(is_active=True).count()
            inactive_reminders = reminders.filter(is_active=False).count()
            
            # Статистика по состоянию
            overdue_reminders = reminders.filter(
                scheduled_time__lt=now,
                is_active=True,
                last_sent__isnull=True
            ).count()
            
            upcoming_time = now + timedelta(hours=24)
            upcoming_reminders = reminders.filter(
                Q(scheduled_time__range=(now, upcoming_time)) |
                Q(next_reminder__range=(now, upcoming_time)),
                is_active=True
            ).count()
            
            # Статистика по типам
            payment_reminders = reminders.filter(reminder_type='payment').count()
            debt_reminders = reminders.filter(reminder_type='debt').count()
            goal_reminders = reminders.filter(reminder_type='goal').count()
            custom_reminders = reminders.filter(reminder_type='custom').count()
            
            # Статистика по периодичности
            once_reminders = reminders.filter(repeat='once').count()
            daily_reminders = reminders.filter(repeat='daily').count()
            weekly_reminders = reminders.filter(repeat='weekly').count()
            monthly_reminders = reminders.filter(repeat='monthly').count()
            
            # Статистика отправки
            history = ReminderHistory.objects.filter(reminder__user=user)
            total_sent = history.count()
            
            today = now.date()
            sent_today = history.filter(sent_at__date=today).count()
            
            week_start = today - timedelta(days=today.weekday())
            sent_this_week = history.filter(sent_at__date__gte=week_start).count()
            
            month_start = today.replace(day=1)
            sent_this_month = history.filter(sent_at__date__gte=month_start).count()
            
            return {
                'total_reminders': total_reminders,
                'active_reminders': active_reminders,
                'inactive_reminders': inactive_reminders,
                'overdue_reminders': overdue_reminders,
                'upcoming_reminders': upcoming_reminders,
                'payment_reminders': payment_reminders,
                'debt_reminders': debt_reminders,
                'goal_reminders': goal_reminders,
                'custom_reminders': custom_reminders,
                'once_reminders': once_reminders,
                'daily_reminders': daily_reminders,
                'weekly_reminders': weekly_reminders,
                'monthly_reminders': monthly_reminders,
                'total_sent': total_sent,
                'sent_today': sent_today,
                'sent_this_week': sent_this_week,
                'sent_this_month': sent_this_month,
            }
            
        except Exception as e:
            logger.error(f"Ошибка получения статистики напоминаний: {str(e)}")
            raise
    
    @staticmethod
    def get_reminder_types():
        """
        Возвращает доступные типы напоминаний и повторений
        
        Returns:
            dict: Типы и повторения
        """
        return {
            'reminder_types': [
                {'value': choice[0], 'label': choice[1]}
                for choice in Reminder.TYPE_CHOICES
            ],
            'repeat_types': [
                {'value': choice[0], 'label': choice[1]}
                for choice in Reminder.REPEAT_CHOICES
            ]
        }
    
    @staticmethod
    def activate_reminder(reminder):
        """Активирует напоминание"""
        try:
            reminder.activate()
            logger.info(f"Напоминание {reminder.title} активировано")
            return {"is_active": True, "message": "Напоминание активировано"}
        except Exception as e:
            logger.error(f"Ошибка активации напоминания: {str(e)}")
            raise
    
    @staticmethod
    def deactivate_reminder(reminder):
        """Деактивирует напоминание"""
        try:
            reminder.deactivate()
            logger.info(f"Напоминание {reminder.title} деактивировано")
            return {"is_active": False, "message": "Напоминание деактивировано"}
        except Exception as e:
            logger.error(f"Ошибка деактивации напоминания: {str(e)}")
            raise
    
    # Методы для формирования Telegram сообщений (5 типов по ТЗ)
    
    @staticmethod
    def _send_reminder_created_notification(reminder):
        """Отправляет уведомление о создании напоминания"""
        try:
            message = ReminderService._format_reminder_created_message(reminder)
            send_telegram_message(reminder.user, message)
            
            reminder.telegram_notified = True
            reminder.save(update_fields=['telegram_notified'])
            
        except Exception as e:
            logger.error(f"Ошибка отправки уведомления о создании напоминания: {str(e)}")
    
    @staticmethod
    def _format_reminder_created_message(reminder):
        """Форматирует сообщение о создании напоминания"""
        type_emoji = {
            'payment': '💵',
            'debt': '📋',
            'goal': '🎯',
            'custom': '🔔'
        }
        
        repeat_text = {
            'once': 'однократно',
            'daily': 'ежедневно',
            'weekly': 'еженедельно',
            'monthly': 'ежемесячно'
        }
        
        emoji = type_emoji.get(reminder.reminder_type, '🔔')
        
        message = f"""<b>{emoji} Создано новое напоминание!</b>

📝 <b>Событие:</b> {reminder.title}
📅 <b>Дата:</b> {reminder.scheduled_time.strftime('%d.%m.%Y %H:%M')}
🔄 <b>Повтор:</b> {repeat_text.get(reminder.repeat, reminder.repeat)}
📱 <b>Тип:</b> {reminder.get_reminder_type_display()}"""
        
        if reminder.amount:
            message += f"\n💰 <b>Сумма:</b> {reminder.amount:,.0f} UZS"
        
        if reminder.description:
            message += f"\n📋 <b>Описание:</b> {reminder.description}"
        
        if reminder.goal:
            message += f"\n🎯 <b>Цель:</b> {reminder.goal.title}"
        
        message += "\n\n✅ Напоминание активировано и будет отправлено в указанное время!"
        
        return message
    
    @staticmethod
    def _format_payment_reminder_message(reminder):
        """Форматирует сообщение напоминания о платеже"""
        message = f"""<b>💵 Напоминание о платеже!</b>

📝 <b>Событие:</b> {reminder.title}
📅 <b>Дата:</b> {reminder.scheduled_time.strftime('%d.%m.%Y %H:%M')}"""
        
        if reminder.amount:
            message += f"\n💰 <b>Сумма:</b> {reminder.amount:,.0f} UZS"
        
        if reminder.description:
            message += f"\n📋 <b>Описание:</b> {reminder.description}"
        
        message += "\n\n⏰ Время пришло! Не забудьте совершить платеж."
        
        return message
    
    @staticmethod
    def _format_debt_reminder_message(reminder):
        """Форматирует сообщение напоминания о долге"""
        message = f"""<b>📋 Напоминание о долге!</b>

📝 <b>Событие:</b> {reminder.title}
📅 <b>Дата:</b> {reminder.scheduled_time.strftime('%d.%m.%Y %H:%M')}"""
        
        if reminder.amount:
            message += f"\n💰 <b>Сумма:</b> {reminder.amount:,.0f} UZS"
        
        if reminder.description:
            message += f"\n📋 <b>Описание:</b> {reminder.description}"
        
        message += "\n\n⚠️ Не забудьте погасить долг вовремя!"
        
        return message
    
    @staticmethod
    def _format_goal_reminder_message(reminder):
        """Форматирует сообщение напоминания о цели"""
        message = f"""<b>🎯 Напоминание о цели!</b>

📝 <b>Событие:</b> {reminder.title}
📅 <b>Дата:</b> {reminder.scheduled_time.strftime('%d.%m.%Y %H:%M')}"""
        
        if reminder.goal:
            progress = reminder.goal.progress_percentage
            remaining = reminder.goal.remaining_amount
            
            message += f"""
🎯 <b>Цель:</b> {reminder.goal.title}
📊 <b>Прогресс:</b> {progress:.1f}%
💰 <b>Осталось:</b> {remaining:,.0f} UZS"""
        
        if reminder.description:
            message += f"\n📋 <b>Описание:</b> {reminder.description}"
        
        message += "\n\n🚀 Продолжайте работать над достижением цели!"
        
        return message
    
    @staticmethod
    def _format_custom_reminder_message(reminder):
        """Форматирует произвольное сообщение напоминания"""
        message = f"""<b>📝 Кастомное напоминание!</b>

📝 <b>Событие:</b> {reminder.title}
📅 <b>Дата:</b> {reminder.scheduled_time.strftime('%d.%m.%Y %H:%M')}"""
        
        if reminder.description:
            message += f"\n📋 <b>Описание:</b> {reminder.description}"
        
        if reminder.amount:
            message += f"\n💰 <b>Сумма:</b> {reminder.amount:,.0f} UZS"
        
        message += "\n\n🔔 Время выполнить запланированное действие!"
        
        return message 