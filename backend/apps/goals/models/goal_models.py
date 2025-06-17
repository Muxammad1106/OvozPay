"""
Модели для модуля целей и накоплений OvozPay
Этап 6: Goals & Savings API
"""

import uuid
from decimal import Decimal
from django.db import models
from django.core.validators import MinValueValidator
from django.core.exceptions import ValidationError
from django.utils import timezone
from apps.core.models import BaseModel


class Goal(BaseModel):
    """Модель цели накопления"""
    
    STATUS_CHOICES = [
        ('active', 'Активная'),
        ('completed', 'Завершена'),
        ('failed', 'Провалена'),
        ('paused', 'Приостановлена'),
    ]
    
    REMINDER_INTERVAL_CHOICES = [
        ('daily', 'Ежедневно'),
        ('weekly', 'Еженедельно'),
        ('monthly', 'Ежемесячно'),
        ('never', 'Никогда'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey('users.User', on_delete=models.CASCADE, related_name='goals')
    title = models.CharField(max_length=200, verbose_name='Название цели')
    description = models.TextField(blank=True, null=True, verbose_name='Описание цели')
    target_amount = models.DecimalField(
        max_digits=15, 
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
        verbose_name='Целевая сумма'
    )
    current_amount = models.DecimalField(
        max_digits=15, 
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        verbose_name='Текущая сумма'
    )
    deadline = models.DateField(verbose_name='Срок достижения цели')
    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default='active',
        verbose_name='Статус цели'
    )
    reminder_interval = models.CharField(
        max_length=10, 
        choices=REMINDER_INTERVAL_CHOICES,
        default='weekly',
        verbose_name='Интервал напоминаний'
    )
    last_reminder_sent = models.DateTimeField(
        blank=True, 
        null=True,
        verbose_name='Последнее напоминание отправлено'
    )
    telegram_notified = models.BooleanField(
        default=False, 
        verbose_name='Telegram уведомление отправлено'
    )
    
    class Meta:
        ordering = ('-created_at',)
        verbose_name = 'Цель'
        verbose_name_plural = 'Цели'
        indexes = [
            models.Index(fields=['user', 'status']),
            models.Index(fields=['deadline', 'status']),
            models.Index(fields=['status']),
        ]
    
    def __str__(self):
        return f"{self.title} - {self.user.phone_number} ({self.get_status_display()})"
    
    @property
    def progress_percentage(self):
        """Возвращает процент выполнения цели"""
        if self.target_amount <= 0:
            return 0
        
        progress = (self.current_amount / self.target_amount) * 100
        return min(progress, 100)  # Не больше 100%
    
    @property
    def remaining_amount(self):
        """Возвращает оставшуюся сумму для достижения цели"""
        remaining = self.target_amount - self.current_amount
        return max(remaining, Decimal('0.00'))
    
    @property
    def is_overdue(self):
        """Проверяет, просрочена ли цель"""
        return timezone.now().date() > self.deadline and self.status == 'active'
    
    @property
    def is_completed(self):
        """Проверяет, завершена ли цель"""
        return self.status == 'completed'
    
    @property
    def is_active(self):
        """Проверяет, активна ли цель"""
        return self.status == 'active'
    
    @property
    def days_left(self):
        """Возвращает количество дней до дедлайна"""
        today = timezone.now().date()
        if self.deadline > today:
            return (self.deadline - today).days
        return 0
    
    def add_progress(self, amount, description=""):
        """Добавляет прогресс к цели"""
        if not self.is_active:
            raise ValidationError("Нельзя добавлять прогресс к неактивной цели")
        
        if amount <= 0:
            raise ValidationError("Сумма должна быть положительной")
        
        amount_decimal = Decimal(str(amount))
        
        # Проверяем, не превысит ли сумма целевую
        if self.current_amount + amount_decimal > self.target_amount:
            raise ValidationError(
                f"Сумма {amount} превысит целевую сумму. "
                f"Осталось внести: {self.remaining_amount}"
            )
        
        # Создаем транзакцию
        goal_transaction = GoalTransaction.objects.create(
            goal=self,
            amount=amount_decimal,
            description=description or f"Пополнение цели '{self.title}'"
        )
        
        # Обновляем текущую сумму
        self.current_amount += amount_decimal
        
        # Проверяем, достигнута ли цель
        if self.current_amount >= self.target_amount:
            self.status = 'completed'
            self.current_amount = self.target_amount  # Не превышаем целевую сумму
        
        self.save()
        return goal_transaction
    
    def complete_goal(self, force=False):
        """Отмечает цель как завершенную"""
        if not force and self.current_amount < self.target_amount:
            raise ValidationError("Цель не может быть завершена - недостаточно средств")
        
        self.status = 'completed'
        if force:
            self.current_amount = self.target_amount
        self.save()
    
    def fail_goal(self, reason=""):
        """Отмечает цель как проваленную"""
        if self.status == 'completed':
            raise ValidationError("Нельзя провалить завершенную цель")
        
        self.status = 'failed'
        self.save()
    
    def pause_goal(self):
        """Приостанавливает цель"""
        if self.status != 'active':
            raise ValidationError("Можно приостановить только активную цель")
        
        self.status = 'paused'
        self.save()
    
    def resume_goal(self):
        """Возобновляет цель"""
        if self.status != 'paused':
            raise ValidationError("Можно возобновить только приостановленную цель")
        
        # Проверяем, не истек ли дедлайн
        if self.is_overdue:
            raise ValidationError("Нельзя возобновить просроченную цель")
        
        self.status = 'active'
        self.save()
    
    def reset_progress(self):
        """Сбрасывает прогресс цели"""
        if self.status == 'completed':
            raise ValidationError("Нельзя сбросить прогресс завершенной цели")
        
        # Удаляем все транзакции
        self.transactions.all().delete()
        
        self.current_amount = Decimal('0.00')
        self.status = 'active'
        self.save()
    
    def clean(self):
        """Валидация модели"""
        super().clean()
        
        if self.deadline and self.deadline <= timezone.now().date():
            raise ValidationError('Дата цели должна быть в будущем')
        
        if self.current_amount > self.target_amount:
            raise ValidationError('Текущая сумма не может превышать целевую')
        
        if self.target_amount <= 0:
            raise ValidationError('Целевая сумма должна быть больше нуля')
    
    def save(self, *args, **kwargs):
        """Переопределение сохранения для дополнительной логики"""
        self.clean()
        
        # Автоматически обновляем статус просроченных целей
        if self.is_overdue and self.status == 'active':
            self.status = 'failed'
        
        super().save(*args, **kwargs)


class GoalTransaction(BaseModel):
    """Модель транзакции пополнения цели"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    goal = models.ForeignKey(
        Goal, 
        on_delete=models.CASCADE, 
        related_name='transactions',
        verbose_name='Цель'
    )
    amount = models.DecimalField(
        max_digits=15, 
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
        verbose_name='Сумма пополнения'
    )
    description = models.CharField(
        max_length=500,
        blank=True,
        null=True,
        verbose_name='Описание операции'
    )
    telegram_notified = models.BooleanField(
        default=False, 
        verbose_name='Telegram уведомление отправлено'
    )
    
    class Meta:
        ordering = ('-created_at',)
        verbose_name = 'Транзакция цели'
        verbose_name_plural = 'Транзакции целей'
        indexes = [
            models.Index(fields=['goal', 'created_at']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self):
        return f"Пополнение {self.goal.title} на {self.amount} UZS"
    
    @property
    def user(self):
        """Возвращает пользователя цели"""
        return self.goal.user
    
    def clean(self):
        """Валидация модели"""
        super().clean()
        
        if self.amount <= 0:
            raise ValidationError('Сумма пополнения должна быть больше нуля')
        
        if self.goal and not self.goal.is_active:
            raise ValidationError('Нельзя пополнять неактивную цель')
    
    def save(self, *args, **kwargs):
        """Переопределение сохранения для валидации"""
        self.clean()
        super().save(*args, **kwargs) 