"""
Модели для Telegram бота OvozPay
"""

from django.db import models
import uuid
from django.utils import timezone


class BaseModel(models.Model):
    """Базовая модель с общими полями"""
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Создано')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Обновлено')
    
    class Meta:
        abstract = True


class TelegramUser(BaseModel):
    """Пользователь Telegram бота"""
    
    LANGUAGE_CHOICES = [
        ('ru', 'Русский'),
        ('en', 'English'),
        ('uz', 'O\'zbekcha'),
    ]
    
    CURRENCY_CHOICES = [
        ('UZS', 'Узбекский сум'),
        ('USD', 'Доллар США'),
        ('EUR', 'Евро'),
        ('RUB', 'Российский рубль'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    telegram_user_id = models.BigIntegerField(unique=True, verbose_name='Telegram User ID')
    telegram_chat_id = models.BigIntegerField(unique=True, verbose_name='Telegram Chat ID')
    username = models.CharField(max_length=255, blank=True, verbose_name='Username')
    first_name = models.CharField(max_length=255, blank=True, verbose_name='Имя')
    last_name = models.CharField(max_length=255, blank=True, verbose_name='Фамилия')
    phone_number = models.CharField(max_length=20, blank=True, verbose_name='Номер телефона')
    
    language = models.CharField(
        max_length=5,
        choices=LANGUAGE_CHOICES,
        default='ru',
        verbose_name='Язык интерфейса'
    )
    preferred_currency = models.CharField(
        max_length=3,
        choices=CURRENCY_CHOICES,
        default='UZS',
        verbose_name='Предпочитаемая валюта'
    )
    
    is_active = models.BooleanField(default=True, verbose_name='Активен')
    is_blocked = models.BooleanField(default=False, verbose_name='Заблокирован')
    
    class Meta:
        ordering = ('-created_at',)
        verbose_name = 'Пользователь Telegram'
        verbose_name_plural = 'Пользователи Telegram'
        indexes = [
            models.Index(fields=['telegram_chat_id']),
            models.Index(fields=['telegram_user_id']),
            models.Index(fields=['is_active']),
        ]
    
    def __str__(self):
        name = self.first_name or self.username or str(self.telegram_chat_id)
        return f"{name} ({self.get_language_display()})"
    
    @property
    def full_name(self):
        """Возвращает полное имя"""
        parts = [self.first_name, self.last_name]
        return ' '.join(part for part in parts if part)
    
    @property
    def display_name(self):
        """Возвращает отображаемое имя"""
        return self.full_name or self.username or f"User {self.telegram_chat_id}"


class BotSession(BaseModel):
    """Сессия пользователя в боте"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(TelegramUser, on_delete=models.CASCADE, related_name='sessions')
    state = models.CharField(max_length=50, blank=True, null=True, verbose_name='Состояние')
    context_data = models.JSONField(default=dict, blank=True, verbose_name='Контекстные данные')
    is_active = models.BooleanField(default=True, verbose_name='Активна')
    last_activity = models.DateTimeField(auto_now=True, verbose_name='Последняя активность')
    
    class Meta:
        ordering = ('-last_activity',)
        verbose_name = 'Сессия бота'
        verbose_name_plural = 'Сессии бота'
        indexes = [
            models.Index(fields=['user', 'is_active']),
            models.Index(fields=['state']),
        ]
    
    def __str__(self):
        return f"Сессия {self.user.display_name} ({self.state or 'default'})"


class MessageLog(BaseModel):
    """Лог сообщений"""
    
    MESSAGE_TYPE_CHOICES = [
        ('text', 'Текст'),
        ('voice', 'Голос'),
        ('photo', 'Фото'),
        ('command', 'Команда'),
        ('callback', 'Callback'),
    ]
    
    DIRECTION_CHOICES = [
        ('incoming', 'Входящее'),
        ('outgoing', 'Исходящее'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(TelegramUser, on_delete=models.CASCADE, related_name='message_logs')
    message_type = models.CharField(max_length=10, choices=MESSAGE_TYPE_CHOICES, verbose_name='Тип сообщения')
    direction = models.CharField(max_length=10, choices=DIRECTION_CHOICES, verbose_name='Направление')
    content = models.TextField(verbose_name='Содержимое')
    telegram_message_id = models.BigIntegerField(null=True, blank=True, verbose_name='ID сообщения в Telegram')
    processing_time = models.FloatField(null=True, blank=True, verbose_name='Время обработки (сек)')
    success = models.BooleanField(default=True, verbose_name='Успешно')
    error_message = models.TextField(blank=True, verbose_name='Сообщение об ошибке')
    
    class Meta:
        ordering = ('-created_at',)
        verbose_name = 'Лог сообщения'
        verbose_name_plural = 'Логи сообщений'
        indexes = [
            models.Index(fields=['user', 'message_type']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self):
        return f"{self.get_message_type_display()} от {self.user.display_name}"


class VoiceCommand(BaseModel):
    """Голосовые команды пользователей"""
    
    COMMAND_TYPE_CHOICES = [
        ('expense', 'Расход'),
        ('income', 'Доход'),
        ('query', 'Запрос'),
        ('unknown', 'Неизвестно'),
    ]
    
    STATUS_CHOICES = [
        ('processing', 'Обрабатывается'),
        ('success', 'Успешно'),
        ('failed', 'Ошибка'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(TelegramUser, on_delete=models.CASCADE, related_name='voice_commands')
    telegram_file_id = models.CharField(max_length=255, verbose_name='Telegram File ID')
    transcription = models.TextField(blank=True, verbose_name='Распознанный текст')
    duration_seconds = models.PositiveIntegerField(verbose_name='Длительность (сек)')
    command_type = models.CharField(
        max_length=10,
        choices=COMMAND_TYPE_CHOICES,
        default='unknown',
        verbose_name='Тип команды'
    )
    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default='processing',
        verbose_name='Статус обработки'
    )
    extracted_amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name='Извлеченная сумма'
    )
    processing_time = models.FloatField(
        null=True,
        blank=True,
        verbose_name='Время обработки (сек)'
    )
    error_message = models.TextField(blank=True, verbose_name='Сообщение об ошибке')
    created_transaction_id = models.UUIDField(
        null=True,
        blank=True,
        verbose_name='ID созданной транзакции'
    )
    
    class Meta:
        ordering = ('-created_at',)
        verbose_name = 'Голосовая команда'
        verbose_name_plural = 'Голосовые команды'
        indexes = [
            models.Index(fields=['user', 'status']),
            models.Index(fields=['command_type']),
        ]
    
    def __str__(self):
        return f"Голосовая команда {self.user.display_name}: {self.transcription[:50]}..."
    
    @classmethod
    def get_user_stats(cls, user, days=30):
        """Получает статистику голосовых команд пользователя за указанный период"""
        from django.utils import timezone
        from datetime import timedelta
        
        start_date = timezone.now() - timedelta(days=days)
        commands = cls.objects.filter(user=user, created_at__gte=start_date)
        
        total_commands = commands.count()
        successful_commands = commands.filter(status='success').count()
        failed_commands = commands.filter(status='failed').count()
        
        return {
            'total_commands': total_commands,
            'successful_commands': successful_commands,
            'failed_commands': failed_commands,
            'success_rate': successful_commands / total_commands if total_commands > 0 else 0,
            'period_days': days
        }


class PhotoReceipt(BaseModel):
    """Фотографии чеков"""
    
    STATUS_CHOICES = [
        ('processing', 'Обрабатывается'),
        ('success', 'Успешно'),
        ('failed', 'Ошибка'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(TelegramUser, on_delete=models.CASCADE, related_name='photo_receipts')
    telegram_file_id = models.CharField(max_length=255, verbose_name='Telegram File ID')
    file_size_bytes = models.PositiveIntegerField(verbose_name='Размер файла (байт)')
    extracted_text = models.TextField(blank=True, verbose_name='Извлечённый текст')
    items_count = models.PositiveIntegerField(default=0, verbose_name='Количество товаров')
    total_amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name='Общая сумма'
    )
    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default='processing',
        verbose_name='Статус обработки'
    )
    processing_time = models.FloatField(
        null=True,
        blank=True,
        verbose_name='Время обработки (сек)'
    )
    error_message = models.TextField(blank=True, verbose_name='Сообщение об ошибке')
    
    class Meta:
        ordering = ('-created_at',)
        verbose_name = 'Фото чека'
        verbose_name_plural = 'Фото чеков'
        indexes = [
            models.Index(fields=['user', 'status']),
        ]
    
    def __str__(self):
        return f"Фото чека {self.user.display_name}: {self.items_count} товаров"


class BotStatistics(BaseModel):
    """Статистика использования бота"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    date = models.DateField(unique=True, verbose_name='Дата')
    total_users = models.PositiveIntegerField(default=0, verbose_name='Всего пользователей')
    active_users = models.PositiveIntegerField(default=0, verbose_name='Активных пользователей')
    new_users = models.PositiveIntegerField(default=0, verbose_name='Новых пользователей')
    total_messages = models.PositiveIntegerField(default=0, verbose_name='Всего сообщений')
    voice_messages = models.PositiveIntegerField(default=0, verbose_name='Голосовых сообщений')
    photo_messages = models.PositiveIntegerField(default=0, verbose_name='Фото сообщений')
    successful_commands = models.PositiveIntegerField(default=0, verbose_name='Успешных команд')
    failed_commands = models.PositiveIntegerField(default=0, verbose_name='Неудачных команд')
    
    # Статистика по языкам
    users_ru = models.PositiveIntegerField(default=0, verbose_name='Пользователей (русский)')
    users_en = models.PositiveIntegerField(default=0, verbose_name='Пользователей (английский)')
    users_uz = models.PositiveIntegerField(default=0, verbose_name='Пользователей (узбекский)')
    
    class Meta:
        ordering = ('-date',)
        verbose_name = 'Статистика бота'
        verbose_name_plural = 'Статистика бота'
        indexes = [
            models.Index(fields=['date']),
        ]
    
    def __str__(self):
        return f"Статистика {self.date}: {self.active_users} активных пользователей"
