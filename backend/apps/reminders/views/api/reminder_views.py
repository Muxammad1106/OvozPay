"""
API views для модуля напоминаний и планировщика OvozPay
Этап 7: Reminders & Scheduler API
"""

import logging
from datetime import datetime, timedelta
from django.utils import timezone
from django.db.models import Q
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from apps.reminders.models import Reminder, ReminderHistory
from apps.reminders.serializers import (
    ReminderSerializer,
    ReminderCreateSerializer,
    ReminderUpdateSerializer,
    ReminderListSerializer,
    ReminderHistorySerializer,
    ReminderStatsSerializer,
    ReminderTypesSerializer,
    ReminderActivationSerializer,
    ReminderSendNowSerializer,
)
from apps.reminders.services.reminder_service import ReminderService

logger = logging.getLogger(__name__)


class ReminderViewSet(viewsets.ModelViewSet):
    """
    ViewSet для управления напоминаниями
    
    Поддерживает 12 эндпоинтов согласно ТЗ:
    1. GET /api/reminders/ - Список напоминаний пользователя
    2. POST /api/reminders/ - Создать напоминание
    3. GET /api/reminders/{id}/ - Получить детальную информацию
    4. PUT /api/reminders/{id}/ - Полное обновление
    5. PATCH /api/reminders/{id}/ - Частичное обновление
    6. DELETE /api/reminders/{id}/ - Удалить напоминание
    7. POST /api/reminders/{id}/activate/ - Активировать напоминание
    8. POST /api/reminders/{id}/deactivate/ - Деактивировать напоминание
    9. GET /api/reminders/upcoming/ - Ближайшие напоминания
    10. GET /api/reminders/history/ - История выполненных напоминаний
    11. POST /api/reminders/{id}/send-now/ - Отправить уведомление вручную
    12. GET /api/reminders/types/ - Список доступных типов
    """
    
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['reminder_type', 'repeat', 'is_active']
    search_fields = ['title', 'description']
    ordering_fields = ['created_at', 'scheduled_time', 'next_reminder']
    ordering = ['-created_at']
    
    def get_queryset(self):
        """Возвращает напоминания только для текущего пользователя"""
        return Reminder.objects.filter(user=self.request.user).select_related('goal')
    
    def get_serializer_class(self):
        """Выбор сериализатора в зависимости от действия"""
        if self.action == 'create':
            return ReminderCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return ReminderUpdateSerializer
        elif self.action == 'list':
            return ReminderListSerializer
        elif self.action == 'activate' or self.action == 'deactivate':
            return ReminderActivationSerializer
        elif self.action == 'send_now':
            return ReminderSendNowSerializer
        elif self.action == 'types':
            return ReminderTypesSerializer
        elif self.action == 'stats':
            return ReminderStatsSerializer
        else:
            return ReminderSerializer
    
    def create(self, request, *args, **kwargs):
        """Создание напоминания"""
        try:
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            
            reminder = serializer.save()
            
            # Возвращаем полную информацию о созданном напоминании
            response_serializer = ReminderSerializer(reminder, context={'request': request})
            
            logger.info(f"Создано напоминание {reminder.title} пользователем {request.user.phone_number}")
            
            return Response(
                response_serializer.data,
                status=status.HTTP_201_CREATED
            )
            
        except Exception as e:
            logger.error(f"Ошибка создания напоминания: {str(e)}")
            return Response(
                {'error': 'Ошибка создания напоминания'},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    def update(self, request, *args, **kwargs):
        """Полное обновление напоминания"""
        try:
            partial = kwargs.pop('partial', False)
            instance = self.get_object()
            serializer = self.get_serializer(instance, data=request.data, partial=partial)
            serializer.is_valid(raise_exception=True)
            
            reminder = serializer.save()
            
            # Возвращаем полную информацию об обновленном напоминании
            response_serializer = ReminderSerializer(reminder, context={'request': request})
            
            logger.info(f"Обновлено напоминание {reminder.title} пользователем {request.user.phone_number}")
            
            return Response(response_serializer.data)
            
        except Exception as e:
            logger.error(f"Ошибка обновления напоминания: {str(e)}")
            return Response(
                {'error': 'Ошибка обновления напоминания'},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    def destroy(self, request, *args, **kwargs):
        """Удаление напоминания"""
        try:
            instance = self.get_object()
            reminder_title = instance.title
            
            # Удаляем напоминание
            self.perform_destroy(instance)
            
            logger.info(f"Удалено напоминание {reminder_title} пользователем {request.user.phone_number}")
            
            return Response(
                {'message': f'Напоминание "{reminder_title}" успешно удалено'},
                status=status.HTTP_204_NO_CONTENT
            )
            
        except Exception as e:
            logger.error(f"Ошибка удаления напоминания: {str(e)}")
            return Response(
                {'error': 'Ошибка удаления напоминания'},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=True, methods=['post'])
    def activate(self, request, pk=None):
        """Активирует напоминание"""
        try:
            reminder = self.get_object()
            result = ReminderService.activate_reminder(reminder)
            
            return Response(result, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Ошибка активации напоминания: {str(e)}")
            return Response(
                {'error': 'Ошибка активации напоминания'},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=True, methods=['post'])
    def deactivate(self, request, pk=None):
        """Деактивирует напоминание"""
        try:
            reminder = self.get_object()
            result = ReminderService.deactivate_reminder(reminder)
            
            return Response(result, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Ошибка деактивации напоминания: {str(e)}")
            return Response(
                {'error': 'Ошибка деактивации напоминания'},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=False, methods=['get'])
    def upcoming(self, request):
        """Возвращает ближайшие напоминания (в течение 24 часов)"""
        try:
            now = timezone.now()
            upcoming_time = now + timedelta(hours=24)
            
            reminders = self.get_queryset().filter(
                Q(
                    Q(scheduled_time__range=(now, upcoming_time), last_sent__isnull=True) |
                    Q(next_reminder__range=(now, upcoming_time))
                ),
                is_active=True
            ).order_by('scheduled_time', 'next_reminder')
            
            serializer = ReminderListSerializer(reminders, many=True, context={'request': request})
            
            return Response({
                'count': reminders.count(),
                'results': serializer.data
            })
            
        except Exception as e:
            logger.error(f"Ошибка получения ближайших напоминаний: {str(e)}")
            return Response(
                {'error': 'Ошибка получения ближайших напоминаний'},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=False, methods=['get'])
    def history(self, request):
        """Возвращает историю выполненных напоминаний"""
        try:
            history = ReminderHistory.objects.filter(
                reminder__user=request.user
            ).select_related('reminder').order_by('-sent_at')
            
            # Пагинация
            page = self.paginate_queryset(history)
            if page is not None:
                serializer = ReminderHistorySerializer(page, many=True, context={'request': request})
                return self.get_paginated_response(serializer.data)
            
            serializer = ReminderHistorySerializer(history, many=True, context={'request': request})
            
            return Response({
                'count': history.count(),
                'results': serializer.data
            })
            
        except Exception as e:
            logger.error(f"Ошибка получения истории напоминаний: {str(e)}")
            return Response(
                {'error': 'Ошибка получения истории напоминаний'},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=True, methods=['post'])
    def send_now(self, request, pk=None):
        """Отправляет уведомление вручную"""
        try:
            reminder = self.get_object()
            
            # Отправляем напоминание вручную
            history = ReminderService.send_reminder_notification(reminder, manual=True)
            
            response_data = {
                'message': f'Напоминание "{reminder.title}" отправлено',
                'sent_at': history.sent_at,
                'telegram_message_id': history.telegram_message_id
            }
            
            return Response(response_data, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Ошибка отправки напоминания вручную: {str(e)}")
            return Response(
                {'error': 'Ошибка отправки напоминания'},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=False, methods=['get'])
    def types(self, request):
        """Возвращает список доступных типов напоминаний"""
        try:
            types_data = ReminderService.get_reminder_types()
            serializer = ReminderTypesSerializer(types_data)
            
            return Response(serializer.data)
            
        except Exception as e:
            logger.error(f"Ошибка получения типов напоминаний: {str(e)}")
            return Response(
                {'error': 'Ошибка получения типов напоминаний'},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=False, methods=['get'])
    def stats(self, request):
        """Возвращает статистику напоминаний пользователя"""
        try:
            stats_data = ReminderService.get_user_reminders_stats(request.user)
            serializer = ReminderStatsSerializer(stats_data)
            
            return Response(serializer.data)
            
        except Exception as e:
            logger.error(f"Ошибка получения статистики напоминаний: {str(e)}")
            return Response(
                {'error': 'Ошибка получения статистики напоминаний'},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=False, methods=['get'])
    def overdue(self, request):
        """Возвращает просроченные напоминания"""
        try:
            now = timezone.now()
            
            overdue_reminders = self.get_queryset().filter(
                scheduled_time__lt=now,
                is_active=True,
                last_sent__isnull=True
            ).order_by('scheduled_time')
            
            serializer = ReminderListSerializer(overdue_reminders, many=True, context={'request': request})
            
            return Response({
                'count': overdue_reminders.count(),
                'results': serializer.data
            })
            
        except Exception as e:
            logger.error(f"Ошибка получения просроченных напоминаний: {str(e)}")
            return Response(
                {'error': 'Ошибка получения просроченных напоминаний'},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=False, methods=['post'])
    def process_scheduled(self, request):
        """Обрабатывает все запланированные напоминания (для админов)"""
        try:
            # Проверяем, что пользователь имеет права администратора
            if not request.user.is_staff:
                return Response(
                    {'error': 'Недостаточно прав доступа'},
                    status=status.HTTP_403_FORBIDDEN
                )
            
            stats = ReminderService.process_scheduled_reminders()
            
            return Response(stats, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Ошибка обработки запланированных напоминаний: {str(e)}")
            return Response(
                {'error': 'Ошибка обработки запланированных напоминаний'},
                status=status.HTTP_400_BAD_REQUEST
            )


class ReminderHistoryViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet для работы с историей напоминаний (только чтение)
    """
    
    serializer_class = ReminderHistorySerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['status', 'reminder__reminder_type']
    ordering_fields = ['sent_at', 'created_at']
    ordering = ['-sent_at']
    
    def get_queryset(self):
        """Возвращает историю напоминаний только для текущего пользователя"""
        return ReminderHistory.objects.filter(
            reminder__user=self.request.user
        ).select_related('reminder')
    
    @action(detail=False, methods=['get'])
    def summary(self, request):
        """Возвращает сводку по истории напоминаний"""
        try:
            queryset = self.get_queryset()
            
            total_sent = queryset.count()
            successful = queryset.filter(status='sent').count()
            manual = queryset.filter(status='manual').count()
            failed = queryset.filter(status='failed').count()
            
            # Статистика за последние периоды
            now = timezone.now()
            today = now.date()
            week_start = today - timedelta(days=today.weekday())
            month_start = today.replace(day=1)
            
            sent_today = queryset.filter(sent_at__date=today).count()
            sent_this_week = queryset.filter(sent_at__date__gte=week_start).count()
            sent_this_month = queryset.filter(sent_at__date__gte=month_start).count()
            
            return Response({
                'total_sent': total_sent,
                'successful': successful,
                'manual': manual,
                'failed': failed,
                'sent_today': sent_today,
                'sent_this_week': sent_this_week,
                'sent_this_month': sent_this_month,
                'success_rate': round((successful / total_sent * 100), 2) if total_sent > 0 else 0
            })
            
        except Exception as e:
            logger.error(f"Ошибка получения сводки истории: {str(e)}")
            return Response(
                {'error': 'Ошибка получения сводки истории'},
                status=status.HTTP_400_BAD_REQUEST
            ) 