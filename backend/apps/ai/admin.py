"""
Администрирование AI модуля
"""
from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe

from .models import (
    OCRResult, OCRItem, VoiceResult, VoiceCommand, AIProcessingLog
)


@admin.register(OCRResult)
class OCRResultAdmin(admin.ModelAdmin):
    """Администрирование результатов OCR"""
    
    list_display = [
        'id', 'user', 'shop_name', 'total_amount', 'status', 
        'confidence_score', 'items_count', 'created_at'
    ]
    list_filter = [
        'status', 'shop_name', 'created_at'
    ]
    search_fields = [
        'user__username', 'shop_name', 'recognized_text'
    ]
    readonly_fields = [
        'id', 'created_at', 'updated_at', 'processing_time',
        'image_preview', 'text_preview'
    ]
    
    fieldsets = (
        ('Основная информация', {
            'fields': ('user', 'status')
        }),
        ('Изображение', {
            'fields': ('image_file', 'image_preview')
        }),
        ('Результаты распознавания', {
            'fields': ('raw_text', 'processed_text', 'text_preview', 'confidence_score')
        }),
        ('Данные магазина', {
            'fields': ('shop_name', 'receipt_date', 'receipt_number')
        }),
        ('Суммы', {
            'fields': ('total_amount',)
        }),
        ('Техническая информация', {
            'fields': ('language_detected', 'processing_time', 'error_message')
        }),
        ('Временные метки', {
            'fields': ('created_at', 'updated_at')
        })
    )
    
    def image_preview(self, obj):
        """Превью изображения"""
        if obj.image_file:
            return format_html(
                '<img src="{}" style="max-width: 200px; max-height: 200px;" />',
                obj.image_file.url
            )
        return "Нет изображения"
    image_preview.short_description = "Превью"
    
    def text_preview(self, obj):
        """Превью распознанного текста"""
        text = obj.processed_text or obj.raw_text
        if text:
            preview = text[:200]
            if len(text) > 200:
                preview += "..."
            return format_html('<div style="max-width: 300px;">{}</div>', preview)
        return "Нет текста"
    text_preview.short_description = "Превью текста"
    
    def items_count(self, obj):
        """Количество товаров"""
        return obj.items.count()
    items_count.short_description = "Товаров"


@admin.register(OCRItem)
class OCRItemAdmin(admin.ModelAdmin):
    """Администрирование товаров из чеков"""
    
    list_display = [
        'id', 'ocr_result_link', 'name', 'quantity', 
        'unit_price', 'total_price', 'category', 'line_number'
    ]
    list_filter = [
        'category', 'ocr_result__shop_name', 'ocr_result__created_at'
    ]
    search_fields = [
        'name', 'category__name', 'ocr_result__shop_name'
    ]
    
    def ocr_result_link(self, obj):
        """Ссылка на результат OCR"""
        if obj.ocr_result:
            url = reverse('admin:ai_ocrresult_change', args=[obj.ocr_result.pk])
            return format_html('<a href="{}">{}</a>', url, obj.ocr_result.id)
        return "-"
    ocr_result_link.short_description = "OCR результат"


