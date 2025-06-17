from rest_framework import serializers
from decimal import Decimal
from django.utils import timezone
from apps.goals.models import Goal


class GoalSerializer(serializers.ModelSerializer):
    user_phone = serializers.CharField(source='user.phone_number', read_only=True)
    progress_percentage = serializers.FloatField(read_only=True)
    remaining_amount = serializers.DecimalField(max_digits=15, decimal_places=2, read_only=True)
    is_overdue = serializers.BooleanField(read_only=True)
    
    class Meta:
        model = Goal
        fields = [
            'id', 'user', 'user_phone', 'title', 'target_amount', 'current_amount',
            'deadline', 'reminder_interval', 'is_completed', 'progress_percentage',
            'remaining_amount', 'is_overdue', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'created_at', 'updated_at', 'user_phone', 'progress_percentage',
            'remaining_amount', 'is_overdue'
        ]
    
    def validate_target_amount(self, value):
        if value <= Decimal('0'):
            raise serializers.ValidationError("Целевая сумма должна быть больше нуля")
        if value > Decimal('999999999999.99'):
            raise serializers.ValidationError("Целевая сумма слишком большая")
        return value
    
    def validate_current_amount(self, value):
        if value < Decimal('0'):
            raise serializers.ValidationError("Текущая сумма не может быть отрицательной")
        return value
    
    def validate_deadline(self, value):
        if value <= timezone.now().date():
            raise serializers.ValidationError("Дата цели должна быть в будущем")
        return value
    
    def validate_title(self, value):
        if len(value.strip()) < 3:
            raise serializers.ValidationError("Название цели должно содержать минимум 3 символа")
        return value.strip()
    
    def validate(self, data):
        target_amount = data.get('target_amount')
        current_amount = data.get('current_amount', Decimal('0'))
        
        if target_amount and current_amount > target_amount:
            raise serializers.ValidationError(
                "Текущая сумма не может превышать целевую сумму"
            )
        
        return data 