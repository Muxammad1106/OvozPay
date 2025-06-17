"""
Сериализаторы для AI API
"""

from rest_framework import serializers
from apps.ai.models import OCRResult, OCRItem, VoiceResult, VoiceCommand, ReceiptVoiceMatch


class OCRItemSerializer(serializers.ModelSerializer):
    """Сериализатор для позиций чека"""
    
    class Meta:
        model = OCRItem
        fields = [
            'id', 'name', 'quantity', 'price', 'total_price',
            'category', 'category_confidence', 'line_number'
        ]
        read_only_fields = ['id']


class OCRResultSerializer(serializers.ModelSerializer):
    """Сериализатор для результатов OCR"""
    
    items = OCRItemSerializer(many=True, read_only=True)
    items_count = serializers.ReadOnlyField()
    is_completed = serializers.ReadOnlyField()
    
    class Meta:
        model = OCRResult
        fields = [
            'id', 'original_filename', 'raw_text', 'processed_text',
            'confidence_score', 'shop_name', 'receipt_date', 'receipt_number',
            'total_amount', 'status', 'error_message', 'processing_time',
            'language_detected', 'items_count', 'is_completed', 'items',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'raw_text', 'processed_text', 'confidence_score',
            'shop_name', 'receipt_date', 'receipt_number', 'total_amount',
            'status', 'error_message', 'processing_time', 'language_detected',
            'items_count', 'is_completed', 'items', 'created_at', 'updated_at'
        ]


class VoiceCommandSerializer(serializers.ModelSerializer):
    """Сериализатор для голосовых команд"""
    
    class Meta:
        model = VoiceCommand
        fields = [
            'id', 'command_type', 'command_text', 'extracted_params',
            'execution_status', 'execution_result', 'execution_error',
            'executed_at', 'confidence_score', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'command_type', 'command_text', 'extracted_params',
            'execution_status', 'execution_result', 'execution_error',
            'executed_at', 'confidence_score', 'created_at', 'updated_at'
        ]


class VoiceResultSerializer(serializers.ModelSerializer):
    """Сериализатор для результатов распознавания голоса"""
    
    command = VoiceCommandSerializer(read_only=True)
    is_completed = serializers.ReadOnlyField()
    
    class Meta:
        model = VoiceResult
        fields = [
            'id', 'original_filename', 'audio_format', 'audio_size',
            'language_code', 'recognition_task', 'recognized_text',
            'confidence_score', 'detected_language', 'segments_count',
            'processing_metadata', 'status', 'error_message',
            'is_completed', 'command', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'recognized_text', 'confidence_score', 'detected_language',
            'segments_count', 'processing_metadata', 'status', 'error_message',
            'is_completed', 'command', 'created_at', 'updated_at'
        ]


class ReceiptVoiceMatchSerializer(serializers.ModelSerializer):
    """Сериализатор для сопоставления голоса с чеками"""
    
    voice_result = VoiceResultSerializer(read_only=True)
    ocr_result = OCRResultSerializer(read_only=True)
    is_high_confidence = serializers.ReadOnlyField()
    matched_items_count = serializers.ReadOnlyField()
    amount_difference = serializers.ReadOnlyField()
    amount_match_percentage = serializers.ReadOnlyField()
    
    class Meta:
        model = ReceiptVoiceMatch
        fields = [
            'id', 'voice_result', 'ocr_result', 'confidence_score',
            'voice_items', 'total_amount_voice', 'receipt_items',
            'total_amount_receipt', 'matched_items', 'matching_details',
            'status', 'error_message', 'time_difference_minutes',
            'is_high_confidence', 'matched_items_count', 'amount_difference',
            'amount_match_percentage', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'confidence_score', 'voice_items', 'total_amount_voice',
            'receipt_items', 'total_amount_receipt', 'matched_items',
            'matching_details', 'status', 'error_message',
            'time_difference_minutes', 'is_high_confidence',
            'matched_items_count', 'amount_difference',
            'amount_match_percentage', 'created_at', 'updated_at'
        ]


class ReceiptVoiceMatchCreateSerializer(serializers.Serializer):
    """Сериализатор для создания сопоставления"""
    
    voice_result_id = serializers.UUIDField()
    ocr_result_id = serializers.UUIDField()
    
    def validate(self, attrs):
        """Валидация данных"""
        user = self.context['request'].user
        
        # Проверяем существование voice_result
        try:
            voice_result = VoiceResult.objects.get(
                id=attrs['voice_result_id'],
                user=user
            )
        except VoiceResult.DoesNotExist:
            raise serializers.ValidationError({
                'voice_result_id': 'Результат распознавания голоса не найден'
            })
        
        # Проверяем существование ocr_result  
        try:
            ocr_result = OCRResult.objects.get(
                id=attrs['ocr_result_id'],
                user=user
            )
        except OCRResult.DoesNotExist:
            raise serializers.ValidationError({
                'ocr_result_id': 'Результат OCR не найден'
            })
        
        # Проверяем, что оба результата завершены
        if voice_result.status != 'completed':
            raise serializers.ValidationError({
                'voice_result_id': 'Распознавание голоса не завершено'
            })
        
        if ocr_result.status != 'completed':
            raise serializers.ValidationError({
                'ocr_result_id': 'OCR обработка не завершена'
            })
        
        attrs['voice_result'] = voice_result
        attrs['ocr_result'] = ocr_result
        
        return attrs


class AutoMatchSerializer(serializers.Serializer):
    """Сериализатор для автоматического сопоставления"""
    
    voice_result_id = serializers.UUIDField()
    time_window_minutes = serializers.IntegerField(default=5, min_value=1, max_value=60)
    
    def validate_voice_result_id(self, value):
        """Валидация voice_result_id"""
        user = self.context['request'].user
        
        try:
            voice_result = VoiceResult.objects.get(id=value, user=user)
        except VoiceResult.DoesNotExist:
            raise serializers.ValidationError(
                'Результат распознавания голоса не найден'
            )
        
        if voice_result.status != 'completed':
            raise serializers.ValidationError(
                'Распознавание голоса не завершено'
            )
        
        return value


class ProcessingStatusSerializer(serializers.Serializer):
    """Сериализатор для статуса обработки"""
    
    # OCR Status
    tesseract_available = serializers.BooleanField(required=False)
    supported_languages = serializers.ListField(required=False)
    language_config = serializers.CharField(required=False)
    psm_modes = serializers.DictField(required=False)
    
    # Voice Status
    whisper_available = serializers.BooleanField(required=False)
    current_model = serializers.CharField(required=False)
    supported_formats = serializers.ListField(required=False)
    available_models = serializers.DictField(required=False)
    model_loaded = serializers.BooleanField(required=False)
    
    # Receipt-Voice Matching Status
    max_time_diff_minutes = serializers.IntegerField(required=False)
    similarity_threshold = serializers.FloatField(required=False)
    item_keywords = serializers.DictField(required=False)
    amount_keywords = serializers.DictField(required=False) 