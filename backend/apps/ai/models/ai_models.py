"""
Модели для модуля AI интеграции OvozPay
OCR, Voice Recognition, NLP
"""

import uuid
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from apps.core.models import BaseModel


class OCRResult(BaseModel):
    """Модель результата OCR распознавания чека"""
    
    STATUS_CHOICES = [
        ('processing', 'Обрабатывается'),
        ('completed', 'Завершено'),
        ('failed', 'Ошибка'),
        ('pending_review', 'Требует проверки'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey('users.User', on_delete=models.CASCADE, related_name='ocr_results')
    
    # Исходные данные
    image_file = models.ImageField(upload_to='ocr/images/%Y/%m/', verbose_name='Изображение чека')
    original_filename = models.CharField(max_length=255, verbose_name='Исходное имя файла')
    
    # Результаты OCR
    raw_text = models.TextField(blank=True, verbose_name='Сырой текст OCR')
    processed_text = models.TextField(blank=True, verbose_name='Обработанный текст')
    confidence_score = models.FloatField(
        default=0.0, 
        validators=[MinValueValidator(0.0)],
        verbose_name='Уровень уверенности'
    )
    
    # Парсинг данных чека
    shop_name = models.CharField(max_length=255, blank=True, verbose_name='Название магазина')
    receipt_date = models.DateTimeField(blank=True, null=True, verbose_name='Дата чека')
    receipt_number = models.CharField(max_length=100, blank=True, verbose_name='Номер чека')
    total_amount = models.DecimalField(
        max_digits=15, 
        decimal_places=2, 
        default=0,
        verbose_name='Общая сумма'
    )
    
    # Статус обработки
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='processing',
        verbose_name='Статус обработки'
    )
    error_message = models.TextField(blank=True, verbose_name='Сообщение об ошибке')
    
    # Метаданные
    processing_time = models.FloatField(default=0.0, verbose_name='Время обработки (сек)')
    language_detected = models.CharField(max_length=10, blank=True, verbose_name='Определенный язык')
    
    class Meta:
        ordering = ('-created_at',)
        verbose_name = 'Результат OCR'
        verbose_name_plural = 'Результаты OCR'
        indexes = [
            models.Index(fields=['user', 'status']),
            models.Index(fields=['created_at', 'status']),
            models.Index(fields=['shop_name']),
        ]
    
    def __str__(self):
        return f"OCR {self.shop_name or 'Unknown'} - {self.user.phone_number}"
    
    @property
    def is_completed(self):
        """Проверяет, завершена ли обработка"""
        return self.status == 'completed'
    
    @property
    def items_count(self):
        """Возвращает количество позиций в чеке"""
        return self.items.count()


class OCRItem(BaseModel):
    """Модель позиции товара/услуги из чека"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    ocr_result = models.ForeignKey(
        OCRResult, 
        on_delete=models.CASCADE, 
        related_name='items',
        verbose_name='Результат OCR'
    )
    
    # Данные позиции
    name = models.CharField(max_length=500, verbose_name='Название товара/услуги')
    quantity = models.DecimalField(
        max_digits=10, 
        decimal_places=3, 
        default=1,
        verbose_name='Количество'
    )
    unit_price = models.DecimalField(
        max_digits=15, 
        decimal_places=2,
        default=0,
        verbose_name='Цена за единицу'
    )
    total_price = models.DecimalField(
        max_digits=15, 
        decimal_places=2,
        verbose_name='Общая стоимость'
    )
    
    # Категоризация
    category = models.ForeignKey(
        'categories.Category',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='Категория'
    )
    category_confidence = models.FloatField(
        default=0.0,
        validators=[MinValueValidator(0.0)],
        verbose_name='Уверенность в категории'
    )
    
    # Позиция в чеке
    line_number = models.PositiveIntegerField(default=1, verbose_name='Номер строки')
    raw_text_line = models.TextField(blank=True, verbose_name='Исходная строка текста')
    
    class Meta:
        ordering = ['line_number']
        verbose_name = 'Позиция чека'
        verbose_name_plural = 'Позиции чеков'
        indexes = [
            models.Index(fields=['ocr_result', 'line_number']),
            models.Index(fields=['category']),
        ]
    
    def __str__(self):
        return f"{self.name} - {self.total_price}"


class VoiceResult(BaseModel):
    """Модель результата распознавания голоса"""
    
    RECOGNITION_TYPE_CHOICES = [
        ('expense_description', 'Описание расходов'),
        ('voice_command', 'Голосовая команда'),
        ('receipt_description', 'Описание чека'),
        ('general', 'Общее'),
    ]
    
    STATUS_CHOICES = [
        ('processing', 'Обрабатывается'),
        ('completed', 'Завершено'),
        ('failed', 'Ошибка'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey('users.User', on_delete=models.CASCADE, related_name='voice_results')
    
    # Исходные данные
    audio_file = models.FileField(upload_to='voice/audio/%Y/%m/', verbose_name='Аудио файл')
    original_filename = models.CharField(max_length=255, verbose_name='Исходное имя файла')
    duration = models.FloatField(default=0.0, verbose_name='Длительность (сек)')
    
    # Результаты распознавания
    recognized_text = models.TextField(blank=True, verbose_name='Распознанный текст')
    confidence_score = models.FloatField(
        default=0.0,
        validators=[MinValueValidator(0.0)],
        verbose_name='Уровень уверенности'
    )
    language_detected = models.CharField(max_length=10, blank=True, verbose_name='Определенный язык')
    
    # Тип распознавания
    recognition_type = models.CharField(
        max_length=20,
        choices=RECOGNITION_TYPE_CHOICES,
        default='general',
        verbose_name='Тип распознавания'
    )
    
    # Статус обработки
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='processing',
        verbose_name='Статус обработки'
    )
    error_message = models.TextField(blank=True, verbose_name='Сообщение об ошибке')
    
    # Связанные объекты
    ocr_result = models.ForeignKey(
        OCRResult,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='voice_descriptions',
        verbose_name='Связанный OCR результат'
    )
    
    # Метаданные
    processing_time = models.FloatField(default=0.0, verbose_name='Время обработки (сек)')
    model_used = models.CharField(max_length=50, blank=True, verbose_name='Использованная модель')
    
    class Meta:
        ordering = ('-created_at',)
        verbose_name = 'Результат распознавания голоса'
        verbose_name_plural = 'Результаты распознавания голоса'
        indexes = [
            models.Index(fields=['user', 'status']),
            models.Index(fields=['recognition_type', 'status']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self):
        return f"Voice ({self.recognition_type}) - {self.user.phone_number}"
    
    @property
    def is_completed(self):
        """Проверяет, завершено ли распознавание"""
        return self.status == 'completed'


class VoiceCommand(BaseModel):
    """Модель распознанной голосовой команды"""
    
    COMMAND_TYPE_CHOICES = [
        ('create_category', 'Создать категорию'),
        ('add_expense', 'Добавить расход'),
        ('show_balance', 'Показать баланс'),
        ('delete_category', 'Удалить категорию'),
        ('manage_debt', 'Управление долгами'),
        ('show_stats', 'Показать статистику'),
        ('unknown', 'Неизвестная команда'),
    ]
    
    EXECUTION_STATUS_CHOICES = [
        ('pending', 'Ожидает выполнения'),
        ('executed', 'Выполнена'),
        ('failed', 'Ошибка выполнения'),
        ('cancelled', 'Отменена'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    voice_result = models.OneToOneField(
        VoiceResult,
        on_delete=models.CASCADE,
        related_name='command',
        verbose_name='Результат распознавания'
    )
    
    # Распознанная команда
    command_type = models.CharField(
        max_length=20,
        choices=COMMAND_TYPE_CHOICES,
        verbose_name='Тип команды'
    )
    command_text = models.TextField(verbose_name='Текст команды')
    
    # Параметры команды
    extracted_params = models.JSONField(
        default=dict,
        verbose_name='Извлеченные параметры'
    )
    
    # Выполнение команды
    execution_status = models.CharField(
        max_length=20,
        choices=EXECUTION_STATUS_CHOICES,
        default='pending',
        verbose_name='Статус выполнения'
    )
    execution_result = models.JSONField(
        default=dict,
        blank=True,
        verbose_name='Результат выполнения'
    )
    execution_error = models.TextField(blank=True, verbose_name='Ошибка выполнения')
    executed_at = models.DateTimeField(null=True, blank=True, verbose_name='Время выполнения')
    
    # Метаданные
    confidence_score = models.FloatField(
        default=0.0,
        validators=[MinValueValidator(0.0)],
        verbose_name='Уверенность в команде'
    )
    
    class Meta:
        ordering = ('-created_at',)
        verbose_name = 'Голосовая команда'
        verbose_name_plural = 'Голосовые команды'
        indexes = [
            models.Index(fields=['command_type', 'execution_status']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self):
        return f"{self.get_command_type_display()} - {self.voice_result.user.phone_number}"
    
    @property
    def user(self):
        """Возвращает пользователя команды"""
        return self.voice_result.user
    
    def mark_executed(self, result=None):
        """Отмечает команду как выполненную"""
        self.execution_status = 'executed'
        self.executed_at = timezone.now()
        if result:
            self.execution_result = result
        self.save()
    
    def mark_failed(self, error):
        """Отмечает команду как неудачную"""
        self.execution_status = 'failed'
        self.execution_error = str(error)
        self.executed_at = timezone.now()
        self.save()


class AIProcessingLog(BaseModel):
    """Модель логов обработки AI"""
    
    OPERATION_TYPE_CHOICES = [
        ('ocr_scan', 'OCR сканирование'),
        ('voice_recognition', 'Распознавание голоса'),
        ('nlp_analysis', 'NLP анализ'),
        ('command_execution', 'Выполнение команды'),
        ('category_matching', 'Сопоставление категорий'),
    ]
    
    LEVEL_CHOICES = [
        ('debug', 'Debug'),
        ('info', 'Info'),
        ('warning', 'Warning'),
        ('error', 'Error'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        'users.User', 
        on_delete=models.CASCADE, 
        related_name='ai_logs',
        verbose_name='Пользователь'
    )
    
    # Тип операции
    operation_type = models.CharField(
        max_length=20,
        choices=OPERATION_TYPE_CHOICES,
        verbose_name='Тип операции'
    )
    
    # Детали лога
    level = models.CharField(max_length=10, choices=LEVEL_CHOICES, verbose_name='Уровень')
    message = models.TextField(verbose_name='Сообщение')
    details = models.JSONField(default=dict, blank=True, verbose_name='Детали')
    
    # Связанные объекты
    ocr_result = models.ForeignKey(
        OCRResult,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='OCR результат'
    )
    voice_result = models.ForeignKey(
        VoiceResult,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='Voice результат'
    )
    
    # Производительность
    execution_time = models.FloatField(default=0.0, verbose_name='Время выполнения (сек)')
    memory_used = models.FloatField(default=0.0, verbose_name='Использовано памяти (MB)')
    
    class Meta:
        ordering = ('-created_at',)
        verbose_name = 'Лог AI обработки'
        verbose_name_plural = 'Логи AI обработки'
        indexes = [
            models.Index(fields=['user', 'operation_type']),
            models.Index(fields=['level', 'created_at']),
            models.Index(fields=['operation_type', 'created_at']),
        ]
    
    def __str__(self):
        return f"{self.operation_type} - {self.user.phone_number} - {self.level}"


class ReceiptVoiceMatch(BaseModel):
    """Модель сопоставления голосовых сообщений с чеками"""
    
    STATUS_CHOICES = [
        ('processing', 'Обрабатывается'),
        ('completed', 'Завершено'),
        ('failed', 'Ошибка'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        'users.User', 
        on_delete=models.CASCADE, 
        related_name='receipt_voice_matches',
        verbose_name='Пользователь'
    )
    
    # Связанные объекты
    voice_result = models.ForeignKey(
        VoiceResult,
        on_delete=models.CASCADE,
        related_name='receipt_matches',
        verbose_name='Результат распознавания голоса'
    )
    ocr_result = models.ForeignKey(
        OCRResult,
        on_delete=models.CASCADE,
        related_name='voice_matches',
        verbose_name='Результат OCR чека'
    )
    
    # Результаты сопоставления
    confidence_score = models.FloatField(
        default=0.0,
        validators=[MinValueValidator(0.0), MaxValueValidator(1.0)],
        verbose_name='Уверенность сопоставления'
    )
    
    # Данные из голосового сообщения
    voice_items = models.JSONField(
        default=list,
        blank=True,
        verbose_name='Товары из голоса'
    )
    total_amount_voice = models.FloatField(
        default=0.0,
        verbose_name='Общая сумма из голоса'
    )
    
    # Данные из чека
    receipt_items = models.JSONField(
        default=list,
        blank=True,
        verbose_name='Товары из чека'
    )
    total_amount_receipt = models.FloatField(
        default=0.0,
        verbose_name='Общая сумма из чека'
    )
    
    # Результаты сопоставления
    matched_items = models.JSONField(
        default=list,
        blank=True,
        verbose_name='Сопоставленные товары'
    )
    
    matching_details = models.JSONField(
        default=dict,
        blank=True,
        verbose_name='Детали сопоставления'
    )
    
    # Статус обработки
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='processing',
        verbose_name='Статус обработки'
    )
    error_message = models.TextField(
        blank=True, 
        verbose_name='Сообщение об ошибке'
    )
    
    # Временные рамки
    time_difference_minutes = models.IntegerField(
        default=0,
        verbose_name='Разница во времени (мин)'
    )
    
    class Meta:
        ordering = ('-created_at',)
        verbose_name = 'Сопоставление голоса с чеком'
        verbose_name_plural = 'Сопоставления голоса с чеками'
        indexes = [
            models.Index(fields=['user', 'status']),
            models.Index(fields=['confidence_score']),
            models.Index(fields=['created_at']),
            models.Index(fields=['voice_result', 'ocr_result']),
        ]
        unique_together = [
            ('voice_result', 'ocr_result')
        ]
    
    def __str__(self):
        return f"Match {self.confidence_score:.2f} - {self.user.phone_number}"
    
    @property
    def is_high_confidence(self):
        """Проверяет, является ли сопоставление высокодостоверным"""
        return self.confidence_score >= 0.8
    
    @property
    def matched_items_count(self):
        """Количество сопоставленных товаров"""
        return len(self.matched_items) if self.matched_items else 0
    
    @property
    def amount_difference(self):
        """Разница в суммах"""
        if self.total_amount_voice > 0 and self.total_amount_receipt > 0:
            return abs(self.total_amount_voice - self.total_amount_receipt)
        return 0
    
    @property
    def amount_match_percentage(self):
        """Процент совпадения сумм"""
        if self.total_amount_voice > 0 and self.total_amount_receipt > 0:
            max_amount = max(self.total_amount_voice, self.total_amount_receipt)
            diff = self.amount_difference
            return max(0, (1 - diff / max_amount) * 100)
        return 0
    
    def save(self, *args, **kwargs):
        """Переопределяем save для вычисления временной разности"""
        if self.voice_result and self.ocr_result:
            time_diff = abs(
                (self.voice_result.created_at - self.ocr_result.created_at).total_seconds() / 60
            )
            self.time_difference_minutes = int(time_diff)
        
        super().save(*args, **kwargs)


class ReceiptVoiceMatch(BaseModel):
    """Модель сопоставления голосовых сообщений с чеками"""
    
    STATUS_CHOICES = [
        ('processing', 'Обрабатывается'),
        ('completed', 'Завершено'),
        ('failed', 'Ошибка'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        'users.User', 
        on_delete=models.CASCADE, 
        related_name='receipt_voice_matches',
        verbose_name='Пользователь'
    )
    
    # Связанные объекты
    voice_result = models.ForeignKey(
        VoiceResult,
        on_delete=models.CASCADE,
        related_name='receipt_matches',
        verbose_name='Результат распознавания голоса'
    )
    ocr_result = models.ForeignKey(
        OCRResult,
        on_delete=models.CASCADE,
        related_name='voice_matches',
        verbose_name='Результат OCR чека'
    )
    
    # Результаты сопоставления
    confidence_score = models.FloatField(
        default=0.0,
        validators=[MinValueValidator(0.0), MaxValueValidator(1.0)],
        verbose_name='Уверенность сопоставления'
    )
    
    # Данные из голосового сообщения
    voice_items = models.JSONField(
        default=list,
        blank=True,
        verbose_name='Товары из голоса'
    )
    total_amount_voice = models.FloatField(
        default=0.0,
        verbose_name='Общая сумма из голоса'
    )
    
    # Данные из чека
    receipt_items = models.JSONField(
        default=list,
        blank=True,
        verbose_name='Товары из чека'
    )
    total_amount_receipt = models.FloatField(
        default=0.0,
        verbose_name='Общая сумма из чека'
    )
    
    # Результаты сопоставления
    matched_items = models.JSONField(
        default=list,
        blank=True,
        verbose_name='Сопоставленные товары'
    )
    
    matching_details = models.JSONField(
        default=dict,
        blank=True,
        verbose_name='Детали сопоставления'
    )
    
    # Статус обработки
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='processing',
        verbose_name='Статус обработки'
    )
    error_message = models.TextField(
        blank=True, 
        verbose_name='Сообщение об ошибке'
    )
    
    # Временные рамки
    time_difference_minutes = models.IntegerField(
        default=0,
        verbose_name='Разница во времени (мин)'
    )
    
    class Meta:
        ordering = ('-created_at',)
        verbose_name = 'Сопоставление голоса с чеком'
        verbose_name_plural = 'Сопоставления голоса с чеками'
        indexes = [
            models.Index(fields=['user', 'status']),
            models.Index(fields=['confidence_score']),
            models.Index(fields=['created_at']),
            models.Index(fields=['voice_result', 'ocr_result']),
        ]
        unique_together = [
            ('voice_result', 'ocr_result')
        ]
    
    def __str__(self):
        return f"Match {self.confidence_score:.2f} - {self.user.phone_number}"
    
    @property
    def is_high_confidence(self):
        """Проверяет, является ли сопоставление высокодостоверным"""
        return self.confidence_score >= 0.8
    
    @property
    def matched_items_count(self):
        """Количество сопоставленных товаров"""
        return len(self.matched_items) if self.matched_items else 0
    
    @property
    def amount_difference(self):
        """Разница в суммах"""
        if self.total_amount_voice > 0 and self.total_amount_receipt > 0:
            return abs(self.total_amount_voice - self.total_amount_receipt)
        return 0
    
    @property
    def amount_match_percentage(self):
        """Процент совпадения сумм"""
        if self.total_amount_voice > 0 and self.total_amount_receipt > 0:
            max_amount = max(self.total_amount_voice, self.total_amount_receipt)
            diff = self.amount_difference
            return max(0, (1 - diff / max_amount) * 100)
        return 0
    
    def save(self, *args, **kwargs):
        """Переопределяем save для вычисления временной разности"""
        if self.voice_result and self.ocr_result:
            time_diff = abs(
                (self.voice_result.created_at - self.ocr_result.created_at).total_seconds() / 60
            )
            self.time_difference_minutes = int(time_diff)
        
        super().save(*args, **kwargs) 