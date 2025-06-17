"""
Сериализаторы для модуля целей и накоплений OvozPay
Этап 6: Goals & Savings API
"""

from rest_framework import serializers
from decimal import Decimal
from django.utils import timezone
from django.core.exceptions import ValidationError as DjangoValidationError
from apps.goals.models import Goal, GoalTransaction
from apps.users.models import User


class GoalSerializer(serializers.ModelSerializer):
    """Основной сериализатор для модели Goal"""
    
    user_phone = serializers.CharField(source='user.phone_number', read_only=True)
    progress_percentage = serializers.FloatField(read_only=True)
    remaining_amount = serializers.DecimalField(max_digits=15, decimal_places=2, read_only=True)
    is_overdue = serializers.BooleanField(read_only=True)
    is_completed = serializers.BooleanField(read_only=True)
    is_active = serializers.BooleanField(read_only=True)
    days_left = serializers.IntegerField(read_only=True)
    transactions_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Goal
        fields = [
            'id', 'user', 'user_phone', 'title', 'description', 'target_amount', 
            'current_amount', 'deadline', 'status', 'reminder_interval',
            'last_reminder_sent', 'telegram_notified', 'progress_percentage',
            'remaining_amount', 'is_overdue', 'is_completed', 'is_active',
            'days_left', 'transactions_count', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'user', 'current_amount', 'created_at', 'updated_at', 
            'user_phone', 'progress_percentage', 'remaining_amount', 'is_overdue',
            'is_completed', 'is_active', 'days_left', 'transactions_count',
            'last_reminder_sent', 'telegram_notified'
        ]
    
    def get_transactions_count(self, obj):
        """Возвращает количество транзакций по цели"""
        return obj.transactions.count()
    
    def validate_target_amount(self, value):
        """Валидация целевой суммы"""
        if value <= Decimal('0'):
            raise serializers.ValidationError("Целевая сумма должна быть больше нуля")
        if value > Decimal('999999999999.99'):
            raise serializers.ValidationError("Целевая сумма слишком большая")
        return value
    
    def validate_deadline(self, value):
        """Валидация даты дедлайна"""
        if value <= timezone.now().date():
            raise serializers.ValidationError("Дата цели должна быть в будущем")
        return value
    
    def validate_title(self, value):
        """Валидация названия цели"""
        if len(value.strip()) < 3:
            raise serializers.ValidationError("Название цели должно содержать минимум 3 символа")
        if len(value.strip()) > 200:
            raise serializers.ValidationError("Название цели слишком длинное")
        return value.strip()
    
    def validate_description(self, value):
        """Валидация описания цели"""
        if value and len(value.strip()) > 1000:
            raise serializers.ValidationError("Описание цели слишком длинное")
        return value.strip() if value else None
    
    def validate_status(self, value):
        """Валидация статуса цели"""
        valid_statuses = ['active', 'completed', 'failed', 'paused']
        if value not in valid_statuses:
            raise serializers.ValidationError(f"Недопустимый статус. Доступные: {valid_statuses}")
        return value


class GoalCreateSerializer(serializers.ModelSerializer):
    """Сериализатор для создания новой цели"""
    
    class Meta:
        model = Goal
        fields = [
            'title', 'description', 'target_amount', 'deadline', 'reminder_interval'
        ]
    
    def validate_target_amount(self, value):
        """Валидация целевой суммы"""
        if value <= Decimal('0'):
            raise serializers.ValidationError("Целевая сумма должна быть больше нуля")
        if value > Decimal('999999999999.99'):
            raise serializers.ValidationError("Целевая сумма слишком большая")
        return value
    
    def validate_deadline(self, value):
        """Валидация даты дедлайна"""
        if value <= timezone.now().date():
            raise serializers.ValidationError("Дата цели должна быть в будущем")
        return value
    
    def validate_title(self, value):
        """Валидация названия цели"""
        if len(value.strip()) < 3:
            raise serializers.ValidationError("Название цели должно содержать минимум 3 символа")
        return value.strip()
    
    def create(self, validated_data):
        """Создание новой цели с автоматическим назначением пользователя"""
        request = self.context.get('request')
        if request and hasattr(request, 'user'):
            validated_data['user'] = request.user
        return super().create(validated_data)


