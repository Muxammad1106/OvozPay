import logging
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from apps.users.models import User
from apps.users.serializers.auth_serializers import (
    TelegramAuthSerializer,
    TelegramTokenResponseSerializer
)

logger = logging.getLogger(__name__)


@swagger_auto_schema(
    method='post',
    operation_description="Аутентификация пользователя по Telegram Chat ID",
    request_body=TelegramAuthSerializer,
    responses={
        200: TelegramTokenResponseSerializer,
        400: openapi.Response(
            description="Ошибка валидации данных",
            examples={
                "application/json": {
                    "error": "Неверные данные",
                    "details": {}
                }
            }
        ),
        500: openapi.Response(
            description="Внутренняя ошибка сервера"
        )
    },
    tags=['Аутентификация']
)
@api_view(['POST'])
@permission_classes([AllowAny])
def telegram_login(request):
    """
    Аутентификация пользователя по Telegram Chat ID
    
    Если пользователь существует - возвращает JWT токены
    Если не существует - создает нового и возвращает токены
    """
    try:
        # Валидируем входные данные
        serializer = TelegramAuthSerializer(data=request.data)
        
        if not serializer.is_valid():
            return Response(
                {
                    'error': 'Неверные данные',
                    'details': serializer.errors
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        
        telegram_chat_id = serializer.validated_data['telegram_chat_id']
        phone_number = serializer.validated_data.get('phone_number')
        
        # Получаем или создаем пользователя
        user, is_new_user = User.get_or_create_by_telegram(
            telegram_chat_id=telegram_chat_id,
            phone_number=phone_number
        )
        
        # Генерируем JWT токены
        refresh = RefreshToken.for_user(user)
        access_token = str(refresh.access_token)
        refresh_token = str(refresh)
        
        # Формируем ответ
        response_data = {
            'access': access_token,
            'refresh': refresh_token,
            'user_id': str(user.id),
            'phone_number': user.phone_number,
            'is_new_user': is_new_user
        }
        
        # Логируем успешную аутентификацию
        logger.info(
            f"Telegram аутентификация: chat_id={telegram_chat_id}, "
            f"user_id={user.id}, new_user={is_new_user}"
        )
        
        return Response(
            response_data,
            status=status.HTTP_200_OK
        )
        
    except Exception as e:
        logger.error(f"Ошибка Telegram аутентификации: {e}")
        return Response(
            {
                'error': 'Внутренняя ошибка сервера',
                'message': 'Попробуйте позже'
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@swagger_auto_schema(
    method='post',
    operation_description="Обновление refresh токена",
    request_body=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        properties={
            'refresh': openapi.Schema(
                type=openapi.TYPE_STRING,
                description='Refresh токен'
            )
        },
        required=['refresh']
    ),
    responses={
        200: openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'access': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description='Новый access токен'
                ),
                'refresh': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description='Новый refresh токен (опционально)'
                )
            }
        ),
        400: openapi.Response(description="Неверный токен"),
        401: openapi.Response(description="Токен истек")
    },
    tags=['Аутентификация']
)
@api_view(['POST'])
@permission_classes([AllowAny])
def refresh_token(request):
    """
    Обновление access токена с помощью refresh токена
    """
    try:
        refresh_token = request.data.get('refresh')
        
        if not refresh_token:
            return Response(
                {'error': 'Refresh токен обязателен'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            # Создаем объект RefreshToken
            refresh = RefreshToken(refresh_token)
            
            # Получаем новый access токен
            access_token = str(refresh.access_token)
            
            response_data = {
                'access': access_token
            }
            
            # В некоторых случаях можем вернуть и новый refresh токен
            # if settings.SIMPLE_JWT.get('ROTATE_REFRESH_TOKENS'):
            #     response_data['refresh'] = str(refresh)
            
            return Response(
                response_data,
                status=status.HTTP_200_OK
            )
            
        except Exception as token_error:
            logger.warning(f"Неверный refresh токен: {token_error}")
            return Response(
                {'error': 'Неверный или истекший токен'},
                status=status.HTTP_401_UNAUTHORIZED
            )
            
    except Exception as e:
        logger.error(f"Ошибка обновления токена: {e}")
        return Response(
            {'error': 'Внутренняя ошибка сервера'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        ) 