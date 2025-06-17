"""
API Views для AI сервисов OvozPay
Обработка OCR, голосовых сообщений и их сопоставления
"""

from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser
from django.core.files.uploadedfile import InMemoryUploadedFile, TemporaryUploadedFile

from apps.ai.models import OCRResult, VoiceResult, ReceiptVoiceMatch
from apps.ai.api.serializers import (
    OCRResultSerializer, VoiceResultSerializer, ReceiptVoiceMatchSerializer
)
from apps.ai.services.ocr.tesseract_service import TesseractOCRService
from apps.ai.services.voice.whisper_service import WhisperVoiceService
from apps.ai.services.nlp.receipt_matcher import ReceiptVoiceMatcher


class OCRViewSet(viewsets.ModelViewSet):
    """ViewSet для OCR обработки чеков"""
    
    serializer_class = OCRResultSerializer
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]
    
    def get_queryset(self):
        return OCRResult.objects.filter(user=self.request.user)
    
    @action(detail=False, methods=['post'], url_path='scan-receipt')
    def scan_receipt(self, request):
        """
        OCR сканирование чека
        
        POST /api/ai/ocr/scan-receipt/
        
        Form data:
        - image: файл изображения
        - recognition_type: тип распознавания (optional, default='receipt')
        """
        # Проверяем наличие изображения
        if 'image' not in request.FILES:
            return Response(
                {'error': 'Требуется изображение для обработки'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        image_file = request.FILES['image']
        recognition_type = request.data.get('recognition_type', 'receipt')
        
        # Инициализируем OCR сервис
        ocr_service = TesseractOCRService()
        
        # Валидируем изображение
        is_valid, error_message = self._validate_image(image_file)
        if not is_valid:
            return Response(
                {'error': error_message},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            # Выполняем OCR обработку
            ocr_result = ocr_service.process_receipt_image(
                user=request.user,
                image_file=image_file,
                recognition_type=recognition_type
            )
            
            # Сериализуем результат
            serializer = OCRResultSerializer(ocr_result)
            
            return Response({
                'success': True,
                'message': 'OCR обработка завершена',
                'data': serializer.data
            }, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            return Response(
                {'error': f'Ошибка обработки изображения: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['get'], url_path='processing-status')
    def processing_status(self, request):
        """
        Статус OCR сервиса
        
        GET /api/ai/ocr/processing-status/
        """
        ocr_service = TesseractOCRService()
        status_info = ocr_service.get_processing_status()
        
        return Response({
            'success': True,
            'data': status_info
        })
    
    def _validate_image(self, image_file):
        """Валидация изображения"""
        # Проверка размера файла (макс 10MB)
        max_size = 10 * 1024 * 1024
        if image_file.size > max_size:
            return False, "Размер файла не должен превышать 10MB"
        
        # Проверка формата
        allowed_types = ['image/jpeg', 'image/png', 'image/bmp', 'image/tiff']
        if image_file.content_type not in allowed_types:
            return False, f"Неподдерживаемый формат. Используйте: {', '.join(allowed_types)}"
        
        return True, ""


class VoiceViewSet(viewsets.ModelViewSet):
    """ViewSet для обработки голосовых сообщений"""
    
    serializer_class = VoiceResultSerializer
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]
    
    def get_queryset(self):
        return VoiceResult.objects.filter(user=self.request.user)
    
    @action(detail=False, methods=['post'], url_path='recognize')
    def recognize(self, request):
        """
        Распознавание голосового сообщения
        
        POST /api/ai/voice/recognize/
        
        Form data:
        - audio: аудио файл
        - language: язык распознавания (optional, default='auto')
        - task: тип задачи (optional, default='transcribe')
        """
        # Проверяем наличие аудио файла
        if 'audio' not in request.FILES:
            return Response(
                {'error': 'Требуется аудио файл для обработки'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        audio_file = request.FILES['audio']
        language = request.data.get('language', 'auto')
        task = request.data.get('task', 'transcribe')
        
        # Инициализируем сервис распознавания речи
        whisper_service = WhisperVoiceService()
        
        # Валидируем аудио файл
        is_valid, error_message = whisper_service.validate_audio_file(audio_file)
        if not is_valid:
            return Response(
                {'error': error_message},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            # Выполняем распознавание
            voice_result = whisper_service.recognize_voice(
                user=request.user,
                audio_file=audio_file,
                language=language,
                task=task
            )
            
            # Сериализуем результат
            serializer = VoiceResultSerializer(voice_result)
            
            return Response({
                'success': True,
                'message': 'Распознавание голоса завершено',
                'data': serializer.data
            }, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            return Response(
                {'error': f'Ошибка обработки аудио: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['get'], url_path='processing-status')
    def processing_status(self, request):
        """
        Статус Voice сервиса
        
        GET /api/ai/voice/processing-status/
        """
        whisper_service = WhisperVoiceService()
        status_info = whisper_service.get_processing_status()
        
        return Response({
            'success': True,
            'data': status_info
        })
    
    @action(detail=False, methods=['get'], url_path='supported-languages')
    def supported_languages(self, request):
        """
        Поддерживаемые языки
        
        GET /api/ai/voice/supported-languages/
        """
        whisper_service = WhisperVoiceService()
        languages = whisper_service.get_supported_languages()
        
        return Response({
            'success': True,
            'data': {
                'languages': languages,
                'models': whisper_service.get_available_models()
            }
        })


class ReceiptVoiceMatchViewSet(viewsets.ModelViewSet):
    """ViewSet для сопоставления голосовых сообщений с чеками"""
    
    serializer_class = ReceiptVoiceMatchSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return ReceiptVoiceMatch.objects.filter(user=self.request.user)
    
    @action(detail=False, methods=['post'], url_path='match-with-receipt')
    def match_with_receipt(self, request):
        """
        Сопоставление голосового сообщения с чеком
        
        POST /api/ai/voice/match-with-receipt/
        
        JSON data:
        - voice_result_id: ID результата распознавания голоса
        - ocr_result_id: ID результата OCR чека
        """
        voice_result_id = request.data.get('voice_result_id')
        ocr_result_id = request.data.get('ocr_result_id')
        
        if not voice_result_id or not ocr_result_id:
            return Response(
                {'error': 'Требуются voice_result_id и ocr_result_id'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            # Получаем объекты
            voice_result = VoiceResult.objects.get(
                id=voice_result_id, 
                user=request.user
            )
            ocr_result = OCRResult.objects.get(
                id=ocr_result_id, 
                user=request.user
            )
            
            # Инициализируем сервис сопоставления
            matcher = ReceiptVoiceMatcher()
            
            # Выполняем сопоставление
            match_result = matcher.match_voice_with_receipt(
                voice_result, ocr_result
            )
            
            # Сериализуем результат
            serializer = ReceiptVoiceMatchSerializer(match_result)
            
            return Response({
                'success': True,
                'message': 'Сопоставление выполнено',
                'data': serializer.data
            }, status=status.HTTP_201_CREATED)
            
        except VoiceResult.DoesNotExist:
            return Response(
                {'error': 'Результат распознавания голоса не найден'},
                status=status.HTTP_404_NOT_FOUND
            )
        except OCRResult.DoesNotExist:
            return Response(
                {'error': 'Результат OCR не найден'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {'error': f'Ошибка сопоставления: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['post'], url_path='auto-match')
    def auto_match(self, request):
        """
        Автоматическое сопоставление голосового сообщения с недавними чеками
        
        POST /api/ai/voice/auto-match/
        
        JSON data:
        - voice_result_id: ID результата распознавания голоса
        - time_window_minutes: временное окно поиска (optional, default=5)
        """
        voice_result_id = request.data.get('voice_result_id')
        time_window_minutes = request.data.get('time_window_minutes', 5)
        
        if not voice_result_id:
            return Response(
                {'error': 'Требуется voice_result_id'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            # Получаем результат распознавания голоса
            voice_result = VoiceResult.objects.get(
                id=voice_result_id, 
                user=request.user
            )
            
            # Инициализируем сервис сопоставления
            matcher = ReceiptVoiceMatcher()
            
            # Выполняем автоматическое сопоставление
            matches = matcher.auto_match_recent_receipts(voice_result)
            
            # Сериализуем результаты
            serializer = ReceiptVoiceMatchSerializer(matches, many=True)
            
            return Response({
                'success': True,
                'message': f'Найдено {len(matches)} сопоставлений',
                'data': {
                    'matches_count': len(matches),
                    'matches': serializer.data
                }
            })
            
        except VoiceResult.DoesNotExist:
            return Response(
                {'error': 'Результат распознавания голоса не найден'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {'error': f'Ошибка автоматического сопоставления: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['get'], url_path='recent-matches')
    def recent_matches(self, request):
        """
        Недавние сопоставления пользователя
        
        GET /api/ai/voice/recent-matches/
        
        Query params:
        - limit: количество результатов (default=10)
        - min_confidence: минимальная уверенность (default=0.5)
        """
        limit = int(request.query_params.get('limit', 10))
        min_confidence = float(request.query_params.get('min_confidence', 0.5))
        
        matches = self.get_queryset().filter(
            confidence_score__gte=min_confidence,
            status='completed'
        )[:limit]
        
        serializer = ReceiptVoiceMatchSerializer(matches, many=True)
        
        return Response({
            'success': True,
            'data': {
                'matches_count': len(matches),
                'matches': serializer.data
            }
        })
    
    @action(detail=False, methods=['get'], url_path='processing-status')
    def processing_status(self, request):
        """
        Статус сервиса сопоставления
        
        GET /api/ai/voice/processing-status/
        """
        matcher = ReceiptVoiceMatcher()
        status_info = matcher.get_processing_status()
        
        return Response({
            'success': True,
            'data': status_info
        }) 