class GoalTransactionSerializer(serializers.ModelSerializer):
    """Сериализатор для транзакций пополнения цели"""
    
    goal_title = serializers.CharField(source='goal.title', read_only=True)
    user_phone = serializers.CharField(source='user.phone_number', read_only=True)
    
    class Meta:
        model = GoalTransaction
        fields = [
            'id', 'goal', 'goal_title', 'user_phone', 'amount', 'description',
            'telegram_notified', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'goal_title', 'user_phone', 'telegram_notified', 
            'created_at', 'updated_at'
        ]
    
    def validate_amount(self, value):
        """Валидация суммы пополнения"""
        if value <= Decimal('0'):
            raise serializers.ValidationError("Сумма пополнения должна быть больше нуля")
        if value > Decimal('999999999999.99'):
            raise serializers.ValidationError("Сумма пополнения слишком большая")
        return value
    
    def validate_goal(self, value):
        """Валидация цели"""
        if not value.is_active:
            raise serializers.ValidationError("Нельзя пополнять неактивную цель")
        
        # Проверяем, что цель принадлежит текущему пользователю
        request = self.context.get('request')
        if request and hasattr(request, 'user') and value.user != request.user:
            raise serializers.ValidationError("Вы можете пополнять только свои цели")
        
        return value
    
    def validate(self, data):
        """Кросс-валидация данных"""
        goal = data.get('goal')
        amount = data.get('amount')
        
        if goal and amount:
            # Проверяем, не превысит ли сумма целевую
            if goal.current_amount + amount > goal.target_amount:
                raise serializers.ValidationError({
                    'amount': f"Сумма {amount} превысит целевую сумму. "
                             f"Осталось внести: {goal.remaining_amount}"
                })
        
        return data


class GoalProgressSerializer(serializers.Serializer):
    """Сериализатор для добавления прогресса к цели"""
    
    amount = serializers.DecimalField(max_digits=15, decimal_places=2)
    description = serializers.CharField(max_length=500, required=False, allow_blank=True)
    
    def validate_amount(self, value):
        """Валидация суммы"""
        if value <= Decimal('0'):
            raise serializers.ValidationError("Сумма должна быть больше нуля")
        if value > Decimal('999999999999.99'):
            raise serializers.ValidationError("Сумма слишком большая")
        return value
    
    def validate(self, data):
        """Кросс-валидация с учетом цели"""
        goal = self.context.get('goal')
        amount = data.get('amount')
        
        if goal and amount:
            if not goal.is_active:
                raise serializers.ValidationError("Нельзя добавлять прогресс к неактивной цели")
            
            if goal.current_amount + amount > goal.target_amount:
                raise serializers.ValidationError({
                    'amount': f"Сумма {amount} превысит целевую сумму. "
                             f"Осталось внести: {goal.remaining_amount}"
                })
        
        return data


class GoalStatsSerializer(serializers.Serializer):
    """Сериализатор для статистики целей пользователя"""
    
    total_goals = serializers.IntegerField(read_only=True)
    active_goals = serializers.IntegerField(read_only=True)
    completed_goals = serializers.IntegerField(read_only=True)
    failed_goals = serializers.IntegerField(read_only=True)
    paused_goals = serializers.IntegerField(read_only=True)
    total_target_amount = serializers.DecimalField(max_digits=15, decimal_places=2, read_only=True)
    total_saved_amount = serializers.DecimalField(max_digits=15, decimal_places=2, read_only=True)
    average_progress_percentage = serializers.FloatField(read_only=True)
    overdue_goals_count = serializers.IntegerField(read_only=True)
    
    # Последние цели
    recent_goals = GoalSerializer(many=True, read_only=True)
    
    # Статистика за период
    this_month_saved = serializers.DecimalField(max_digits=15, decimal_places=2, read_only=True)
    this_year_saved = serializers.DecimalField(max_digits=15, decimal_places=2, read_only=True)


# Дополнительные сериализаторы для специфических операций

class GoalCompleteSerializer(serializers.Serializer):
    """Сериализатор для завершения цели"""
    
    force = serializers.BooleanField(default=False)
    reason = serializers.CharField(max_length=500, required=False, allow_blank=True)


class GoalStatusUpdateSerializer(serializers.Serializer):
    """Сериализатор для обновления статуса цели"""
    
    status = serializers.ChoiceField(choices=Goal.STATUS_CHOICES)
    reason = serializers.CharField(max_length=500, required=False, allow_blank=True)
    
    def validate_status(self, value):
        """Валидация нового статуса"""
        goal = self.context.get('goal')
        if goal:
            current_status = goal.status
            
            # Логика переходов между статусами
            valid_transitions = {
                'active': ['completed', 'failed', 'paused'],
                'paused': ['active', 'failed'],
                'completed': [],  # Завершенную цель нельзя изменить
                'failed': ['active']  # Можно попробовать возобновить
            }
            
            if current_status not in valid_transitions:
                raise serializers.ValidationError(f"Неизвестный текущий статус: {current_status}")
            
            if value not in valid_transitions[current_status]:
                raise serializers.ValidationError(
                    f"Нельзя изменить статус с '{current_status}' на '{value}'"
                )
        
        return value 