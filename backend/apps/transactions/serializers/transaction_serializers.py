from decimal import Decimal
from rest_framework import serializers
from django.utils import timezone
from apps.transactions.models import Transaction, DebtTransaction
from apps.categories.models import Category
from apps.sources.models import Source
from apps.users.models import User


class TransactionSerializer(serializers.ModelSerializer):
    user_phone = serializers.CharField(source='user.phone_number', read_only=True)
    category_name = serializers.CharField(source='category.name', read_only=True)
    source_name = serializers.CharField(source='source.name', read_only=True)
    related_user_phone = serializers.CharField(source='related_user.phone_number', read_only=True)
    balance_impact = serializers.DecimalField(source='get_balance_impact', max_digits=15, decimal_places=2, read_only=True)
    
    class Meta:
        model = Transaction
        fields = [
            'id', 'user', 'user_phone', 'amount', 'category', 'category_name',
            'source', 'source_name', 'type', 'description', 'date',
            'related_user', 'related_user_phone', 'is_closed', 'telegram_notified',
            'balance_impact', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'telegram_notified']
    
    def validate_amount(self, value):
        """Валидация суммы - должна быть положительной"""
        if value <= 0:
            raise serializers.ValidationError('Сумма должна быть больше нуля')
        
        if value > Decimal('999999999999.99'):
            raise serializers.ValidationError('Сумма слишком большая')
        
        return value
    
    def validate_date(self, value):
        """Валидация даты - не должна быть в далеком будущем"""
        if value > timezone.now() + timezone.timedelta(days=365):
            raise serializers.ValidationError('Дата не может быть более чем на год в будущем')
        
        return value
    
    def validate(self, data):
        """Кросс-валидация полей"""
        transaction_type = data.get('type')
        related_user = data.get('related_user')
        user = data.get('user') or (self.instance.user if self.instance else None)
        
        if transaction_type == 'transfer':
            if not related_user:
                raise serializers.ValidationError({
                    'related_user': 'Для перевода необходимо указать получателя'
                })
            
            if related_user == user:
                raise serializers.ValidationError({
                    'related_user': 'Нельзя переводить самому себе'
                })
        
        if transaction_type == 'expense':
            # Здесь можно добавить проверку баланса
            # Но оставим это для сервисного слоя
            pass
        
        return data
    
    def create(self, validated_data):
        """Создание транзакции с установкой пользователя из контекста"""
        request = self.context.get('request')
        if request and hasattr(request, 'user'):
            validated_data['user'] = request.user
        
        return super().create(validated_data)


class DebtTransactionSerializer(serializers.ModelSerializer):
    user_phone = serializers.CharField(source='user.phone_number', read_only=True)
    category_name = serializers.CharField(source='category.name', read_only=True)
    remaining_amount = serializers.DecimalField(max_digits=15, decimal_places=2, read_only=True)
    payment_progress = serializers.FloatField(read_only=True)
    is_overdue = serializers.BooleanField(read_only=True)
    
    class Meta:
        model = DebtTransaction
        fields = [
            'id', 'user', 'user_phone', 'amount', 'category', 'category_name',
            'type', 'description', 'date', 'is_closed', 'telegram_notified',
            'due_date', 'paid_amount', 'status', 'debtor_name', 'debt_direction',
            'remaining_amount', 'payment_progress', 'is_overdue',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'type', 'created_at', 'updated_at', 'telegram_notified', 'status'
        ]
    
    def validate_amount(self, value):
        """Валидация суммы долга"""
        if value <= 0:
            raise serializers.ValidationError('Сумма долга должна быть больше нуля')
        
        if value > Decimal('999999999999.99'):
            raise serializers.ValidationError('Сумма долга слишком большая')
        
        return value
    
    def validate_due_date(self, value):
        """Валидация даты погашения - должна быть в будущем"""
        if value and value <= timezone.now():
            raise serializers.ValidationError('Дата погашения должна быть в будущем')
        
        return value
    
    def validate_paid_amount(self, value):
        """Валидация выплаченной суммы"""
        if value < 0:
            raise serializers.ValidationError('Выплаченная сумма не может быть отрицательной')
        
        # Проверяем что выплаченная сумма не превышает общую сумму долга
        amount = self.initial_data.get('amount') or (self.instance.amount if self.instance else 0)
        if value > amount:
            raise serializers.ValidationError('Выплаченная сумма не может превышать сумму долга')
        
        return value
    
    def validate_debtor_name(self, value):
        """Валидация имени должника"""
        if not value or not value.strip():
            raise serializers.ValidationError('Имя должника/кредитора обязательно')
        
        if len(value.strip()) < 2:
            raise serializers.ValidationError('Имя должника/кредитора слишком короткое')
        
        return value.strip()
    
    def create(self, validated_data):
        """Создание долговой транзакции"""
        request = self.context.get('request')
        if request and hasattr(request, 'user'):
            validated_data['user'] = request.user
        
        validated_data['type'] = 'debt'
        
        return super().create(validated_data)


class DebtPaymentSerializer(serializers.Serializer):
    """Сериализатор для добавления платежа по долгу"""
    payment_amount = serializers.DecimalField(
        max_digits=15, 
        decimal_places=2,
        min_value=Decimal('0.01')
    )
    description = serializers.CharField(
        max_length=500, 
        required=False, 
        allow_blank=True
    )
    
    def validate_payment_amount(self, value):
        """Валидация суммы платежа"""
        if value <= 0:
            raise serializers.ValidationError('Сумма платежа должна быть положительной')
        
        return value


class TransactionStatsSerializer(serializers.Serializer):
    """Сериализатор для статистики транзакций"""
    total_income = serializers.DecimalField(max_digits=15, decimal_places=2)
    total_expense = serializers.DecimalField(max_digits=15, decimal_places=2)
    total_debts = serializers.DecimalField(max_digits=15, decimal_places=2)
    open_debts_count = serializers.IntegerField()
    current_balance = serializers.DecimalField(max_digits=15, decimal_places=2)
    transactions_count = serializers.IntegerField()


class TransactionCreateSerializer(serializers.ModelSerializer):
    """Упрощенный сериализатор для быстрого создания транзакций"""
    
    class Meta:
        model = Transaction
        fields = ['amount', 'type', 'description', 'category', 'date']
    
    def validate_amount(self, value):
        if value <= 0:
            raise serializers.ValidationError('Сумма должна быть больше нуля')
        return value
    
    def create(self, validated_data):
        request = self.context.get('request')
        if request and hasattr(request, 'user'):
            validated_data['user'] = request.user
        
        return super().create(validated_data) 