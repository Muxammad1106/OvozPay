"""
API Views для AI модуля OvozPay
OCR, Voice Recognition, Command Processing
"""

import logging
from typing import Dict, Any

from rest_framework import status, viewsets, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Q
from django.utils import timezone
from datetime import timedelta

from apps.ai.models import (
    OCRResult, OCRItem, VoiceResult, VoiceCommand, AIProcessingLog
)
from apps.ai.serializers import (
    OCRResultSerializer, OCRUploadSerializer, OCRItemSerializer,
    VoiceResultSerializer, VoiceUploadSerializer, VoiceCommandSerializer,
    AIProcessingLogSerializer, OCRAnalysisSerializer, AIServiceStatusSerializer,
    ReceiptMatchingSerializer, SupportedCommandsSerializer, CommandListSerializer,
    OCRItemUpdateSerializer, BulkReceiptProcessingSerializer, ReceiptStatsSerializer
)
from apps.ai.services.ocr.tesseract_service import TesseractOCRService
from apps.ai.services.voice.whisper_service import WhisperVoiceService
from apps.ai.services.nlp.command_processor import VoiceCommandProcessor
from apps.ai.services.nlp.category_matcher import CategoryMatcher
from apps.core.permissions import IsOwnerOrReadOnly


logger = logging.getLogger(__name__)


