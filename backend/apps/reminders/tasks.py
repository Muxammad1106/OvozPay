"""
Celery задачи для модуля напоминаний и планировщика OvozPay
Этап 7: Reminders & Scheduler API
"""

import logging
from celery import shared_task
from django.utils import timezone
from apps.reminders.services.reminder_service import ReminderService

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def send_scheduled_reminders(self):
    """
    Задача для отправки запланированных напоминаний
    Выполняется каждые 5 минут согласно ТЗ
    """
    try:
        logger.info("Начинается обработка запланированных напоминаний")
        
        stats = ReminderService.process_scheduled_reminders()
        
        logger.info(
            f"Обработка запланированных напоминаний завершена. "
            f"Обработано: {stats['total_processed']}, "
            f"отправлено: {stats['sent_successfully']}, "
            f"ошибок: {stats['failed']}"
        )
        
        return {
            'status': 'success',
            'timestamp': timezone.now().isoformat(),
            'stats': stats
        }
        
    except Exception as e:
        logger.error(f"Ошибка в задаче send_scheduled_reminders: {str(e)}")
        
        # Повторная попытка с экспоненциальной задержкой
        try:
            raise self.retry(countdown=60 * (2 ** self.request.retries))
        except self.MaxRetriesExceededError:
            logger.error("Превышено максимальное количество попыток для send_scheduled_reminders")
            return {
                'status': 'failed',
                'error': str(e),
                'timestamp': timezone.now().isoformat()
            }


@shared_task(bind=True, max_retries=3)
def repeat_reminders(self):
    """
    Задача для создания повторных напоминаний
    Обновляет время следующего напоминания в зависимости от типа повторения
    """
    try:
        logger.info("Начинается обработка повторных напоминаний")
        
        from apps.reminders.models import Reminder
        
        # Получаем активные напоминания, которые были отправлены и требуют повторения
        reminders_to_repeat = Reminder.objects.filter(
            is_active=True,
            last_sent__isnull=False,
            repeat__in=['daily', 'weekly', 'monthly']
        ).exclude(repeat='once')
        
        updated_count = 0
        for reminder in reminders_to_repeat:
            try:
                # Обновляем время следующего напоминания
                old_next_reminder = reminder.next_reminder
                reminder._update_next_reminder()
                reminder.save(update_fields=['next_reminder'])
                
                if old_next_reminder != reminder.next_reminder:
                    updated_count += 1
                    logger.debug(f"Обновлено время следующего напоминания для {reminder.title}")
                    
            except Exception as e:
                logger.error(f"Ошибка обновления напоминания {reminder.id}: {str(e)}")
                continue
        
        logger.info(f"Обработка повторных напоминаний завершена. Обновлено: {updated_count}")
        
        return {
            'status': 'success',
            'timestamp': timezone.now().isoformat(),
            'updated_count': updated_count,
            'total_processed': reminders_to_repeat.count()
        }
        
    except Exception as e:
        logger.error(f"Ошибка в задаче repeat_reminders: {str(e)}")
        
        try:
            raise self.retry(countdown=60 * (2 ** self.request.retries))
        except self.MaxRetriesExceededError:
            logger.error("Превышено максимальное количество попыток для repeat_reminders")
            return {
                'status': 'failed',
                'error': str(e),
                'timestamp': timezone.now().isoformat()
            }


@shared_task(bind=True, max_retries=2)
def send_single_reminder(self, reminder_id):
    """
    Задача для отправки одного конкретного напоминания
    
    Args:
        reminder_id: UUID напоминания для отправки
    """
    try:
        from apps.reminders.models import Reminder
        
        reminder = Reminder.objects.get(id=reminder_id)
        
        if not reminder.is_active:
            logger.warning(f"Попытка отправить неактивное напоминание {reminder_id}")
            return {
                'status': 'skipped',
                'reason': 'Напоминание неактивно',
                'reminder_id': str(reminder_id)
            }
        
        history = ReminderService.send_reminder_notification(reminder)
        
        logger.info(f"Отправлено напоминание {reminder.title}")
        
        return {
            'status': 'success',
            'reminder_id': str(reminder_id),
            'reminder_title': reminder.title,
            'sent_at': history.sent_at.isoformat(),
            'telegram_message_id': history.telegram_message_id
        }
        
    except Reminder.DoesNotExist:
        logger.error(f"Напоминание {reminder_id} не найдено")
        return {
            'status': 'failed',
            'error': 'Напоминание не найдено',
            'reminder_id': str(reminder_id)
        }
        
    except Exception as e:
        logger.error(f"Ошибка отправки напоминания {reminder_id}: {str(e)}")
        
        try:
            raise self.retry(countdown=30 * (2 ** self.request.retries))
        except self.MaxRetriesExceededError:
            logger.error(f"Превышено максимальное количество попыток для напоминания {reminder_id}")
            return {
                'status': 'failed',
                'error': str(e),
                'reminder_id': str(reminder_id)
            }


