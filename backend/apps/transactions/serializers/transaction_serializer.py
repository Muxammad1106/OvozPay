from rest_framework import serializers
from decimal import Decimal
from apps.transactions.models import Transaction, Debt


class TransactionSerializer(serializers.ModelSerializer):
    user_phone = serializers.CharField(source='user.phone_number', read_only=True)
    category_name = serializers.CharField(source='category.name', read_only=True)
    
    class Meta:
        model = Transaction
        fields = [
            'id', 'user', 'user_phone', 'amount', 'category', 'category_name',
            'type', 'description', 'date', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'user_phone', 'category_name']
    
    def validate_amount(self, value):
        if value <= Decimal('0'):
            raise serializers.ValidationError("Сумма должна быть больше нуля")
        if value > Decimal('999999999999.99'):
            raise serializers.ValidationError("Сумма слишком большая")
        return value


class DebtSerializer(serializers.ModelSerializer):
    user_phone = serializers.CharField(source='user.phone_number', read_only=True)
    is_overdue = serializers.BooleanField(read_only=True)
    
    class Meta:
        model = Debt
        fields = [
            'id', 'user', 'user_phone', 'amount', 'debtor_name', 'direction',
            'date', 'description', 'status', 'is_overdue', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'user_phone', 'is_overdue']
    
    def validate_amount(self, value):
        if value <= Decimal('0'):
            raise serializers.ValidationError("Сумма долга должна быть больше нуля")
        if value > Decimal('999999999999.99'):
            raise serializers.ValidationError("Сумма долга слишком большая")
        return value
    
    def validate_debtor_name(self, value):
        if len(value.strip()) < 2:
            raise serializers.ValidationError("Имя должника должно содержать минимум 2 символа")
        return value.strip() 