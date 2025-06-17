"""
Сериализаторы для AI модуля OvozPay
OCR, Voice Recognition, Command Processing
"""

from rest_framework import serializers
from django.core.files.uploadedfile import UploadedFile

from apps.ai.models import (
    OCRResult, OCRItem, VoiceResult, VoiceCommand, AIProcessingLog
)
from apps.categories.serializers import CategorySerializer


class OCRItemSerializer(serializers.ModelSerializer):
    """Сериализатор для позиций чека OCR"""
    
    category_name = serializers.CharField(source='category.name', read_only=True)
    
    class Meta:
        model = OCRItem
        fields = [
            'id', 'name', 'quantity', 'unit_price', 'total_price',
            'category', 'category_name', 'category_confidence',
            'line_number', 'raw_text_line'
        ]
        read_only_fields = ['id']


class OCRResultSerializer(serializers.ModelSerializer):
    """Сериализатор для результатов OCR"""
    
    items = OCRItemSerializer(many=True, read_only=True)
    items_count = serializers.ReadOnlyField()
    is_completed = serializers.ReadOnlyField()
    user_phone = serializers.CharField(source='user.phone_number', read_only=True)
    
    class Meta:
        model = OCRResult
        fields = [
            'id', 'user', 'user_phone', 'image_file', 'original_filename',
            'raw_text', 'processed_text', 'confidence_score',
            'shop_name', 'receipt_date', 'receipt_number', 'total_amount',
            'status', 'error_message', 'processing_time', 'language_detected',
            'items', 'items_count', 'is_completed', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'user', 'raw_text', 'processed_text', 'confidence_score',
            'shop_name', 'receipt_date', 'receipt_number', 'total_amount',
            'status', 'error_message', 'processing_time', 'language_detected',
            'items', 'items_count', 'is_completed', 'created_at', 'updated_at'
        ]


class OCRUploadSerializer(serializers.Serializer):
    """Сериализатор для загрузки изображения OCR"""
    
    image = serializers.ImageField(
        required=True,
        help_text="Изображение чека для OCR обработки"
    )
    recognition_type = serializers.ChoiceField(
        choices=['receipt', 'document', 'general'],
        default='receipt',
        help_text="Тип распознавания"
    )
    
    def validate_image(self, value: UploadedFile):
        """Валидация изображения"""
        from apps.ai.services.ocr.tesseract_service import TesseractOCRService
        
        ocr_service = TesseractOCRService()
        is_valid, error_message = ocr_service.validate_image(value)
        
        if not is_valid:
            raise serializers.ValidationError(error_message)
        
        return value


class VoiceCommandSerializer(serializers.ModelSerializer):
    """Сериализатор для голосовых команд"""
    
    user_phone = serializers.CharField(source='voice_result.user.phone_number', read_only=True)
    recognized_text = serializers.CharField(source='voice_result.recognized_text', read_only=True)
    
    class Meta:
        model = VoiceCommand
        fields = [
            'id', 'voice_result', 'user_phone', 'recognized_text',
            'command_type', 'command_text', 'extracted_params',
            'execution_status', 'execution_result', 'execution_error',
            'executed_at', 'confidence_score', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'voice_result', 'user_phone', 'recognized_text',
            'command_type', 'command_text', 'extracted_params',
            'execution_status', 'execution_result', 'execution_error',
            'executed_at', 'confidence_score', 'created_at', 'updated_at'
        ]


