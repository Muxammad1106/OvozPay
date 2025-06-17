import uuid
from django.db import models
from apps.core.models import BaseModel


class Referral(BaseModel):
    """Модель реферальной программы"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    referrer = models.ForeignKey('User', on_delete=models.CASCADE, related_name='referrals')
    referral_code = models.CharField(max_length=20, unique=True)
    
    class Meta:
        ordering = ('-created_at',)
        verbose_name = 'Реферал'
        verbose_name_plural = 'Рефералы'
    
    def __str__(self):
        return f"Реферал {self.referral_code} от {self.referrer.phone_number}"


class User(BaseModel):
    """Основная модель пользователя"""
    
    LANGUAGE_CHOICES = [
        ('ru', 'Русский'),
        ('uz', "O'zbekcha"),
        ('en', 'English'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    phone_number = models.CharField(max_length=20, unique=True, verbose_name='Номер телефона')
    language = models.CharField(
        max_length=2, 
        choices=LANGUAGE_CHOICES, 
        default='ru',
        verbose_name='Язык'
    )
    referral = models.ForeignKey(
        Referral, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        verbose_name='Реферал'
    )
    source = models.ForeignKey(
        'sources.Source', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        verbose_name='Источник'
    )
    is_active = models.BooleanField(default=True, verbose_name='Активен')
    
    class Meta:
        ordering = ('-created_at',)
        verbose_name = 'Пользователь'
        verbose_name_plural = 'Пользователи'
    
    def __str__(self):
        return self.phone_number
    
    def save(self, *args, **kwargs):
        """Создаем настройки пользователя после создания"""
        is_new = self.pk is None
        super().save(*args, **kwargs)
        
        if is_new:
            UserSettings.objects.create(user=self)


class UserSettings(BaseModel):
    """Настройки пользователя"""
    
    CURRENCY_CHOICES = [
        ('UZS', 'Сум'),
        ('USD', 'Доллар США'),
        ('RUB', 'Российский рубль'),
        ('EUR', 'Евро'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='settings')
    currency = models.CharField(
        max_length=3, 
        choices=CURRENCY_CHOICES, 
        default='UZS',
        verbose_name='Валюта по умолчанию'
    )
    notify_reports = models.BooleanField(default=True, verbose_name='Уведомления об отчётах')
    notify_goals = models.BooleanField(default=True, verbose_name='Напоминания о целях')
    
    class Meta:
        verbose_name = 'Настройки пользователя'
        verbose_name_plural = 'Настройки пользователей'
    
    def __str__(self):
        return f"Настройки {self.user.phone_number}"
