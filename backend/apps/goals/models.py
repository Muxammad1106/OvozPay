import uuid
from decimal import Decimal
from django.db import models
from django.core.validators import MinValueValidator
from apps.core.models import BaseModel


class Goal(BaseModel):
    """Модель цели накопления"""
    
    REMINDER_INTERVAL_CHOICES = [
        ('daily', 'Ежедневно'),
        ('weekly', 'Еженедельно'),
        ('monthly', 'Ежемесячно'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey('users.User', on_delete=models.CASCADE, related_name='goals')
    title = models.CharField(max_length=200, verbose_name='Название цели')
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
    reminder_interval = models.CharField(
        max_length=10, 
        choices=REMINDER_INTERVAL_CHOICES,
        default='weekly',
        verbose_name='Интервал напоминаний'
    )
    is_completed = models.BooleanField(default=False, verbose_name='Цель достигнута')
    
    class Meta:
        ordering = ('-created_at',)
        verbose_name = 'Цель'
        verbose_name_plural = 'Цели'
        indexes = [
            models.Index(fields=['user', 'is_completed']),
            models.Index(fields=['deadline']),
        ]
    
    def __str__(self):
        return f"{self.title} - {self.user.phone_number}"
    
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
        from django.utils import timezone
        return timezone.now().date() > self.deadline and not self.is_completed
    
    def add_progress(self, amount):
        """Добавляет прогресс к цели"""
        if amount <= 0:
            return False
        
        self.current_amount += Decimal(str(amount))
        
        # Проверяем, достигнута ли цель
        if self.current_amount >= self.target_amount:
            self.is_completed = True
            self.current_amount = self.target_amount  # Не превышаем целевую сумму
        
        self.save()
        return True
    
    def reset_progress(self):
        """Сбрасывает прогресс цели"""
        self.current_amount = Decimal('0.00')
        self.is_completed = False
        self.save()
    
    def complete_goal(self):
        """Отмечает цель как завершенную"""
        self.current_amount = self.target_amount
        self.is_completed = True
        self.save()
    
    def clean(self):
        """Валидация модели"""
        from django.core.exceptions import ValidationError
        from django.utils import timezone
        
        if self.deadline and self.deadline <= timezone.now().date():
            raise ValidationError('Дата цели должна быть в будущем')
        
        if self.current_amount > self.target_amount:
            raise ValidationError('Текущая сумма не может превышать целевую')
