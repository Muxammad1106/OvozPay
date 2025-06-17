from rest_framework import serializers
from decimal import Decimal
from apps.analytics.models import Report, Balance


class ReportSerializer(serializers.ModelSerializer):
    user_phone = serializers.CharField(source='user.phone_number', read_only=True)
    profit = serializers.DecimalField(max_digits=15, decimal_places=2, read_only=True)
    savings_rate = serializers.FloatField(read_only=True)
    
    class Meta:
        model = Report
        fields = [
            'id', 'user', 'user_phone', 'period_start', 'period_end',
            'total_income', 'total_expense', 'profit', 'savings_rate',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'created_at', 'updated_at', 'user_phone', 
            'profit', 'savings_rate'
        ]
    
    def validate(self, data):
        period_start = data.get('period_start')
        period_end = data.get('period_end')
        
        if period_start and period_end and period_start >= period_end:
            raise serializers.ValidationError(
                "Начальная дата должна быть раньше конечной"
            )
        
        return data


class BalanceSerializer(serializers.ModelSerializer):
    user_phone = serializers.CharField(source='user.phone_number', read_only=True)
    
    class Meta:
        model = Balance
        fields = [
            'id', 'user', 'user_phone', 'amount', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'user_phone'] 