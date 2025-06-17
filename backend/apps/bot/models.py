from django.db import models
import uuid
from django.utils import timezone
from apps.core.models import BaseModel

# Create your models here.

class VoiceCommandLog(BaseModel):
    """Лог голосовых команд пользователей"""
    
    COMMAND_TYPE_CHOICES = [
        ('expense', 'Расход'),
        ('income', 'Доход'),
        ('goal', 'Цель'),
        ('debt', 'Долг'),
        ('query', 'Запрос'),
        ('unknown', 'Неизвестно'),
    ]
    
    STATUS_CHOICES = [
        ('processing', 'Обрабатывается'),
        ('success', 'Успешно'),
        ('failed', 'Ошибка'),
        ('partial', 'Частично выполнено'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey('users.User', on_delete=models.CASCADE, related_name='voice_commands')
    text = models.TextField(verbose_name='Распознанный текст')
    original_audio_duration = models.FloatField(
        null=True, 
        blank=True,
        verbose_name='Длительность аудио (сек)'
    )
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
    confidence_score = models.FloatField(
        null=True,
        blank=True,
        verbose_name='Уверенность распознавания (0-1)'
    )
    processing_time = models.FloatField(
        null=True,
        blank=True,
        verbose_name='Время обработки (сек)'
    )
    error_message = models.TextField(blank=True, verbose_name='Сообщение об ошибке')
    extracted_amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name='Извлеченная сумма'
    )
    extracted_currency = models.CharField(
        max_length=3,
        blank=True,
        verbose_name='Извлеченная валюта'
    )
    created_transaction_id = models.UUIDField(
        null=True,
        blank=True,
        verbose_name='ID созданной транзакции'
    )
    received_at = models.DateTimeField(default=timezone.now, verbose_name='Время получения')
    
    class Meta:
        ordering = ('-received_at',)
        verbose_name = 'Лог голосовой команды'
        verbose_name_plural = 'Логи голосовых команд'
        indexes = [
            models.Index(fields=['user', 'command_type']),
            models.Index(fields=['status']),
            models.Index(fields=['received_at']),
        ]
    
    def __str__(self):
        return f"Команда {self.user.phone_number}: {self.text[:50]}..."
    
    def mark_as_success(self, transaction_id=None):
        """Помечает команду как успешно выполненную"""
        self.status = 'success'
        if transaction_id:
            self.created_transaction_id = transaction_id
        self.save()
    
    def mark_as_failed(self, error_message):
        """Помечает команду как неудачную"""
        self.status = 'failed'
        self.error_message = error_message
        self.save()
    
    def set_processing_time(self, start_time):
        """Устанавливает время обработки"""
        self.processing_time = (timezone.now() - start_time).total_seconds()
        self.save()
    
    @classmethod
    def get_user_stats(cls, user, days=30):
        """Возвращает статистику голосовых команд пользователя"""
        from datetime import timedelta
        
        cutoff_date = timezone.now() - timedelta(days=days)
        commands = cls.objects.filter(user=user, received_at__gte=cutoff_date)
        
        return {
            'total_commands': commands.count(),
            'successful_commands': commands.filter(status='success').count(),
            'failed_commands': commands.filter(status='failed').count(),
            'avg_processing_time': commands.exclude(
                processing_time=None
            ).aggregate(
                avg_time=models.Avg('processing_time')
            )['avg_time'] or 0,
            'command_types': commands.values('command_type').annotate(
                count=models.Count('id')
            ),
        }


class BotSession(BaseModel):
    """Сессия взаимодействия пользователя с ботом"""
    
    SESSION_TYPE_CHOICES = [
        ('voice', 'Голосовая'),
        ('text', 'Текстовая'),
        ('mixed', 'Смешанная'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey('users.User', on_delete=models.CASCADE, related_name='bot_sessions')
    telegram_chat_id = models.BigIntegerField(verbose_name='ID чата в Telegram')
    session_type = models.CharField(
        max_length=10,
        choices=SESSION_TYPE_CHOICES,
        default='mixed',
        verbose_name='Тип сессии'
    )
    is_active = models.BooleanField(default=True, verbose_name='Активна')
    started_at = models.DateTimeField(default=timezone.now, verbose_name='Начало сессии')
    ended_at = models.DateTimeField(
        null=True, 
        blank=True, 
        verbose_name='Конец сессии'
    )
    messages_count = models.PositiveIntegerField(default=0, verbose_name='Количество сообщений')
    voice_messages_count = models.PositiveIntegerField(default=0, verbose_name='Голосовых сообщений')
    commands_executed = models.PositiveIntegerField(default=0, verbose_name='Выполнено команд')
    last_activity_at = models.DateTimeField(
        default=timezone.now,
        verbose_name='Последняя активность'
    )
    
    class Meta:
        ordering = ('-started_at',)
        verbose_name = 'Сессия бота'
        verbose_name_plural = 'Сессии бота'
        indexes = [
            models.Index(fields=['user', 'is_active']),
            models.Index(fields=['telegram_chat_id']),
            models.Index(fields=['last_activity_at']),
        ]
    
    def __str__(self):
        status = "Активна" if self.is_active else "Завершена"
        return f"Сессия {self.user.phone_number} ({status})"
    
    @property
    def duration(self):
        """Возвращает длительность сессии"""
        end_time = self.ended_at or timezone.now()
        return end_time - self.started_at
    
    @property
    def duration_minutes(self):
        """Возвращает длительность сессии в минутах"""
        return self.duration.total_seconds() / 60
    
    def update_activity(self):
        """Обновляет время последней активности"""
        self.last_activity_at = timezone.now()
        self.save(update_fields=['last_activity_at'])
    
    def add_message(self, is_voice=False):
        """Добавляет сообщение к счетчику"""
        self.messages_count += 1
        if is_voice:
            self.voice_messages_count += 1
        self.update_activity()
        self.save(update_fields=['messages_count', 'voice_messages_count'])
    
    def add_command(self):
        """Добавляет выполненную команду к счетчику"""
        self.commands_executed += 1
        self.update_activity()
        self.save(update_fields=['commands_executed'])
    
    def end_session(self):
        """Завершает сессию"""
        self.is_active = False
        self.ended_at = timezone.now()
        self.save()
    
    @classmethod
    def get_or_create_active_session(cls, user, telegram_chat_id):
        """Получает или создает активную сессию для пользователя"""
        # Сначала пытаемся найти активную сессию
        active_session = cls.objects.filter(
            user=user,
            telegram_chat_id=telegram_chat_id,
            is_active=True
        ).first()
        
        if active_session:
            # Проверяем, не слишком ли старая сессия (больше 24 часов)
            if active_session.duration.total_seconds() > 24 * 3600:
                active_session.end_session()
                active_session = None
        
        # Создаем новую сессию, если нет активной
        if not active_session:
            active_session = cls.objects.create(
                user=user,
                telegram_chat_id=telegram_chat_id
            )
        
        return active_session
    
    @classmethod
    def end_inactive_sessions(cls, hours=24):
        """Завершает неактивные сессии старше указанного времени"""
        from datetime import timedelta
        
        cutoff_time = timezone.now() - timedelta(hours=hours)
        inactive_sessions = cls.objects.filter(
            is_active=True,
            last_activity_at__lt=cutoff_time
        )
        
        count = inactive_sessions.count()
        inactive_sessions.update(
            is_active=False,
            ended_at=timezone.now()
        )
        
        return count
