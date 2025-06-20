from rest_framework import serializers
from apps.users.models import User


class TelegramAuthSerializer(serializers.Serializer):
    """
    Сериализатор для аутентификации по Telegram Chat ID
    """
    telegram_chat_id = serializers.IntegerField(
        help_text="Telegram Chat ID пользователя"
    )
    phone_number = serializers.CharField(
        max_length=20,
        required=False,
        help_text="Номер телефона пользователя (опционально)"
    )
    
    def validate_telegram_chat_id(self, value):
        """
        Проверяем корректность Telegram Chat ID
        """
        if value <= 0:
            raise serializers.ValidationError(
                "Telegram Chat ID должен быть положительным числом"
            )
        return value
    
    def validate_phone_number(self, value):
        """
        Проверяем формат номера телефона
        """
        if value and not value.startswith('+'):
            raise serializers.ValidationError(
                "Номер телефона должен начинаться с +"
            )
        return value


class TelegramTokenResponseSerializer(serializers.Serializer):
    """
    Сериализатор для ответа с JWT токенами
    """
    access = serializers.CharField(
        help_text="Access токен JWT"
    )
    refresh = serializers.CharField(
        help_text="Refresh токен JWT"
    )
    user_id = serializers.UUIDField(
        help_text="ID пользователя"
    )
    phone_number = serializers.CharField(
        help_text="Номер телефона пользователя"
    )
    is_new_user = serializers.BooleanField(
        help_text="Новый пользователь или существующий"
    ) 