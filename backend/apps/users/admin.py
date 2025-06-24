from django.contrib import admin
from .models import User

@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = (
        'phone_number', 
        'first_name', 
        'last_name', 
        'username',
        'telegram_chat_id',
        'is_active',
        'created_at',
    )
    list_filter = (
        'is_active', 
        'created_at',
    )
    search_fields = (
        'phone_number', 
        'first_name', 
        'last_name', 
        'username',
        'telegram_chat_id',
    )
    readonly_fields = (
        'id', 
        'created_at', 
        'updated_at',
    )
    ordering = ('-created_at',)
    
    fieldsets = (
        ('Основная информация', {
            'fields': (
                'phone_number',
                'first_name', 
                'last_name',
                'username',
            )
        }),
        ('Telegram данные', {
            'fields': (
                'telegram_chat_id',
            )
        }),
        ('Статус', {
            'fields': (
                'is_active',
            )
        }),
        ('Системная информация', {
            'fields': (
                'id',
                'created_at',
                'updated_at',
            ),
            'classes': ('collapse',)
        }),
    )
