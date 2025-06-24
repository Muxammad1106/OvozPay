from rest_framework import serializers
from apps.bot.models import VoiceCommand, BotSession


class VoiceCommandLogSerializer(serializers.ModelSerializer):
    user_phone = serializers.CharField(source='user.phone_number', read_only=True)
    
    class Meta:
        model = VoiceCommand
        fields = [
            'id', 'user', 'user_phone', 'transcription', 'duration_seconds',
            'command_type', 'status', 'processing_time',
            'error_message', 'extracted_amount',
            'created_transaction_id', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'user_phone', 'created_at', 'updated_at'
        ]
    
    def validate_transcription(self, value):
        if value and len(value.strip()) < 1:
            raise serializers.ValidationError("Текст команды не может быть пустым")
        return value.strip() if value else value


class BotSessionSerializer(serializers.ModelSerializer):
    user_phone = serializers.CharField(source='user.phone_number', read_only=True)
    duration_minutes = serializers.FloatField(read_only=True)
    
    class Meta:
        model = BotSession
        fields = [
            'id', 'user', 'user_phone', 'state', 'context_data',
            'is_active', 'last_activity', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'user_phone', 'created_at', 'updated_at'
        ] 