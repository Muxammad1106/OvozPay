from rest_framework import serializers
from django.utils import timezone
from apps.broadcast.models import BroadcastMessage, BroadcastUserLog


class BroadcastMessageSerializer(serializers.ModelSerializer):
    total_recipients = serializers.IntegerField(read_only=True)
    success_rate = serializers.FloatField(read_only=True)
    
    class Meta:
        model = BroadcastMessage
        fields = [
            'id', 'title', 'body', 'send_at', 'status', 'target_audience',
            'sent_count', 'failed_count', 'total_recipients', 'success_rate',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'sent_count', 'failed_count', 'total_recipients', 
            'success_rate', 'created_at', 'updated_at'
        ]
    
    def validate_title(self, value):
        if len(value.strip()) < 3:
            raise serializers.ValidationError("Заголовок должен содержать минимум 3 символа")
        return value.strip()
    
    def validate_body(self, value):
        if len(value.strip()) < 10:
            raise serializers.ValidationError("Текст сообщения должен содержать минимум 10 символов")
        return value.strip()
    
    def validate_send_at(self, value):
        if value and value < timezone.now():
            raise serializers.ValidationError("Время отправки не может быть в прошлом")
        return value


class BroadcastUserLogSerializer(serializers.ModelSerializer):
    message_title = serializers.CharField(source='message.title', read_only=True)
    user_phone = serializers.CharField(source='user.phone_number', read_only=True)
    delivery_time = serializers.DurationField(read_only=True)
    
    class Meta:
        model = BroadcastUserLog
        fields = [
            'id', 'message', 'message_title', 'user', 'user_phone', 'status',
            'sent_at', 'error_message', 'read_at', 'delivery_time',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'message_title', 'user_phone', 'delivery_time',
            'created_at', 'updated_at'
        ] 