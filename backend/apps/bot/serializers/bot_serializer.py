from rest_framework import serializers
from apps.bot.models import VoiceCommandLog, BotSession


class VoiceCommandLogSerializer(serializers.ModelSerializer):
    user_phone = serializers.CharField(source='user.phone_number', read_only=True)
    
    class Meta:
        model = VoiceCommandLog
        fields = [
            'id', 'user', 'user_phone', 'text', 'original_audio_duration',
            'command_type', 'status', 'confidence_score', 'processing_time',
            'error_message', 'extracted_amount', 'extracted_currency',
            'created_transaction_id', 'received_at', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'user_phone', 'created_at', 'updated_at'
        ]
    
    def validate_text(self, value):
        if len(value.strip()) < 1:
            raise serializers.ValidationError("Текст команды не может быть пустым")
        return value.strip()
    
    def validate_confidence_score(self, value):
        if value is not None and (value < 0 or value > 1):
            raise serializers.ValidationError("Уверенность должна быть от 0 до 1")
        return value


class BotSessionSerializer(serializers.ModelSerializer):
    user_phone = serializers.CharField(source='user.phone_number', read_only=True)
    duration_minutes = serializers.FloatField(read_only=True)
    
    class Meta:
        model = BotSession
        fields = [
            'id', 'user', 'user_phone', 'telegram_chat_id', 'session_type',
            'is_active', 'started_at', 'ended_at', 'messages_count',
            'voice_messages_count', 'commands_executed', 'last_activity_at',
            'duration_minutes', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'user_phone', 'duration_minutes', 'created_at', 'updated_at'
        ] 