class VoiceResultSerializer(serializers.ModelSerializer):
    """Сериализатор для результатов распознавания голоса"""
    
    command = VoiceCommandSerializer(read_only=True)
    user_phone = serializers.CharField(source='user.phone_number', read_only=True)
    is_completed = serializers.ReadOnlyField()
    duration_formatted = serializers.SerializerMethodField()
    
    class Meta:
        model = VoiceResult
        fields = [
            'id', 'user', 'user_phone', 'audio_file', 'original_filename',
            'duration', 'duration_formatted', 'recognized_text',
            'confidence_score', 'language_detected', 'recognition_type',
            'status', 'error_message', 'ocr_result', 'processing_time',
            'model_used', 'command', 'is_completed', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'user', 'duration', 'recognized_text', 'confidence_score',
            'language_detected', 'status', 'error_message', 'processing_time',
            'model_used', 'command', 'is_completed', 'created_at', 'updated_at'
        ]
    
    def get_duration_formatted(self, obj):
        """Форматированная длительность"""
        if obj.duration:
            minutes = int(obj.duration // 60)
            seconds = int(obj.duration % 60)
            return f"{minutes}:{seconds:02d}"
        return "0:00"


class VoiceUploadSerializer(serializers.Serializer):
    """Сериализатор для загрузки аудио файла"""
    
    audio = serializers.FileField(
        required=True,
        help_text="Аудио файл для распознавания речи"
    )
    recognition_type = serializers.ChoiceField(
        choices=[
            ('expense_description', 'Описание расходов'),
            ('voice_command', 'Голосовая команда'),
            ('receipt_description', 'Описание чека'),
            ('general', 'Общее'),
        ],
        default='general',
        help_text="Тип распознавания"
    )
    ocr_result_id = serializers.UUIDField(
        required=False,
        help_text="ID результата OCR для связывания с голосовым описанием"
    )
    
    def validate_audio(self, value: UploadedFile):
        """Валидация аудио файла"""
        from apps.ai.services.voice.whisper_service import WhisperVoiceService
        
        voice_service = WhisperVoiceService()
        is_valid, error_message = voice_service.validate_audio_file(value)
        
        if not is_valid:
            raise serializers.ValidationError(error_message)
        
        return value
    
    def validate_ocr_result_id(self, value):
        """Валидация ID результата OCR"""
        if value:
            try:
                ocr_result = OCRResult.objects.get(id=value)
                # Проверяем, что OCR результат принадлежит текущему пользователю
                request = self.context.get('request')
                if request and ocr_result.user != request.user:
                    raise serializers.ValidationError(
                        "OCR result не принадлежит текущему пользователю"
                    )
                return value
            except OCRResult.DoesNotExist:
                raise serializers.ValidationError("OCR result не найден")
        return value


class AIProcessingLogSerializer(serializers.ModelSerializer):
    """Сериализатор для логов обработки AI"""
    
    user_phone = serializers.CharField(source='user.phone_number', read_only=True)
    ocr_result_id = serializers.UUIDField(source='ocr_result.id', read_only=True)
    voice_result_id = serializers.UUIDField(source='voice_result.id', read_only=True)
    
    class Meta:
        model = AIProcessingLog
        fields = [
            'id', 'user', 'user_phone', 'operation_type', 'level',
            'message', 'details', 'ocr_result_id', 'voice_result_id',
            'execution_time', 'memory_used', 'created_at'
        ]
        read_only_fields = '__all__'


class OCRAnalysisSerializer(serializers.Serializer):
    """Сериализатор для анализа OCR результатов"""
    
    categories = serializers.DictField(read_only=True)
    total_amount = serializers.DecimalField(max_digits=15, decimal_places=2, read_only=True)
    matched_items = serializers.IntegerField(read_only=True)
    unmatched_items = serializers.ListField(read_only=True)
    matching_rate = serializers.FloatField(read_only=True)
    suggestions = serializers.ListField(read_only=True)


class VoiceCommandResponseSerializer(serializers.Serializer):
    """Сериализатор для ответа на выполненную команду"""
    
    success = serializers.BooleanField()
    message = serializers.CharField()
    command_type = serializers.CharField(read_only=True)
    execution_time = serializers.FloatField(read_only=True)
    result_data = serializers.DictField(read_only=True)


class AIServiceStatusSerializer(serializers.Serializer):
    """Сериализатор для статуса AI сервисов"""
    
    ocr_available = serializers.BooleanField(read_only=True)
    voice_recognition_available = serializers.BooleanField(read_only=True)
    tesseract_version = serializers.CharField(read_only=True)
    whisper_model = serializers.CharField(read_only=True)
    supported_languages = serializers.ListField(read_only=True)
    supported_image_formats = serializers.ListField(read_only=True)
    supported_audio_formats = serializers.ListField(read_only=True)


class ReceiptMatchingSerializer(serializers.Serializer):
    """Сериализатор для сопоставления чека и голоса"""
    
    ocr_result_id = serializers.UUIDField(
        required=True,
        help_text="ID результата OCR"
    )
    voice_result_id = serializers.UUIDField(
        required=True,
        help_text="ID результата распознавания голоса"
    )
    
    def validate(self, data):
        """Валидация данных сопоставления"""
        request = self.context.get('request')
        if not request or not request.user:
            raise serializers.ValidationError("Пользователь не аутентифицирован")
        
        user = request.user
        
        # Проверяем OCR результат
        try:
            ocr_result = OCRResult.objects.get(id=data['ocr_result_id'])
            if ocr_result.user != user:
                raise serializers.ValidationError(
                    "OCR результат не принадлежит текущему пользователю"
                )
            if ocr_result.status != 'completed':
                raise serializers.ValidationError(
                    "OCR результат еще не обработан"
                )
        except OCRResult.DoesNotExist:
            raise serializers.ValidationError("OCR результат не найден")
        
        # Проверяем Voice результат
        try:
            voice_result = VoiceResult.objects.get(id=data['voice_result_id'])
            if voice_result.user != user:
                raise serializers.ValidationError(
                    "Voice результат не принадлежит текущему пользователю"
                )
            if voice_result.status != 'completed':
                raise serializers.ValidationError(
                    "Voice результат еще не обработан"
                )
        except VoiceResult.DoesNotExist:
            raise serializers.ValidationError("Voice результат не найден")
        
        return data


class SupportedCommandsSerializer(serializers.Serializer):
    """Сериализатор для поддерживаемых команд"""
    
    language = serializers.ChoiceField(
        choices=['ru', 'uz', 'en'],
        default='ru',
        help_text="Язык для примеров команд"
    )


class CommandListSerializer(serializers.Serializer):
    """Сериализатор для списка команд"""
    
    type = serializers.CharField(read_only=True)
    example = serializers.CharField(read_only=True)
    description = serializers.CharField(read_only=True)


class OCRItemUpdateSerializer(serializers.ModelSerializer):
    """Сериализатор для обновления позиций чека"""
    
    class Meta:
        model = OCRItem
        fields = ['category']
    
    def validate_category(self, value):
        """Валидация категории"""
        request = self.context.get('request')
        if value and request and value.user != request.user:
            raise serializers.ValidationError(
                "Категория не принадлежит текущему пользователю"
            )
        return value


class BulkReceiptProcessingSerializer(serializers.Serializer):
    """Сериализатор для массовой обработки чеков"""
    
    images = serializers.ListField(
        child=serializers.ImageField(),
        min_length=1,
        max_length=10,
        help_text="Список изображений чеков (максимум 10)"
    )
    recognition_type = serializers.ChoiceField(
        choices=['receipt', 'document', 'general'],
        default='receipt'
    )
    
    def validate_images(self, value):
        """Валидация списка изображений"""
        from apps.ai.services.ocr.tesseract_service import TesseractOCRService
        
        ocr_service = TesseractOCRService()
        
        for i, image in enumerate(value):
            is_valid, error_message = ocr_service.validate_image(image)
            if not is_valid:
                raise serializers.ValidationError(
                    f"Изображение {i+1}: {error_message}"
                )
        
        return value


class ReceiptStatsSerializer(serializers.Serializer):
    """Сериализатор для статистики по чекам"""
    
    period = serializers.ChoiceField(
        choices=['day', 'week', 'month', 'year'],
        default='month',
        help_text="Период для статистики"
    )
    
    def validate_period(self, value):
        """Валидация периода"""
        valid_periods = ['day', 'week', 'month', 'year']
        if value not in valid_periods:
            raise serializers.ValidationError(
                f"Период должен быть одним из: {', '.join(valid_periods)}"
            )
        return value 