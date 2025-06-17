import uuid
from decimal import Decimal
from django.db import models
from django.core.exceptions import ValidationError
from django.utils import timezone
from apps.core.models import BaseModel


class Transaction(BaseModel):
    """Улучшенная модель транзакции"""
    
    TYPE_CHOICES = [
        ('income', 'Доход'),
        ('expense', 'Расход'),
        ('debt', 'Долг'),
        ('transfer', 'Перевод'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        'users.User', 
        on_delete=models.CASCADE, 
        related_name='transactions',
        verbose_name='Пользователь'
    )
    amount = models.DecimalField(
        max_digits=15, 
        decimal_places=2,
        verbose_name='Сумма'
    )
    category = models.ForeignKey(
        'categories.Category', 
        on_delete=models.SET_NULL, 
        null=True, blank=True,
        verbose_name='Категория'
    )
    source = models.ForeignKey(
        'sources.Source',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        verbose_name='Источник'
    )
    type = models.CharField(
        max_length=10, 
        choices=TYPE_CHOICES,
        verbose_name='Тип операции'
    )
    description = models.TextField(blank=True, verbose_name='Описание')
    date = models.DateTimeField(verbose_name='Дата операции')
    
    related_user = models.ForeignKey(
        'users.User',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='related_transactions',
        verbose_name='Связанный пользователь'
    )
    
    is_closed = models.BooleanField(default=False, verbose_name='Закрыто')
    
    telegram_notified = models.BooleanField(
        default=False, 
        verbose_name='Уведомление отправлено'
    )
    
    class Meta:
        ordering = ('-date', '-created_at')
        verbose_name = 'Транзакция'
        verbose_name_plural = 'Транзакции'
        indexes = [
            models.Index(fields=['user', 'type']),
            models.Index(fields=['date']),
            models.Index(fields=['user', 'is_closed']),
        ]
    
    def __str__(self):
        type_display = dict(self.TYPE_CHOICES).get(self.type, self.type)
        return f"{type_display}: {self.amount} ({self.user.phone_number})"
    
    def clean(self):
        """Валидация модели"""
        if self.amount <= 0:
            raise ValidationError('Сумма должна быть больше нуля')
        
        if self.type == 'transfer' and not self.related_user:
            raise ValidationError('Для перевода необходимо указать получателя')
        
        if self.type == 'transfer' and self.related_user == self.user:
            raise ValidationError('Нельзя переводить самому себе')
    
    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)
    
    @property
    def is_debt(self):
        """Проверяет, является ли транзакция долгом"""
        return self.type == 'debt'
    
    @property
    def is_transfer(self):
        """Проверяет, является ли транзакция переводом"""
        return self.type == 'transfer'
    
    def get_balance_impact(self):
        """Возвращает влияние на баланс (+/-)"""
        if self.type in ['income']:
            return self.amount
        elif self.type in ['expense', 'transfer']:
            return -self.amount
        elif self.type == 'debt':
            return Decimal('0')
        return Decimal('0')


class DebtTransaction(Transaction):
    """Модель долговой транзакции (наследник Transaction)"""
    
    STATUS_CHOICES = [
        ('open', 'Открыт'),
        ('partial', 'Частично погашен'),
        ('closed', 'Закрыт'),
        ('overdue', 'Просрочен'),
    ]
    
    due_date = models.DateTimeField(
        null=True, blank=True,
        verbose_name='Дата погашения'
    )
    
    paid_amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name='Выплаченная сумма'
    )
    
    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default='open',
        verbose_name='Статус долга'
    )
    
    debtor_name = models.CharField(
        max_length=100,
        verbose_name='Имя должника/кредитора'
    )
    
    debt_direction = models.CharField(
        max_length=10,
        choices=[
            ('from_me', 'Я дал в долг'),
            ('to_me', 'Мне дали в долг'),
        ],
        verbose_name='Направление долга'
    )
    
    class Meta:
        verbose_name = 'Долговая транзакция'
        verbose_name_plural = 'Долговые транзакции'
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['due_date']),
            models.Index(fields=['debt_direction']),
        ]
    
    def __str__(self):
        direction = 'дал' if self.debt_direction == 'from_me' else 'взял'
        return f"{self.user.phone_number} {direction} {self.amount} - {self.debtor_name}"
    
    def clean(self):
        """Дополнительная валидация для долгов"""
        super().clean()
        
        if self.type != 'debt':
            raise ValidationError('DebtTransaction должна иметь type="debt"')
        
        if self.due_date and self.due_date <= timezone.now():
            raise ValidationError('Дата погашения должна быть в будущем')
        
        if self.paid_amount < 0:
            raise ValidationError('Выплаченная сумма не может быть отрицательной')
        
        if self.paid_amount > self.amount:
            raise ValidationError('Выплаченная сумма не может превышать сумму долга')
    
    def save(self, *args, **kwargs):
        self.type = 'debt'
        self.update_status()
        super().save(*args, **kwargs)
    
    def update_status(self):
        """Обновляет статус долга на основе выплаченной суммы и даты"""
        if self.paid_amount >= self.amount:
            self.status = 'closed'
            self.is_closed = True
        elif self.paid_amount > 0:
            self.status = 'partial'
        elif self.due_date and self.due_date < timezone.now() and self.status != 'closed':
            self.status = 'overdue'
        else:
            self.status = 'open'
    
    def add_payment(self, payment_amount):
        """Добавляет платеж к долгу"""
        if payment_amount <= 0:
            raise ValidationError('Сумма платежа должна быть положительной')
        
        if self.paid_amount + payment_amount > self.amount:
            raise ValidationError('Общая сумма платежей не может превышать сумму долга')
        
        self.paid_amount += payment_amount
        self.update_status()
        self.save()
        
        return self.status == 'closed'
    
    def close_debt(self):
        """Полностью закрывает долг"""
        self.paid_amount = self.amount
        self.status = 'closed'
        self.is_closed = True
        self.save()
    
    @property
    def remaining_amount(self):
        """Возвращает оставшуюся сумму долга"""
        return self.amount - self.paid_amount
    
    @property
    def is_overdue(self):
        """Проверяет, просрочен ли долг"""
        if self.status == 'closed':
            return False
        
        if not self.due_date:
            return False
        
        return timezone.now() > self.due_date
    
    @property
    def payment_progress(self):
        """Возвращает прогресс выплаты в процентах"""
        if self.amount == 0:
            return 0
        return float((self.paid_amount / self.amount) * 100) 