import uuid
from django.db import models
from django.utils import timezone
from apps.core.models import BaseModel


class BroadcastMessage(BaseModel):
    """Модель рассылки сообщений"""
    
    STATUS_CHOICES = [
        ('draft', 'Черновик'),
        ('scheduled', 'Запланировано'),
        ('sending', 'Отправляется'),
        ('sent', 'Отправлено'),
        ('failed', 'Ошибка'),
    ]
    
    TARGET_CHOICES = [
        ('all', 'Все пользователи'),
        ('active', 'Только активные'),
        ('inactive', 'Неактивные'),
        ('new', 'Новые (за последние 7 дней)'),
        ('custom', 'Кастомная группа'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=200, verbose_name='Заголовок рассылки')
    body = models.TextField(verbose_name='Текст сообщения')
    send_at = models.DateTimeField(
        verbose_name='Дата отправки',
        help_text='Если не указано, отправится немедленно'
    )
    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default='draft',
        verbose_name='Статус'
    )
    target_audience = models.CharField(
        max_length=10,
        choices=TARGET_CHOICES,
        default='active',
        verbose_name='Целевая аудитория'
    )
    sent_count = models.PositiveIntegerField(default=0, verbose_name='Отправлено')
    failed_count = models.PositiveIntegerField(default=0, verbose_name='Ошибок')
    
    class Meta:
        ordering = ('-created_at',)
        verbose_name = 'Рассылка'
        verbose_name_plural = 'Рассылки'
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['send_at']),
        ]
    
    def __str__(self):
        return f"Рассылка: {self.title}"
    
    @property
    def total_recipients(self):
        """Возвращает общее количество получателей"""
        return self.broadcast_logs.count()
    
    @property
    def success_rate(self):
        """Возвращает процент успешной доставки"""
        if self.total_recipients == 0:
            return 0
        
        return (self.sent_count / self.total_recipients) * 100
    
    def get_target_users(self):
        """Возвращает QuerySet пользователей для рассылки"""
        from apps.users.models import User
        from datetime import timedelta
        
        if self.target_audience == 'all':
            return User.objects.all()
        elif self.target_audience == 'active':
            return User.objects.filter(is_active=True)
        elif self.target_audience == 'inactive':
            return User.objects.filter(is_active=False)
        elif self.target_audience == 'new':
            week_ago = timezone.now() - timedelta(days=7)
            return User.objects.filter(created_at__gte=week_ago, is_active=True)
        else:  # custom
            return User.objects.none()
    
    def schedule_broadcast(self, send_at=None):
        """Планирует рассылку"""
        if send_at:
            self.send_at = send_at
        
        if self.send_at <= timezone.now():
            self.status = 'sending'
        else:
            self.status = 'scheduled'
        
        self.save()
    
    def start_sending(self):
        """Начинает отправку рассылки"""
        if self.status not in ['draft', 'scheduled']:
            return False
        
        self.status = 'sending'
        self.save()
        
        # Создаем записи для всех получателей
        users = self.get_target_users()
        
        for user in users:
            BroadcastUserLog.objects.get_or_create(
                message=self,
                user=user,
                defaults={'status': 'pending'}
            )
        
        return True
    
    def mark_as_completed(self):
        """Помечает рассылку как завершенную"""
        self.status = 'sent'
        
        # Обновляем счетчики
        self.sent_count = self.broadcast_logs.filter(status='sent').count()
        self.failed_count = self.broadcast_logs.filter(status='failed').count()
        
        self.save()


class BroadcastUserLog(BaseModel):
    """Лог отправки рассылки конкретному пользователю"""
    
    STATUS_CHOICES = [
        ('pending', 'Ожидает отправки'),
        ('sent', 'Отправлено'),
        ('failed', 'Ошибка'),
        ('read', 'Прочитано'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    message = models.ForeignKey(
        BroadcastMessage, 
        on_delete=models.CASCADE, 
        related_name='broadcast_logs'
    )
    user = models.ForeignKey('users.User', on_delete=models.CASCADE, related_name='broadcast_logs')
    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default='pending',
        verbose_name='Статус отправки'
    )
    sent_at = models.DateTimeField(null=True, blank=True, verbose_name='Время отправки')
    error_message = models.TextField(blank=True, verbose_name='Сообщение об ошибке')
    read_at = models.DateTimeField(null=True, blank=True, verbose_name='Время прочтения')
    
    class Meta:
        ordering = ('-created_at',)
        verbose_name = 'Лог рассылки'
        verbose_name_plural = 'Логи рассылок'
        unique_together = [['message', 'user']]
        indexes = [
            models.Index(fields=['message', 'status']),
            models.Index(fields=['user']),
            models.Index(fields=['sent_at']),
        ]
    
    def __str__(self):
        return f"{self.message.title} -> {self.user.phone_number}"
    
    def mark_as_sent(self):
        """Помечает сообщение как отправленное"""
        self.status = 'sent'
        self.sent_at = timezone.now()
        self.save()
    
    def mark_as_failed(self, error_message=None):
        """Помечает сообщение как неудачное"""
        self.status = 'failed'
        if error_message:
            self.error_message = error_message
        self.save()
    
    def mark_as_read(self):
        """Помечает сообщение как прочитанное"""
        if self.status == 'sent':
            self.status = 'read'
            self.read_at = timezone.now()
            self.save()
    
    @property
    def delivery_time(self):
        """Возвращает время доставки (если доставлено)"""
        if self.sent_at and self.created_at:
            return self.sent_at - self.created_at
        return None
