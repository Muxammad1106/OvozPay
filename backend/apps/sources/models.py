import uuid
from django.db import models
from apps.core.models import BaseModel


class Source(BaseModel):
    """Модель источника трафика"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(
        max_length=100, 
        unique=True,
        verbose_name='Название источника',
        help_text='Например: telegram, instagram, google, referral, direct'
    )
    description = models.TextField(
        blank=True,
        verbose_name='Описание источника'
    )
    utm_source = models.CharField(
        max_length=100,
        blank=True,
        verbose_name='UTM источник'
    )
    utm_medium = models.CharField(
        max_length=100,
        blank=True,
        verbose_name='UTM медиум'
    )
    utm_campaign = models.CharField(
        max_length=100,
        blank=True,
        verbose_name='UTM кампания'
    )
    is_active = models.BooleanField(default=True, verbose_name='Активен')
    
    class Meta:
        ordering = ('name',)
        verbose_name = 'Источник трафика'
        verbose_name_plural = 'Источники трафика'
        indexes = [
            models.Index(fields=['name']),
            models.Index(fields=['is_active']),
        ]
    
    def __str__(self):
        return self.name
    
    @classmethod
    def get_or_create_source(cls, name, **kwargs):
        """Получает или создает источник по имени"""
        source, created = cls.objects.get_or_create(
            name=name,
            defaults=kwargs
        )
        return source
    
    @classmethod
    def create_default_sources(cls):
        """Создает стандартные источники трафика"""
        default_sources = [
            {
                'name': 'telegram',
                'description': 'Переходы из Telegram',
                'utm_source': 'telegram',
                'utm_medium': 'social'
            },
            {
                'name': 'instagram',
                'description': 'Переходы из Instagram',
                'utm_source': 'instagram',
                'utm_medium': 'social'
            },
            {
                'name': 'whatsapp',
                'description': 'Переходы из WhatsApp',
                'utm_source': 'whatsapp',
                'utm_medium': 'messaging'
            },
            {
                'name': 'referral',
                'description': 'Реферальные переходы',
                'utm_source': 'referral',
                'utm_medium': 'referral'
            },
            {
                'name': 'direct',
                'description': 'Прямые переходы',
                'utm_source': 'direct',
                'utm_medium': 'none'
            },
            {
                'name': 'google',
                'description': 'Переходы из Google',
                'utm_source': 'google',
                'utm_medium': 'organic'
            },
            {
                'name': 'yandex',
                'description': 'Переходы из Yandex',
                'utm_source': 'yandex',
                'utm_medium': 'organic'
            },
        ]
        
        created_sources = []
        for source_data in default_sources:
            source, created = cls.objects.get_or_create(
                name=source_data['name'],
                defaults=source_data
            )
            if created:
                created_sources.append(source)
        
        return created_sources
    
    def get_users_count(self):
        """Возвращает количество пользователей из этого источника"""
        return self.users.count()
    
    def get_active_users_count(self):
        """Возвращает количество активных пользователей из этого источника"""
        return self.users.filter(is_active=True).count()