@admin.register(VoiceResult)
class VoiceResultAdmin(admin.ModelAdmin):
    """Администрирование результатов голосового распознавания"""
    
    list_display = [
        'id', 'user', 'recognition_type', 'language_detected',
        'confidence_score', 'status', 'duration', 'created_at'
    ]
    list_filter = [
        'status', 'recognition_type', 'language_detected', 'created_at'
    ]
    search_fields = [
        'user__username', 'recognized_text', 'original_filename'
    ]
    readonly_fields = [
        'id', 'created_at', 'updated_at', 'processing_time',
        'audio_player', 'text_preview'
    ]
    
    fieldsets = (
        ('Основная информация', {
            'fields': ('user', 'status', 'recognition_type')
        }),
        ('Аудио файл', {
            'fields': ('audio_file', 'audio_player', 'original_filename', 'duration')
        }),
        ('Результаты распознавания', {
            'fields': ('recognized_text', 'text_preview', 'confidence_score', 'language_detected')
        }),
        ('Техническая информация', {
            'fields': ('model_used', 'processing_time', 'error_message')
        }),
        ('Временные метки', {
            'fields': ('created_at', 'updated_at')
        })
    )
    
    def audio_player(self, obj):
        """Аудио плеер"""
        if obj.audio_file:
            return format_html(
                '<audio controls><source src="{}" type="audio/mpeg">Ваш браузер не поддерживает аудио.</audio>',
                obj.audio_file.url
            )
        return "Нет аудио"
    audio_player.short_description = "Плеер"
    
    def text_preview(self, obj):
        """Превью распознанного текста"""
        if obj.recognized_text:
            preview = obj.recognized_text[:150]
            if len(obj.recognized_text) > 150:
                preview += "..."
            return format_html('<div style="max-width: 300px;">{}</div>', preview)
        return "Нет текста"
    text_preview.short_description = "Превью текста"


@admin.register(VoiceCommand)
class VoiceCommandAdmin(admin.ModelAdmin):
    """Администрирование голосовых команд"""
    
    list_display = [
        'id', 'voice_result_link', 'command_type', 'execution_status',
        'created_at'
    ]
    list_filter = [
        'command_type', 'execution_status', 'created_at'
    ]
    search_fields = [
        'voice_result__user__phone_number', 'command_text'
    ]
    readonly_fields = [
        'id', 'created_at', 'updated_at', 'executed_at'
    ]
    
    fieldsets = (
        ('Основная информация', {
            'fields': ('voice_result', 'command_type', 'execution_status')
        }),
        ('Команда', {
            'fields': ('command_text', 'extracted_params')
        }),
        ('Результат выполнения', {
            'fields': ('execution_result', 'execution_error', 'executed_at')
        }),
        ('Временные метки', {
            'fields': ('created_at', 'updated_at')
        })
    )
    
    def voice_result_link(self, obj):
        """Ссылка на голосовой результат"""
        if obj.voice_result:
            url = reverse('admin:ai_voiceresult_change', args=[obj.voice_result.pk])
            return format_html('<a href="{}">{}</a>', url, obj.voice_result.id)
        return "-"
    voice_result_link.short_description = "Голосовой результат"


@admin.register(AIProcessingLog)
class AIProcessingLogAdmin(admin.ModelAdmin):
    """Администрирование логов обработки AI"""
    
    list_display = [
        'id', 'user', 'operation_type', 'level', 'message_preview', 'created_at'
    ]
    list_filter = [
        'operation_type', 'level', 'created_at'
    ]
    search_fields = [
        'user__phone_number', 'message', 'operation_type'
    ]
    readonly_fields = [
        'id', 'created_at', 'details_formatted'
    ]
    
    fieldsets = (
        ('Основная информация', {
            'fields': ('user', 'operation_type', 'level')
        }),
        ('Связанные объекты', {
            'fields': ('ocr_result', 'voice_result')
        }),
        ('Сообщение и детали', {
            'fields': ('message', 'details_formatted')
        }),
        ('Время', {
            'fields': ('created_at',)
        })
    )
    
    def message_preview(self, obj):
        """Превью сообщения"""
        if obj.message:
            preview = obj.message[:80]
            if len(obj.message) > 80:
                preview += "..."
            return preview
        return "Нет сообщения"
    message_preview.short_description = "Сообщение"
    
    def details_formatted(self, obj):
        """Форматированные детали"""
        if obj.details:
            import json
            try:
                formatted = json.dumps(obj.details, indent=2, ensure_ascii=False)
                return format_html('<pre style="max-width: 400px; white-space: pre-wrap;">{}</pre>', formatted)
            except:
                return str(obj.details)
        return "Нет деталей"
    details_formatted.short_description = "Детали" 