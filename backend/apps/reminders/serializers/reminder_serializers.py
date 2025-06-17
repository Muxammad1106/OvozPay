"""
Сериализаторы для модуля напоминаний и планировщика OvozPay
Этап 7: Reminders & Scheduler API
"""

from rest_framework import serializers
from django.utils import timezone
from django.core.exceptions import ValidationError
from apps.reminders.models import Reminder, ReminderHistory
from apps.goals.models import Goal


class ReminderSerializer(serializers.ModelSerializer):
    """Основной сериализатор для напоминаний"""
    
    # Вычисляемые поля
    is_overdue = serializers.ReadOnlyField()
    is_upcoming = serializers.ReadOnlyField()
    time_until_reminder = serializers.SerializerMethodField()
    reminder_type_display = serializers.CharField(source='get_reminder_type_display', read_only=True)
    repeat_display = serializers.CharField(source='get_repeat_display', read_only=True)
    
    # Дополнительные поля
    goal_title = serializers.CharField(source='goal.title', read_only=True)
    user_phone = serializers.CharField(source='user.phone_number', read_only=True)
    
    class Meta:
        model = Reminder
        fields = [
            'id', 'title', 'description', 'reminder_type', 'reminder_type_display',
            'scheduled_time', 'repeat', 'repeat_display', 'is_active', 'amount',
            'goal', 'goal_title', 'last_sent', 'next_reminder', 'telegram_notified',
            'created_at', 'updated_at', 'user_phone',
            # Вычисляемые поля
            'is_overdue', 'is_upcoming', 'time_until_reminder'
        ]
        read_only_fields = [
            'id', 'last_sent', 'next_reminder', 'telegram_notified', 
            'created_at', 'updated_at', 'user_phone'
        ]
    
    def get_time_until_reminder(self, obj):
        """Возвращает время до напоминания в секундах"""
        time_delta = obj.time_until_reminder
        if time_delta:
            return int(time_delta.total_seconds())
        return None
    
    def validate_scheduled_time(self, value):
        """Валидация времени напоминания"""
        if value < timezone.now():
            raise serializers.ValidationError(
                "Время напоминания не может быть в прошлом"
            )
        return value
    
    def validate_amount(self, value):
        """Валидация суммы"""
        if value is not None and value <= 0:
            raise serializers.ValidationError(
                "Сумма должна быть положительной"
            )
        return value
    
    def validate(self, data):
        """Кросс-валидация полей"""
        reminder_type = data.get('reminder_type')
        amount = data.get('amount')
        goal = data.get('goal')
        
        # Проверка суммы для платежей и долгов
        if reminder_type in ['payment', 'debt'] and not amount:
            raise serializers.ValidationError({
                'amount': 'Для напоминания о платеже/долге необходимо указать сумму'
            })
        
        # Проверка цели для напоминаний о целях
        if reminder_type == 'goal' and not goal:
            raise serializers.ValidationError({
                'goal': 'Для напоминания о цели необходимо указать цель'
            })
        
        # Проверка принадлежности цели пользователю
        if goal and hasattr(self, 'context') and self.context.get('request'):
            user = self.context['request'].user
            if goal.user != user:
                raise serializers.ValidationError({
                    'goal': 'Вы можете создавать напоминания только для своих целей'
                })
        
        return data


class ReminderCreateSerializer(serializers.ModelSerializer):
    """Сериализатор для создания напоминаний"""
    
    class Meta:
        model = Reminder
        fields = [
            'title', 'description', 'reminder_type', 'scheduled_time',
            'repeat', 'amount', 'goal'
        ]
    
    def validate_scheduled_time(self, value):
        """Валидация времени напоминания"""
        if value < timezone.now():
            raise serializers.ValidationError(
                "Время напоминания не может быть в прошлом"
            )
        return value
    
    def validate_amount(self, value):
        """Валидация суммы"""
        if value is not None and value <= 0:
            raise serializers.ValidationError(
                "Сумма должна быть положительной"
            )
        return value
    
    def validate(self, data):
        """Кросс-валидация полей"""
        reminder_type = data.get('reminder_type')
        amount = data.get('amount')
        goal = data.get('goal')
        
        # Проверка суммы для платежей и долгов
        if reminder_type in ['payment', 'debt'] and not amount:
            raise serializers.ValidationError({
                'amount': 'Для напоминания о платеже/долге необходимо указать сумму'
            })
        
        # Проверка цели для напоминаний о целях
        if reminder_type == 'goal' and not goal:
            raise serializers.ValidationError({
                'goal': 'Для напоминания о цели необходимо указать цель'
            })
        
        # Проверка принадлежности цели пользователю
        if goal and hasattr(self, 'context') and self.context.get('request'):
            user = self.context['request'].user
            if goal.user != user:
                raise serializers.ValidationError({
                    'goal': 'Вы можете создавать напоминания только для своих целей'
                })
        
        return data
    
    def create(self, validated_data):
        """Создание напоминания с привязкой к пользователю"""
        user = self.context['request'].user
        validated_data['user'] = user
        return super().create(validated_data)