class OCRResultViewSet(viewsets.ModelViewSet):
    """ViewSet для результатов OCR обработки"""
    
    serializer_class = OCRResultSerializer
    permission_classes = [permissions.IsAuthenticated, IsOwnerOrReadOnly]
    parser_classes = [MultiPartParser, FormParser]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['status', 'shop_name', 'language_detected']
    search_fields = ['shop_name', 'processed_text', 'receipt_number']
    ordering_fields = ['created_at', 'processing_time', 'total_amount']
    ordering = ['-created_at']
    
    def get_queryset(self):
        """Получение результатов OCR для текущего пользователя"""
        return OCRResult.objects.filter(
            user=self.request.user
        ).prefetch_related('items', 'items__category')
    
    def create(self, request, *args, **kwargs):
        """Создание нового OCR результата (загрузка изображения)"""
        serializer = OCRUploadSerializer(data=request.data)
        if serializer.is_valid():
            try:
                # Инициализируем OCR сервис
                ocr_service = TesseractOCRService()
                
                # Обрабатываем изображение
                ocr_result = ocr_service.process_receipt_image(
                    user=request.user,
                    image_file=serializer.validated_data['image'],
                    recognition_type=serializer.validated_data['recognition_type']
                )
                
                # Возвращаем результат
                result_serializer = OCRResultSerializer(ocr_result)
                return Response(
                    result_serializer.data, 
                    status=status.HTTP_201_CREATED
                )
                
            except Exception as e:
                logger.error(f"OCR processing error: {e}")
                return Response(
                    {'error': f'OCR processing failed: {str(e)}'},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['get'])
    def analysis(self, request, pk=None):
        """Анализ категорий для OCR результата"""
        try:
            ocr_result = self.get_object()
            
            if ocr_result.status != 'completed':
                return Response(
                    {'error': 'OCR processing not completed yet'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Получаем позиции чека
            items = ocr_result.items.all()
            items_data = [
                {
                    'name': item.name,
                    'total_price': item.total_price,
                    'category': item.category.name if item.category else None
                }
                for item in items
            ]
            
            # Анализируем категории
            category_matcher = CategoryMatcher()
            analysis_result = category_matcher.analyze_receipt_categories(
                items_data, request.user, ocr_result.shop_name
            )
            
            # Добавляем предложения категорий
            analysis_result['suggestions'] = category_matcher.suggest_categories_for_user(
                request.user, limit=5
            )
            
            serializer = OCRAnalysisSerializer(analysis_result)
            return Response(serializer.data)
            
        except Exception as e:
            logger.error(f"OCR analysis error: {e}")
            return Response(
                {'error': f'Analysis failed: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['post'])
    def bulk_process(self, request):
        """Массовая обработка чеков"""
        serializer = BulkReceiptProcessingSerializer(data=request.data)
        if serializer.is_valid():
            try:
                ocr_service = TesseractOCRService()
                results = []
                
                for image in serializer.validated_data['images']:
                    ocr_result = ocr_service.process_receipt_image(
                        user=request.user,
                        image_file=image,
                        recognition_type=serializer.validated_data['recognition_type']
                    )
                    results.append(OCRResultSerializer(ocr_result).data)
                
                return Response({
                    'results': results,
                    'total_processed': len(results)
                }, status=status.HTTP_201_CREATED)
                
            except Exception as e:
                logger.error(f"Bulk OCR processing error: {e}")
                return Response(
                    {'error': f'Bulk processing failed: {str(e)}'},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['get'])
    def stats(self, request):
        """Статистика по OCR обработке"""
        serializer = ReceiptStatsSerializer(data=request.query_params)
        if serializer.is_valid():
            period = serializer.validated_data['period']
            
            # Определяем период
            now = timezone.now()
            if period == 'day':
                start_date = now - timedelta(days=1)
            elif period == 'week':
                start_date = now - timedelta(weeks=1)
            elif period == 'month':
                start_date = now - timedelta(days=30)
            else:  # year
                start_date = now - timedelta(days=365)
            
            # Получаем статистику
            queryset = self.get_queryset().filter(created_at__gte=start_date)
            
            from django.db.models import Count, Sum, Avg
            
            stats = queryset.aggregate(
                total_processed=Count('id'),
                completed=Count('id', filter=Q(status='completed')),
                failed=Count('id', filter=Q(status='failed')),
                total_amount=Sum('total_amount'),
                avg_processing_time=Avg('processing_time'),
                avg_confidence=Avg('confidence_score')
            )
            
            # Статистика по магазинам
            shop_stats = queryset.values('shop_name').annotate(
                count=Count('id'),
                total=Sum('total_amount')
            ).order_by('-count')[:10]
            
            return Response({
                'period': period,
                'stats': stats,
                'top_shops': list(shop_stats),
                'success_rate': (stats['completed'] / stats['total_processed'] * 100) if stats['total_processed'] > 0 else 0
            })
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class OCRItemViewSet(viewsets.ModelViewSet):
    """ViewSet для позиций чеков OCR"""
    
    serializer_class = OCRItemSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['category', 'ocr_result']
    search_fields = ['name']
    ordering_fields = ['line_number', 'total_price']
    ordering = ['line_number']
    
    def get_queryset(self):
        """Получение позиций чеков для текущего пользователя"""
        return OCRItem.objects.filter(
            ocr_result__user=self.request.user
        ).select_related('category', 'ocr_result')
    
    def get_serializer_class(self):
        """Выбор сериализатора в зависимости от действия"""
        if self.action in ['update', 'partial_update']:
            return OCRItemUpdateSerializer
        return super().get_serializer_class()
    
    @action(detail=True, methods=['post'])
    def update_category(self, request, pk=None):
        """Обновление категории позиции"""
        item = self.get_object()
        serializer = OCRItemUpdateSerializer(
            item, 
            data=request.data, 
            partial=True,
            context={'request': request}
        )
        
        if serializer.is_valid():
            serializer.save()
            return Response(OCRItemSerializer(item).data)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class VoiceResultViewSet(viewsets.ModelViewSet):
    """ViewSet для результатов распознавания голоса"""
    
    serializer_class = VoiceResultSerializer
    permission_classes = [permissions.IsAuthenticated, IsOwnerOrReadOnly]
    parser_classes = [MultiPartParser, FormParser]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['status', 'recognition_type', 'language_detected']
    search_fields = ['recognized_text', 'original_filename']
    ordering_fields = ['created_at', 'duration', 'confidence_score']
    ordering = ['-created_at']
    
    def get_queryset(self):
        """Получение результатов Voice для текущего пользователя"""
        return VoiceResult.objects.filter(
            user=self.request.user
        ).select_related('ocr_result')
    
    def create(self, request, *args, **kwargs):
        """Создание нового Voice результата (загрузка аудио)"""
        serializer = VoiceUploadSerializer(
            data=request.data, 
            context={'request': request}
        )
        
        if serializer.is_valid():
            try:
                # Инициализируем Voice сервис
                voice_service = WhisperVoiceService()
                
                # Обрабатываем аудио
                voice_result = voice_service.process_voice_message(
                    user=request.user,
                    audio_file=serializer.validated_data['audio'],
                    recognition_type=serializer.validated_data['recognition_type']
                )
                
                # Связываем с OCR результатом если указан
                ocr_result_id = serializer.validated_data.get('ocr_result_id')
                if ocr_result_id:
                    voice_result.ocr_result_id = ocr_result_id
                    voice_result.save()
                
                # Возвращаем результат
                result_serializer = VoiceResultSerializer(voice_result)
                return Response(
                    result_serializer.data, 
                    status=status.HTTP_201_CREATED
                )
                
            except Exception as e:
                logger.error(f"Voice processing error: {e}")
                return Response(
                    {'error': f'Voice processing failed: {str(e)}'},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'])
    def reprocess_command(self, request, pk=None):
        """Повторная обработка как голосовой команды"""
        try:
            voice_result = self.get_object()
            
            if voice_result.status != 'completed':
                return Response(
                    {'error': 'Voice recognition not completed yet'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Обрабатываем как команду
            command_processor = VoiceCommandProcessor()
            command = command_processor.parse_command(
                voice_result.recognized_text,
                voice_result.language_detected,
                request.user
            )
            
            if command:
                # Создаем или обновляем команду
                voice_command, created = VoiceCommand.objects.get_or_create(
                    voice_result=voice_result,
                    defaults={
                        'command_type': command['type'],
                        'command_text': voice_result.recognized_text,
                        'extracted_params': command['params'],
                        'confidence_score': command['confidence']
                    }
                )
                
                if not created:
                    voice_command.command_type = command['type']
                    voice_command.extracted_params = command['params']
                    voice_command.confidence_score = command['confidence']
                    voice_command.save()
                
                # Выполняем команду
                execution_result = command_processor.execute_command(voice_command)
                voice_command.mark_executed(execution_result)
                
                return Response({
                    'command': VoiceCommandSerializer(voice_command).data,
                    'execution_result': execution_result
                })
            else:
                return Response(
                    {'error': 'No command found in voice message'},
                    status=status.HTTP_400_BAD_REQUEST
                )
                
        except Exception as e:
            logger.error(f"Command reprocessing error: {e}")
            return Response(
                {'error': f'Command reprocessing failed: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class VoiceCommandViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet для голосовых команд (только чтение)"""
    
    serializer_class = VoiceCommandSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['command_type', 'execution_status']
    search_fields = ['command_text', 'extracted_params']
    ordering_fields = ['created_at', 'executed_at', 'confidence_score']
    ordering = ['-created_at']
    
    def get_queryset(self):
        """Получение команд для текущего пользователя"""
        return VoiceCommand.objects.filter(
            voice_result__user=self.request.user
        ).select_related('voice_result')
    
    @action(detail=True, methods=['post'])
    def retry_execution(self, request, pk=None):
        """Повторное выполнение команды"""
        try:
            voice_command = self.get_object()
            
            if voice_command.execution_status == 'executed':
                return Response(
                    {'error': 'Command already executed successfully'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Повторно выполняем команду
            command_processor = VoiceCommandProcessor()
            execution_result = command_processor.execute_command(voice_command)
            voice_command.mark_executed(execution_result)
            
            return Response({
                'command': VoiceCommandSerializer(voice_command).data,
                'execution_result': execution_result
            })
            
        except Exception as e:
            logger.error(f"Command retry error: {e}")
            voice_command.mark_failed(str(e))
            return Response(
                {'error': f'Command retry failed: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class AIProcessingLogViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet для логов обработки AI (только чтение)"""
    
    serializer_class = AIProcessingLogSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['operation_type', 'level']
    search_fields = ['message']
    ordering_fields = ['created_at', 'execution_time']
    ordering = ['-created_at']
    
    def get_queryset(self):
        """Получение логов для текущего пользователя"""
        return AIProcessingLog.objects.filter(
            user=self.request.user
        ).select_related('ocr_result', 'voice_result')


class AIServiceViewSet(viewsets.ViewSet):
    """ViewSet для управления AI сервисами"""
    
    permission_classes = [permissions.IsAuthenticated]
    
    @action(detail=False, methods=['get'])
    def status(self, request):
        """Получение статуса AI сервисов"""
        try:
            # Проверяем OCR сервис
            ocr_service = TesseractOCRService()
            
            # Проверяем Voice сервис
            voice_service = WhisperVoiceService()
            voice_status = voice_service.get_processing_status()
            
            status_data = {
                'ocr_available': True,  # OCR всегда доступен если Tesseract установлен
                'voice_recognition_available': voice_status['whisper_available'],
                'tesseract_version': 'Available',
                'whisper_model': voice_status.get('model_path', 'Not available'),
                'supported_languages': voice_status['supported_languages'],
                'supported_image_formats': ocr_service.get_supported_formats(),
                'supported_audio_formats': voice_status['supported_formats']
            }
            
            serializer = AIServiceStatusSerializer(status_data)
            return Response(serializer.data)
            
        except Exception as e:
            logger.error(f"Service status error: {e}")
            return Response(
                {'error': f'Could not get service status: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['get'])
    def supported_commands(self, request):
        """Получение списка поддерживаемых команд"""
        serializer = SupportedCommandsSerializer(data=request.query_params)
        if serializer.is_valid():
            try:
                language = serializer.validated_data['language']
                
                command_processor = VoiceCommandProcessor()
                commands = command_processor.get_supported_commands(language)
                
                response_serializer = CommandListSerializer(commands, many=True)
                return Response({
                    'language': language,
                    'commands': response_serializer.data
                })
                
            except Exception as e:
                logger.error(f"Supported commands error: {e}")
                return Response(
                    {'error': f'Could not get supported commands: {str(e)}'},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['post'])
    def match_receipt_voice(self, request):
        """Сопоставление чека и голосового описания"""
        serializer = ReceiptMatchingSerializer(
            data=request.data, 
            context={'request': request}
        )
        
        if serializer.is_valid():
            try:
                ocr_result_id = serializer.validated_data['ocr_result_id']
                voice_result_id = serializer.validated_data['voice_result_id']
                
                # Получаем объекты
                ocr_result = OCRResult.objects.get(id=ocr_result_id)
                voice_result = VoiceResult.objects.get(id=voice_result_id)
                
                # Связываем голосовой результат с OCR
                voice_result.ocr_result = ocr_result
                voice_result.save()
                
                # Анализируем соответствие
                category_matcher = CategoryMatcher()
                
                # Получаем позиции OCR
                ocr_items = [{
                    'name': item.name,
                    'total_price': item.total_price
                } for item in ocr_result.items.all()]
                
                # Анализируем голосовое описание на предмет упоминания товаров
                voice_text = voice_result.recognized_text.lower()
                matched_items = []
                
                for item in ocr_items:
                    if any(word in voice_text for word in item['name'].lower().split()):
                        matched_items.append(item)
                
                return Response({
                    'ocr_result': OCRResultSerializer(ocr_result).data,
                    'voice_result': VoiceResultSerializer(voice_result).data,
                    'matched_items': matched_items,
                    'matching_score': len(matched_items) / len(ocr_items) if ocr_items else 0
                })
                
            except Exception as e:
                logger.error(f"Receipt matching error: {e}")
                return Response(
                    {'error': f'Receipt matching failed: {str(e)}'},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST) 