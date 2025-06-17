"""
Модели для модуля напоминаний и планировщика OvozPay
Этап 7: Reminders & Scheduler API
"""

import uuid
from django.db import models
from django.core.validators import MinValueValidator
from django.core.exceptions import ValidationError
from django.utils import timezone
from apps.core.models import BaseModel


class Reminder(BaseModel):
    """Модель напоминания"""
    
    TYPE_CHOICES = [
        ('payment', 'Платеж'),
        ('debt', 'Долг'),
        ('goal', 'Цель'),
        ('custom', 'Произвольное'),
    ]
    
    REPEAT_CHOICES = [
        ('once', 'Однократно'),
        ('daily', 'Ежедневно'),
        ('weekly', 'Еженедельно'),
        ('monthly', 'Ежемесячно'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey('users.User', on_delete=models.CASCADE, related_name='reminders')
    title = models.CharField(max_length=255, verbose_name='Название события')
    description = models.TextField(blank=True, null=True, verbose_name='Описание')
    reminder_type = models.CharField(
        max_length=10,
        choices=TYPE_CHOICES,
        default='custom',
        verbose_name='Тип напоминания'
    )
    scheduled_time = models.DateTimeField(verbose_name='Время срабатывания')
    repeat = models.CharField(
        max_length=10,
        choices=REPEAT_CHOICES,
        default='once',
        verbose_name='Периодичность'
    )
    is_active = models.BooleanField(default=True, verbose_name='Активно')
    amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        blank=True,
        null=True,
        validators=[MinValueValidator(0)],
        verbose_name='Сумма (для платежей/долгов)'
    )
    goal = models.ForeignKey(
        'goals.Goal',
        on_delete=models.CASCADE,
        blank=True,
        null=True,
        related_name='reminders',
        verbose_name='Связанная цель'
    )
    last_sent = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name='Последняя отправка'
    )
    next_reminder = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name='Следующее напоминание'
    )
    telegram_notified = models.BooleanField(
        default=False,
        verbose_name='Telegram уведомление отправлено'
    )
    
    class Meta:
        ordering = ('-created_at',)
        verbose_name = 'Напоминание'
        verbose_name_plural = 'Напоминания'
        indexes = [
            models.Index(fields=['user', 'is_active']),
            models.Index(fields=['scheduled_time', 'is_active']),
            models.Index(fields=['next_reminder', 'is_active']),
            models.Index(fields=['reminder_type']),
            models.Index(fields=['repeat']),
        ]
    
    def __str__(self):
        return f"{self.title} - {self.user.phone_number} ({self.get_reminder_type_display()})"
    
    @property
    def is_overdue(self):
        """Проверяет, просрочено ли напоминание"""
        return timezone.now() > self.scheduled_time and self.is_active
    
    @property
    def is_upcoming(self):
        """Проверяет, предстоящее ли напоминание (в течение 24 часов)"""
        now = timezone.now()
        upcoming_time = now + timezone.timedelta(hours=24)
        return now <= self.scheduled_time <= upcoming_time and self.is_active
    
    @property
    def time_until_reminder(self):
        """Возвращает время до напоминания"""
        if not self.is_active:
            return None
        
        now = timezone.now()
        target_time = self.next_reminder or self.scheduled_time
        
        if target_time > now:
            return target_time - now
        return None
    
    def activate(self):
        """Активирует напоминание"""
        self.is_active = True
        self._update_next_reminder()
        self.save()
    
    def deactivate(self):
        """Деактивирует напоминание"""
        self.is_active = False
        self.next_reminder = None
        self.save()
    
    def mark_as_sent(self):
        """Отмечает напоминание как отправленное"""
        self.last_sent = timezone.now()
        self.telegram_notified = True
        
        if self.repeat == 'once':
            self.deactivate()
        else:
            self._update_next_reminder()
        
        self.save()
    
    def _update_next_reminder(self):
        """Обновляет время следующего напоминания"""
        if not self.is_active or self.repeat == 'once':
            self.next_reminder = None
            return
        
        now = timezone.now()
        base_time = self.last_sent or self.scheduled_time
        
        # Если базовое время в прошлом, используем текущее время
        if base_time < now:
            base_time = now
        
        if self.repeat == 'daily':
            self.next_reminder = base_time + timezone.timedelta(days=1)
        elif self.repeat == 'weekly':
            self.next_reminder = base_time + timezone.timedelta(weeks=1)
        elif self.repeat == 'monthly':
            # Добавляем примерно месяц (30 дней)
            self.next_reminder = base_time + timezone.timedelta(days=30)
    
    def clean(self):
        """Валидация модели"""
        super().clean()
        
        # Проверяем, что scheduled_time не в прошлом для новых записей
        if not self.pk and self.scheduled_time:
            if self.scheduled_time < timezone.now():
                raise ValidationError("Время напоминания не может быть в прошлом")
        
        # Проверяем связанную цель
        if self.reminder_type == 'goal' and not self.goal:
            raise ValidationError("Для напоминания о цели необходимо указать цель")
        
        # Проверяем сумму для платежей и долгов
        if self.reminder_type in ['payment', 'debt'] and not self.amount:
            raise ValidationError("Для напоминания о платеже/долге необходимо указать сумму")
    
    def save(self, *args, **kwargs):
        """Переопределяем save для дополнительной логики"""
        # Обновляем next_reminder при создании или изменении
        if self.is_active:
            self._update_next_reminder()
        
        super().save(*args, **kwargs)


class ReminderHistory(BaseModel):
    """Модель истории выполненных напоминаний"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    reminder = models.ForeignKey(
        Reminder,
        on_delete=models.CASCADE,
        related_name='history',
        verbose_name='Напоминание'
    )
    sent_at = models.DateTimeField(
        default=timezone.now,
        verbose_name='Время отправки'
    )
    status = models.CharField(
        max_length=20,
        choices=[
            ('sent', 'Отправлено'),
            ('failed', 'Ошибка отправки'),
            ('manual', 'Отправлено вручную'),
        ],
        default='sent',
        verbose_name='Статус отправки'
    )
    telegram_message_id = models.IntegerField(
        blank=True,
        null=True,
        verbose_name='ID сообщения в Telegram'
    )
    error_message = models.TextField(
        blank=True,
        null=True,
        verbose_name='Сообщение об ошибке'
    )
    
    class Meta:
        ordering = ('-sent_at',)
        verbose_name = 'История напоминания'
        verbose_name_plural = 'История напоминаний'
        indexes = [
            models.Index(fields=['reminder', 'sent_at']),
            models.Index(fields=['status']),
            models.Index(fields=['sent_at']),
        ]
    
    def __str__(self):
        return f"История: {self.reminder.title} - {self.sent_at.strftime('%d.%m.%Y %H:%M')}"
    
    @property
    def user(self):
        """Возвращает пользователя напоминания"""
        return self.reminder.user 