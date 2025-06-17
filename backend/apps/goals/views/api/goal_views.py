"""
API Views для модуля целей и накоплений OvozPay
Этап 6: Goals & Savings API
"""

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters
from django.db.models import Q
from django.core.exceptions import ValidationError as DjangoValidationError
from apps.goals.models import Goal, GoalTransaction
from apps.goals.serializers import (
    GoalSerializer,
    GoalCreateSerializer,
    GoalTransactionSerializer,
    GoalProgressSerializer,
    GoalStatsSerializer,
    GoalCompleteSerializer,
    GoalStatusUpdateSerializer
)
from apps.goals.services import GoalService
import logging
from django.utils import timezone

logger = logging.getLogger(__name__)


class GoalViewSet(viewsets.ModelViewSet):
    """ViewSet для управления целями"""
    
    serializer_class = GoalSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['status', 'reminder_interval']
    search_fields = ['title', 'description']
    ordering_fields = ['created_at', 'deadline', 'target_amount', 'current_amount', 'progress_percentage']
    ordering = ['-created_at']
    
    def get_queryset(self):
        """Возвращает цели только для текущего пользователя"""
        return Goal.objects.filter(user=self.request.user).select_related('user')
    
    def get_serializer_class(self):
        """Возвращает соответствующий сериализатор в зависимости от действия"""
        if self.action == 'create':
            return GoalCreateSerializer
        elif self.action == 'add_progress':
            return GoalProgressSerializer
        elif self.action == 'complete_goal':
            return GoalCompleteSerializer
        elif self.action == 'update_status':
            return GoalStatusUpdateSerializer
        return GoalSerializer
    
    def create(self, request, *args, **kwargs):
        """Создание новой цели"""
        try:
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            
            # Создаем цель через сервис для Telegram уведомлений
            goal = GoalService.create_goal(
                user=request.user,
                title=serializer.validated_data['title'],
                target_amount=serializer.validated_data['target_amount'],
                deadline=serializer.validated_data['deadline'],
                description=serializer.validated_data.get('description', ''),
                reminder_interval=serializer.validated_data.get('reminder_interval', 'weekly')
            )
            
            # Сериализуем созданную цель
            response_serializer = GoalSerializer(goal, context={'request': request})
            
            return Response(
                response_serializer.data,
                status=status.HTTP_201_CREATED
            )
            
        except Exception as e:
            logger.error(f"Ошибка создания цели: {str(e)}")
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    def list(self, request, *args, **kwargs):
        """Список целей с дополнительными фильтрами"""
        queryset = self.filter_queryset(self.get_queryset())
        
        # Дополнительные фильтры
        is_overdue = request.query_params.get('is_overdue')
        is_completed = request.query_params.get('is_completed')
        is_active = request.query_params.get('is_active')
        
        if is_overdue == 'true':
            queryset = queryset.filter(
                status='active',
                deadline__lt=timezone.now().date()
            )
        elif is_completed == 'true':
            queryset = queryset.filter(status='completed')
        elif is_active == 'true':
            queryset = queryset.filter(status='active')
        
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def add_progress(self, request, pk=None):
        """Добавляет прогресс к цели"""
        try:
            goal = self.get_object()
            serializer = self.get_serializer(
                data=request.data,
                context={'goal': goal, 'request': request}
            )
            serializer.is_valid(raise_exception=True)
            
            amount = serializer.validated_data['amount']
            description = serializer.validated_data.get('description', '')
            withdraw_from_balance = request.data.get('withdraw_from_balance', True)
            
            # Добавляем прогресс через сервис
            goal_transaction = GoalService.add_progress_to_goal(
                goal=goal,
                amount=amount,
                description=description,
                withdraw_from_balance=withdraw_from_balance
            )
            
            # Возвращаем обновленную цель и транзакцию
            goal.refresh_from_db()
            goal_serializer = GoalSerializer(goal, context={'request': request})
            transaction_serializer = GoalTransactionSerializer(
                goal_transaction,
                context={'request': request}
            )
            
            return Response({
                'goal': goal_serializer.data,
                'transaction': transaction_serializer.data,
                'message': 'Прогресс успешно добавлен'
            }, status=status.HTTP_200_OK)
            
        except DjangoValidationError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            logger.error(f"Ошибка добавления прогресса: {str(e)}")
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=True, methods=['post'])
    def complete_goal(self, request, pk=None):
        """Завершает цель досрочно"""
        try:
            goal = self.get_object()
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            
            force = serializer.validated_data.get('force', False)
            reason = serializer.validated_data.get('reason', '')
            
            # Завершаем цель через сервис
            GoalService.complete_goal(goal, force=force, reason=reason)
            
            # Возвращаем обновленную цель
            goal.refresh_from_db()
            goal_serializer = GoalSerializer(goal, context={'request': request})
            
            return Response({
                'goal': goal_serializer.data,
                'message': 'Цель успешно завершена'
            }, status=status.HTTP_200_OK)
            
        except DjangoValidationError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            logger.error(f"Ошибка завершения цели: {str(e)}")
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=True, methods=['post'])
    def update_status(self, request, pk=None):
        """Обновляет статус цели"""
        try:
            goal = self.get_object()
            serializer = self.get_serializer(
                data=request.data,
                context={'goal': goal}
            )
            serializer.is_valid(raise_exception=True)
            
            new_status = serializer.validated_data['status']
            reason = serializer.validated_data.get('reason', '')
            
            # Обновляем статус в зависимости от типа
            if new_status == 'completed':
                GoalService.complete_goal(goal, force=True, reason=reason)
            elif new_status == 'failed':
                GoalService.fail_goal(goal, reason=reason)
            elif new_status == 'paused':
                goal.pause_goal()
            elif new_status == 'active':
                goal.resume_goal()
            
            # Возвращаем обновленную цель
            goal.refresh_from_db()
            goal_serializer = GoalSerializer(goal, context={'request': request})
            
            return Response({
                'goal': goal_serializer.data,
                'message': f'Статус цели изменен на "{goal.get_status_display()}"'
            }, status=status.HTTP_200_OK)
            
        except DjangoValidationError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            logger.error(f"Ошибка обновления статуса цели: {str(e)}")
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=False, methods=['get'])
    def stats(self, request):
        """Возвращает статистику целей пользователя"""
        try:
            stats_data = GoalService.get_user_goals_stats(request.user)
            serializer = GoalStatsSerializer(stats_data)
            
            return Response(serializer.data, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Ошибка получения статистики целей: {str(e)}")
            return Response(
                {'error': 'Ошибка получения статистики'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['get'])
    def overdue(self, request):
        """Возвращает просроченные цели"""
        try:
            overdue_goals = self.get_queryset().filter(
                status='active',
                deadline__lt=timezone.now().date()
            )
            
            serializer = GoalSerializer(overdue_goals, many=True, context={'request': request})
            
            return Response({
                'count': overdue_goals.count(),
                'goals': serializer.data
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Ошибка получения просроченных целей: {str(e)}")
            return Response(
                {'error': 'Ошибка получения просроченных целей'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['post'])
    def check_overdue(self, request):
        """Проверяет и обновляет просроченные цели"""
        try:
            updated_count = GoalService.check_and_update_overdue_goals()
            
            return Response({
                'message': f'Обновлено {updated_count} просроченных целей',
                'updated_count': updated_count
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Ошибка проверки просроченных целей: {str(e)}")
            return Response(
                {'error': 'Ошибка проверки просроченных целей'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class GoalTransactionViewSet(viewsets.ModelViewSet):
    """ViewSet для управления транзакциями целей"""
    
    serializer_class = GoalTransactionSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['goal', 'telegram_notified']
    search_fields = ['description', 'goal__title']
    ordering_fields = ['created_at', 'amount']
    ordering = ['-created_at']
    http_method_names = ['get', 'post', 'head', 'options']  # Только чтение и создание
    
    def get_queryset(self):
        """Возвращает транзакции целей только для текущего пользователя"""
        return GoalTransaction.objects.filter(
            goal__user=self.request.user
        ).select_related('goal', 'goal__user')
    
    def create(self, request, *args, **kwargs):
        """Создание новой транзакции пополнения цели"""
        try:
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            
            goal = serializer.validated_data['goal']
            amount = serializer.validated_data['amount']
            description = serializer.validated_data.get('description', '')
            withdraw_from_balance = request.data.get('withdraw_from_balance', True)
            
            # Создаем транзакцию через сервис
            goal_transaction = GoalService.add_progress_to_goal(
                goal=goal,
                amount=amount,
                description=description,
                withdraw_from_balance=withdraw_from_balance
            )
            
            # Сериализуем созданную транзакцию
            response_serializer = GoalTransactionSerializer(
                goal_transaction,
                context={'request': request}
            )
            
            return Response(
                response_serializer.data,
                status=status.HTTP_201_CREATED
            )
            
        except DjangoValidationError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            logger.error(f"Ошибка создания транзакции цели: {str(e)}")
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    def list(self, request, *args, **kwargs):
        """Список транзакций с дополнительными фильтрами"""
        queryset = self.filter_queryset(self.get_queryset())
        
        # Фильтрация по цели
        goal_id = request.query_params.get('goal_id')
        if goal_id:
            queryset = queryset.filter(goal__id=goal_id)
        
        # Фильтрация по диапазону дат
        date_from = request.query_params.get('date_from')
        date_to = request.query_params.get('date_to')
        
        if date_from:
            queryset = queryset.filter(created_at__date__gte=date_from)
        if date_to:
            queryset = queryset.filter(created_at__date__lte=date_to)
        
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def summary(self, request):
        """Возвращает сводку по транзакциям пользователя"""
        try:
            from django.db.models import Sum, Count
            
            queryset = self.get_queryset()
            
            # Общая статистика
            total_transactions = queryset.count()
            total_amount = queryset.aggregate(
                total=Sum('amount')
            )['total'] or 0
            
            # Статистика за текущий месяц
            current_month = timezone.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            month_transactions = queryset.filter(created_at__gte=current_month)
            month_count = month_transactions.count()
            month_amount = month_transactions.aggregate(
                total=Sum('amount')
            )['total'] or 0
            
            # Статистика по целям
            goal_stats = queryset.values('goal__title', 'goal__id').annotate(
                transaction_count=Count('id'),
                total_amount=Sum('amount')
            ).order_by('-total_amount')[:5]
            
            return Response({
                'total_transactions': total_transactions,
                'total_amount': total_amount,
                'this_month_transactions': month_count,
                'this_month_amount': month_amount,
                'top_goals': goal_stats
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Ошибка получения сводки транзакций: {str(e)}")
            return Response(
                {'error': 'Ошибка получения сводки'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            ) 