@shared_task
def cleanup_old_reminder_history():
    """
    Задача для очистки старой истории напоминаний (старше 6 месяцев)
    Выполняется ежедневно в 2:00
    """
    try:
        from apps.reminders.models import ReminderHistory
        from datetime import timedelta
        
        cutoff_date = timezone.now() - timedelta(days=180)  # 6 месяцев
        
        old_history = ReminderHistory.objects.filter(sent_at__lt=cutoff_date)
        deleted_count = old_history.count()
        old_history.delete()
        
        logger.info(f"Удалено {deleted_count} старых записей истории напоминаний")
        
        return {
            'status': 'success',
            'deleted_count': deleted_count,
            'cutoff_date': cutoff_date.isoformat()
        }
        
    except Exception as e:
        logger.error(f"Ошибка очистки истории напоминаний: {str(e)}")
        return {
            'status': 'failed',
            'error': str(e)
        }


@shared_task
def deactivate_expired_reminders():
    """
    Задача для деактивации просроченных одноразовых напоминаний
    Выполняется ежедневно в 1:00
    """
    try:
        from apps.reminders.models import Reminder
        
        now = timezone.now()
        
        # Находим просроченные одноразовые напоминания
        expired_reminders = Reminder.objects.filter(
            scheduled_time__lt=now - timezone.timedelta(days=7),  # Просрочены более недели
            repeat='once',
            is_active=True,
            last_sent__isnull=True  # Не были отправлены
        )
        
        deactivated_count = 0
        for reminder in expired_reminders:
            reminder.deactivate()
            deactivated_count += 1
            logger.debug(f"Деактивировано просроченное напоминание: {reminder.title}")
        
        logger.info(f"Деактивировано {deactivated_count} просроченных напоминаний")
        
        return {
            'status': 'success',
            'deactivated_count': deactivated_count,
            'cutoff_date': (now - timezone.timedelta(days=7)).isoformat()
        }
        
    except Exception as e:
        logger.error(f"Ошибка деактивации просроченных напоминаний: {str(e)}")
        return {
            'status': 'failed',
            'error': str(e)
        }


@shared_task
def generate_reminder_stats():
    """
    Задача для генерации ежедневной статистики напоминаний
    Выполняется ежедневно в 23:00
    """
    try:
        from apps.reminders.models import Reminder, ReminderHistory
        from apps.users.models import User
        
        now = timezone.now()
        today = now.date()
        
        # Общая статистика
        total_reminders = Reminder.objects.count()
        active_reminders = Reminder.objects.filter(is_active=True).count()
        
        # Статистика за сегодня
        sent_today = ReminderHistory.objects.filter(sent_at__date=today).count()
        created_today = Reminder.objects.filter(created_at__date=today).count()
        
        # Статистика по типам
        type_stats = {}
        for choice in Reminder.TYPE_CHOICES:
            type_stats[choice[0]] = Reminder.objects.filter(reminder_type=choice[0]).count()
        
        # Пользователи с напоминаниями
        users_with_reminders = User.objects.filter(reminders__isnull=False).distinct().count()
        
        stats = {
            'date': today.isoformat(),
            'total_reminders': total_reminders,
            'active_reminders': active_reminders,
            'sent_today': sent_today,
            'created_today': created_today,
            'users_with_reminders': users_with_reminders,
            'type_distribution': type_stats
        }
        
        logger.info(f"Сгенерирована статистика напоминаний за {today}: {stats}")
        
        return {
            'status': 'success',
            'stats': stats
        }
        
    except Exception as e:
        logger.error(f"Ошибка генерации статистики напоминаний: {str(e)}")
        return {
            'status': 'failed',
            'error': str(e)
        } 