class ReminderUpdateSerializer(serializers.ModelSerializer):
    """Сериализатор для обновления напоминаний"""
    
    class Meta:
        model = Reminder
        fields = [
            'title', 'description', 'reminder_type', 'scheduled_time',
            'repeat', 'amount', 'goal', 'is_active'
        ]
    
    def validate_scheduled_time(self, value):
        """Валидация времени напоминания"""
        # Для обновления разрешаем время в прошлом (если уже было)
        instance = getattr(self, 'instance', None)
        if not instance and value < timezone.now():
            raise serializers.ValidationError(
                "Время напоминания не может быть в прошлом"
            )
        return value
    
    def validate_amount(self, value):
        """Валидация суммы"""
        if value is not None and value <= 0:
            raise serializers.ValidationError(
                "Сумма должна быть положительной"
            )
        return value
    
    def validate(self, data):
        """Кросс-валидация полей"""
        # Получаем текущие значения из instance
        instance = getattr(self, 'instance', None)
        if instance:
            reminder_type = data.get('reminder_type', instance.reminder_type)
            amount = data.get('amount', instance.amount)
            goal = data.get('goal', instance.goal)
        else:
            reminder_type = data.get('reminder_type')
            amount = data.get('amount')
            goal = data.get('goal')
        
        # Проверка суммы для платежей и долгов
        if reminder_type in ['payment', 'debt'] and not amount:
            raise serializers.ValidationError({
                'amount': 'Для напоминания о платеже/долге необходимо указать сумму'
            })
        
        # Проверка цели для напоминаний о целях
        if reminder_type == 'goal' and not goal:
            raise serializers.ValidationError({
                'goal': 'Для напоминания о цели необходимо указать цель'
            })
        
        return data


class ReminderListSerializer(serializers.ModelSerializer):
    """Сериализатор для списка напоминаний (упрощенный)"""
    
    reminder_type_display = serializers.CharField(source='get_reminder_type_display', read_only=True)
    repeat_display = serializers.CharField(source='get_repeat_display', read_only=True)
    is_overdue = serializers.ReadOnlyField()
    is_upcoming = serializers.ReadOnlyField()
    goal_title = serializers.CharField(source='goal.title', read_only=True)
    
    class Meta:
        model = Reminder
        fields = [
            'id', 'title', 'reminder_type', 'reminder_type_display',
            'scheduled_time', 'repeat', 'repeat_display', 'is_active',
            'amount', 'goal_title', 'next_reminder',
            'is_overdue', 'is_upcoming', 'created_at'
        ]


class ReminderHistorySerializer(serializers.ModelSerializer):
    """Сериализатор для истории напоминаний"""
    
    reminder_title = serializers.CharField(source='reminder.title', read_only=True)
    reminder_type = serializers.CharField(source='reminder.reminder_type', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    user_phone = serializers.CharField(source='user.phone_number', read_only=True)
    
    class Meta:
        model = ReminderHistory
        fields = [
            'id', 'reminder', 'reminder_title', 'reminder_type',
            'sent_at', 'status', 'status_display', 'telegram_message_id',
            'error_message', 'user_phone', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class ReminderStatsSerializer(serializers.Serializer):
    """Сериализатор для статистики напоминаний"""
    
    total_reminders = serializers.IntegerField()
    active_reminders = serializers.IntegerField()
    inactive_reminders = serializers.IntegerField()
    overdue_reminders = serializers.IntegerField()
    upcoming_reminders = serializers.IntegerField()
    
    # Статистика по типам
    payment_reminders = serializers.IntegerField()
    debt_reminders = serializers.IntegerField()
    goal_reminders = serializers.IntegerField()
    custom_reminders = serializers.IntegerField()
    
    # Статистика по периодичности
    once_reminders = serializers.IntegerField()
    daily_reminders = serializers.IntegerField()
    weekly_reminders = serializers.IntegerField()
    monthly_reminders = serializers.IntegerField()
    
    # Статистика отправки
    total_sent = serializers.IntegerField()
    sent_today = serializers.IntegerField()
    sent_this_week = serializers.IntegerField()
    sent_this_month = serializers.IntegerField()


class ReminderTypesSerializer(serializers.Serializer):
    """Сериализатор для списка доступных типов напоминаний"""
    
    reminder_types = serializers.ListField(
        child=serializers.DictField(),
        read_only=True
    )
    repeat_types = serializers.ListField(
        child=serializers.DictField(),
        read_only=True
    )


class ReminderActivationSerializer(serializers.Serializer):
    """Сериализатор для активации/деактивации напоминаний"""
    
    is_active = serializers.BooleanField()
    message = serializers.CharField(read_only=True)


class ReminderSendNowSerializer(serializers.Serializer):
    """Сериализатор для отправки напоминания вручную"""
    
    message = serializers.CharField(read_only=True)
    telegram_message_id = serializers.IntegerField(read_only=True, allow_null=True)
    sent_at = serializers.DateTimeField(read_only=True) 