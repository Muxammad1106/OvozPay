import uuid
from django.db import models
from apps.core.models import BaseModel


class Category(BaseModel):
    """Модель категории доходов/расходов"""
    
    TYPE_CHOICES = [
        ('income', 'Доход'),
        ('expense', 'Расход'),
        ('debt', 'Долг'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        'users.User', 
        on_delete=models.CASCADE, 
        null=True, 
        blank=True,
        related_name='categories',
        verbose_name='Пользователь',
        help_text='Если null - системная категория для всех пользователей'
    )
    name = models.CharField(max_length=100, verbose_name='Название категории')
    type = models.CharField(
        max_length=10, 
        choices=TYPE_CHOICES,
        verbose_name='Тип категории'
    )
    is_default = models.BooleanField(default=False, verbose_name='Категория по умолчанию')
    
    class Meta:
        ordering = ('type', 'name')
        verbose_name = 'Категория'
        verbose_name_plural = 'Категории'
        unique_together = [['user', 'name', 'type']]
        indexes = [
            models.Index(fields=['user', 'type']),
            models.Index(fields=['is_default']),
        ]
    
    def __str__(self):
        user_info = f" ({self.user.phone_number})" if self.user else " (системная)"
        return f"{self.name} - {self.get_type_display()}{user_info}"
    
    @classmethod
    def get_default_categories(cls):
        """Возвращает системные категории по умолчанию"""
        return cls.objects.filter(user=None, is_default=True)
    
    @classmethod
    def create_default_categories_for_user(cls, user):
        """Создает дефолтные категории для нового пользователя"""
        default_categories = [
            # Категории расходов
            {'name': 'Еда и рестораны', 'type': 'expense'},
            {'name': 'Транспорт', 'type': 'expense'},
            {'name': 'Покупки', 'type': 'expense'},
            {'name': 'ЖКХ', 'type': 'expense'},
            {'name': 'Здоровье', 'type': 'expense'},
            {'name': 'Развлечения', 'type': 'expense'},
            {'name': 'Образование', 'type': 'expense'},
            {'name': 'Другое', 'type': 'expense'},
            
            # Категории доходов
            {'name': 'Зарплата', 'type': 'income'},
            {'name': 'Фриланс', 'type': 'income'},
            {'name': 'Продажи', 'type': 'income'},
            {'name': 'Инвестиции', 'type': 'income'},
            {'name': 'Подарки', 'type': 'income'},
            {'name': 'Другое', 'type': 'income'},
            
            # Категории долгов
            {'name': 'Долг другу', 'type': 'debt'},
            {'name': 'Кредит', 'type': 'debt'},
            {'name': 'Займ', 'type': 'debt'},
        ]
        
        created_categories = []
        for cat_data in default_categories:
            category, created = cls.objects.get_or_create(
                user=user,
                name=cat_data['name'],
                type=cat_data['type'],
                defaults={'is_default': True}
            )
            if created:
                created_categories.append(category)
        
        return created_categories
