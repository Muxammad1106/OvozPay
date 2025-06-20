import uuid
from decimal import Decimal
from django.db import models
from apps.core.models import BaseModel


class Transaction(BaseModel):
    """Модель транзакции (доход/расход)"""
    
    TYPE_CHOICES = [
        ('income', 'Доход'),
        ('expense', 'Расход'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey('users.User', on_delete=models.CASCADE, related_name='transactions')
    amount = models.DecimalField(
        max_digits=15, 
        decimal_places=2,
        verbose_name='Сумма'
    )
    category = models.ForeignKey(
        'categories.Category', 
        on_delete=models.SET_NULL, 
        null=True,
        verbose_name='Категория'
    )
    type = models.CharField(
        max_length=10, 
        choices=TYPE_CHOICES,
        verbose_name='Тип операции'
    )
    description = models.TextField(blank=True, verbose_name='Описание')
    date = models.DateTimeField(verbose_name='Дата операции')
    
    class Meta:
        ordering = ('-date', '-created_at')
        verbose_name = 'Транзакция'
        verbose_name_plural = 'Транзакции'
        indexes = [
            models.Index(fields=['user', 'type']),
            models.Index(fields=['date']),
        ]
    
    def __str__(self):
        type_display = 'Доход' if self.type == 'income' else 'Расход'
        return f"{type_display}: {self.amount} ({self.user.phone_number})"
    
    def clean(self):
        """Валидация модели"""
        from django.core.exceptions import ValidationError
        
        if self.amount <= 0:
            raise ValidationError('Сумма должна быть больше нуля')


class Debt(BaseModel):
    """Модель долга"""
    
    DIRECTION_CHOICES = [
        ('from_me', 'Я дал в долг'),
        ('to_me', 'Мне дали в долг'),
    ]
    
    STATUS_CHOICES = [
        ('open', 'Открыт'),
        ('closed', 'Закрыт'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey('users.User', on_delete=models.CASCADE, related_name='debts')
    amount = models.DecimalField(
        max_digits=15, 
        decimal_places=2,
        verbose_name='Сумма долга'
    )
    debtor_name = models.CharField(max_length=100, verbose_name='Имя должника/кредитора')
    direction = models.CharField(
        max_length=10, 
        choices=DIRECTION_CHOICES,
        verbose_name='Направление долга'
    )
    date = models.DateTimeField(verbose_name='Дата создания долга')
    description = models.TextField(blank=True, verbose_name='Описание')
    status = models.CharField(
        max_length=10, 
        choices=STATUS_CHOICES, 
        default='open',
        verbose_name='Статус'
    )
    
    class Meta:
        ordering = ('-date', '-created_at')
        verbose_name = 'Долг'
        verbose_name_plural = 'Долги'
        indexes = [
            models.Index(fields=['user', 'status']),
            models.Index(fields=['date']),
        ]
    
    def __str__(self):
        direction_display = 'дал' if self.direction == 'from_me' else 'взял'
        return f"{self.user.phone_number} {direction_display} {self.amount} - {self.debtor_name}"
    
    def clean(self):
        """Валидация модели"""
        from django.core.exceptions import ValidationError
        
        if self.amount <= 0:
            raise ValidationError('Сумма долга должна быть больше нуля')
    
    def close_debt(self):
        """Закрывает долг"""
        self.status = 'closed'
        self.save()
    
    @property
    def is_overdue(self):
        """Проверяет, просрочен ли долг (старше 30 дней)"""
        from django.utils import timezone
        from datetime import timedelta
        
        if self.status == 'closed':
            return False
        
        return timezone.now() - self.date > timedelta(days=30)
