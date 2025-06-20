from django.db import models
import uuid
from apps.core.models import BaseModel

# Create your models here.

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
    first_name = models.CharField(max_length=150, blank=True, verbose_name='Имя')
    last_name = models.CharField(max_length=150, blank=True, verbose_name='Фамилия')
    username = models.CharField(max_length=150, blank=True, verbose_name='Username')
    telegram_chat_id = models.BigIntegerField(
        unique=True, 
        null=True, 
        blank=True,
        verbose_name='Telegram Chat ID'
    )
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

    @classmethod
    def get_or_create_by_telegram(cls, telegram_chat_id, phone_number=None, 
                                first_name='', last_name='', username=''):
        """Получает или создает пользователя по Telegram Chat ID"""
        try:
            # Пытаемся найти пользователя по telegram_chat_id
            user = cls.objects.get(telegram_chat_id=telegram_chat_id)
            return user, False
        except cls.DoesNotExist:
            # Если не найден по telegram_chat_id и есть номер телефона, 
            # пытаемся найти по номеру телефона
            if phone_number:
                try:
                    user = cls.objects.get(phone_number=phone_number)
                    # Обновляем telegram_chat_id
                    user.telegram_chat_id = telegram_chat_id
                    user.save()
                    return user, False
                except cls.DoesNotExist:
                    pass
            
            # Создаем нового пользователя
            user_data = {
                'telegram_chat_id': telegram_chat_id,
                'first_name': first_name or 'Пользователь',
                'last_name': last_name or '',
                'username': username or f'user_{telegram_chat_id}',
            }
            
            if phone_number:
                user_data['phone_number'] = phone_number
            else:
                # Если номер телефона не указан, используем telegram_chat_id как временный
                user_data['phone_number'] = f"tg_{telegram_chat_id}"
            
            user = cls.objects.create(**user_data)
            return user, True


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
