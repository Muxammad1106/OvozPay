from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import get_user_model
from apps.users.models import User
from apps.bot.models import BotSession
import logging

logger = logging.getLogger(__name__)

User = get_user_model()


class TelegramLoginView(APIView):
    permission_classes = [AllowAny]
    
    def post(self, request):
        telegram_chat_id = request.data.get('telegram_chat_id')
        phone_number = request.data.get('phone_number')
        
        if not telegram_chat_id:
            return Response({
                'error': 'telegram_chat_id is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            user = None
            
            existing_session = BotSession.objects.filter(
                telegram_chat_id=telegram_chat_id,
                user__isnull=False
            ).first()
            
            if existing_session:
                user = existing_session.user
                logger.info(f"Found existing user for telegram_chat_id {telegram_chat_id}")
            
            elif phone_number:
                try:
                    user = User.objects.get(phone_number=phone_number)
                    
                    BotSession.objects.update_or_create(
                        telegram_chat_id=telegram_chat_id,
                        defaults={
                            'user': user,
                            'is_active': True,
                            'session_type': 'mixed'
                        }
                    )
                    logger.info(f"Linked existing user {phone_number} to telegram_chat_id {telegram_chat_id}")
                    
                except User.DoesNotExist:
                    user = User.objects.create(
                        phone_number=phone_number,
                        language='ru'
                    )
                    
                    BotSession.objects.create(
                        user=user,
                        telegram_chat_id=telegram_chat_id,
                        is_active=True,
                        session_type='mixed'
                    )
                    logger.info(f"Created new user {phone_number} for telegram_chat_id {telegram_chat_id}")
            
            else:
                user = User.objects.create(
                    phone_number=f"+{telegram_chat_id}",
                    language='ru'
                )
                
                BotSession.objects.create(
                    user=user,
                    telegram_chat_id=telegram_chat_id,
                    is_active=True,
                    session_type='mixed'
                )
                logger.info(f"Created temporary user for telegram_chat_id {telegram_chat_id}")
            
            refresh = RefreshToken.for_user(user)
            access_token = refresh.access_token
            
            return Response({
                'access': str(access_token),
                'refresh': str(refresh),
                'user': {
                    'id': str(user.id),
                    'phone_number': user.phone_number,
                    'language': user.language,
                    'is_active': user.is_active
                }
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Error in telegram login: {str(e)}")
            return Response({
                'error': 'Internal server error'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class TelegramAuthView(APIView):
    permission_classes = [AllowAny]
    
    def post(self, request):
        telegram_chat_id = request.data.get('telegram_chat_id')
        
        if not telegram_chat_id:
            return Response({
                'error': 'telegram_chat_id is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            session = BotSession.objects.filter(
                telegram_chat_id=telegram_chat_id,
                user__isnull=False,
                is_active=True
            ).first()
            
            if not session:
                return Response({
                    'error': 'User not found for this Telegram chat',
                    'requires_registration': True
                }, status=status.HTTP_404_NOT_FOUND)
            
            user = session.user
            refresh = RefreshToken.for_user(user)
            access_token = refresh.access_token
            
            return Response({
                'access': str(access_token),
                'refresh': str(refresh),
                'user': {
                    'id': str(user.id),
                    'phone_number': user.phone_number,
                    'language': user.language,
                    'is_active': user.is_active
                }
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Error in telegram auth: {str(e)}")
            return Response({
                'error': 'Internal server error'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([AllowAny])
def telegram_register(request):
    telegram_chat_id = request.data.get('telegram_chat_id')
    phone_number = request.data.get('phone_number')
    language = request.data.get('language', 'ru')
    
    if not all([telegram_chat_id, phone_number]):
        return Response({
            'error': 'telegram_chat_id and phone_number are required'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        existing_user = User.objects.filter(phone_number=phone_number).first()
        if existing_user:
            return Response({
                'error': 'User with this phone number already exists'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        user = User.objects.create(
            phone_number=phone_number,
            language=language
        )
        
        BotSession.objects.create(
            user=user,
            telegram_chat_id=telegram_chat_id,
            is_active=True,
            session_type='mixed'
        )
        
        refresh = RefreshToken.for_user(user)
        access_token = refresh.access_token
        
        return Response({
            'access': str(access_token),
            'refresh': str(refresh),
            'user': {
                'id': str(user.id),
                'phone_number': user.phone_number,
                'language': user.language,
                'is_active': user.is_active
            }
        }, status=status.HTTP_201_CREATED)
        
    except Exception as e:
        logger.error(f"Error in telegram register: {str(e)}")
        return Response({
            'error': 'Internal server error'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)