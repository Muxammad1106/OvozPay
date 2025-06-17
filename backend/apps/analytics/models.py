import uuid
from decimal import Decimal
from django.db import models
from django.core.validators import MinValueValidator
from apps.core.models import BaseModel


class Report(BaseModel):
    """Модель отчета по доходам/расходам за период"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey('users.User', on_delete=models.CASCADE, related_name='reports')
    period_start = models.DateField(verbose_name='Начало периода')
    period_end = models.DateField(verbose_name='Конец периода')
    total_income = models.DecimalField(
        max_digits=15, 
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        verbose_name='Общий доход'
    )
    total_expense = models.DecimalField(
        max_digits=15, 
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        verbose_name='Общий расход'
    )
    
    class Meta:
        ordering = ('-period_end', '-created_at')
        verbose_name = 'Отчет'
        verbose_name_plural = 'Отчеты'
        unique_together = [['user', 'period_start', 'period_end']]
        indexes = [
            models.Index(fields=['user', 'period_start', 'period_end']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self):
        return f"Отчет {self.user.phone_number} ({self.period_start} - {self.period_end})"
    
    @property
    def profit(self):
        """Возвращает прибыль (доходы - расходы)"""
        return self.total_income - self.total_expense
    
    @property
    def savings_rate(self):
        """Возвращает норму сбережений в процентах"""
        if self.total_income <= 0:
            return 0
        
        return (self.profit / self.total_income) * 100
    
    @classmethod
    def generate_report(cls, user, period_start, period_end):
        """Генерирует отчет для пользователя за указанный период"""
        from apps.transactions.models import Transaction
        from django.db.models import Sum, Q
        
        # Получаем транзакции за период
        transactions = Transaction.objects.filter(
            user=user,
            date__gte=period_start,
            date__lte=period_end
        )
        
        # Считаем доходы и расходы
        income_sum = transactions.filter(type='income').aggregate(
            total=Sum('amount')
        )['total'] or Decimal('0.00')
        
        expense_sum = transactions.filter(type='expense').aggregate(
            total=Sum('amount')
        )['total'] or Decimal('0.00')
        
        # Создаем или обновляем отчет
        report, created = cls.objects.update_or_create(
            user=user,
            period_start=period_start,
            period_end=period_end,
            defaults={
                'total_income': income_sum,
                'total_expense': expense_sum,
            }
        )
        
        return report
    
    def clean(self):
        """Валидация модели"""
        from django.core.exceptions import ValidationError
        
        if self.period_start >= self.period_end:
            raise ValidationError('Начальная дата должна быть раньше конечной')


class Balance(BaseModel):
    """Модель баланса пользователя"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField('users.User', on_delete=models.CASCADE, related_name='balance')
    amount = models.DecimalField(
        max_digits=15, 
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name='Сумма баланса'
    )
    
    class Meta:
        verbose_name = 'Баланс'
        verbose_name_plural = 'Балансы'
        indexes = [
            models.Index(fields=['updated_at']),
        ]
    
    def __str__(self):
        return f"Баланс {self.user.phone_number}: {self.amount}"
    
    def update_balance(self):
        """Обновляет баланс на основе всех транзакций пользователя"""
        from apps.transactions.models import Transaction
        from django.db.models import Sum, Q
        
        # Считаем общие доходы
        total_income = Transaction.objects.filter(
            user=self.user,
            type='income'
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
        
        # Считаем общие расходы
        total_expense = Transaction.objects.filter(
            user=self.user,
            type='expense'
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
        
        # Обновляем баланс
        self.amount = total_income - total_expense
        self.save()
        
        return self.amount
    
    def add_transaction(self, amount, transaction_type):
        """Добавляет транзакцию к балансу"""
        if transaction_type == 'income':
            self.amount += Decimal(str(amount))
        elif transaction_type == 'expense':
            self.amount -= Decimal(str(amount))
        
        self.save()
        return self.amount
    
    @classmethod
    def get_or_create_for_user(cls, user):
        """Получает или создает баланс для пользователя"""
        balance, created = cls.objects.get_or_create(
            user=user,
            defaults={'amount': Decimal('0.00')}
        )
        
        if created:
            balance.update_balance()
        
        return balance
