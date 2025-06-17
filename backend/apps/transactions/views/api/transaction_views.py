from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from django.db.models import Sum, Q
from decimal import Decimal
from django.core.exceptions import ValidationError
from django.utils import timezone

from apps.transactions.models import Transaction, DebtTransaction
from apps.transactions.serializers import (
    TransactionSerializer, 
    DebtTransactionSerializer,
    DebtPaymentSerializer,
    TransactionStatsSerializer,
    TransactionCreateSerializer
)
from apps.transactions.services import TransactionService
from apps.users.models import User
import logging

logger = logging.getLogger(__name__)


class TransactionViewSet(viewsets.ModelViewSet):
    """ViewSet для управления транзакциями"""
    
    queryset = Transaction.objects.all()
    serializer_class = TransactionSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['type', 'category', 'source', 'is_closed', 'telegram_notified']
    search_fields = ['description', 'amount']
    ordering_fields = ['date', 'amount', 'created_at']
    ordering = ['-date', '-created_at']
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.transaction_service = TransactionService()
    
    def get_queryset(self):
        """Возвращает транзакции текущего пользователя"""
        return Transaction.objects.filter(user=self.request.user).select_related(
            'user', 'category', 'source', 'related_user'
        )
    
    def get_serializer_class(self):
        """Выбирает сериализатор в зависимости от действия"""
        if self.action == 'create':
            return TransactionCreateSerializer
        elif self.action == 'stats':
            return TransactionStatsSerializer
        return TransactionSerializer
    
    def perform_create(self, serializer):
        """Создание транзакции через сервис"""
        try:
            transaction_type = serializer.validated_data['type']
            amount = serializer.validated_data['amount']
            description = serializer.validated_data.get('description', '')
            category = serializer.validated_data.get('category')
            source = serializer.validated_data.get('source')
            date = serializer.validated_data.get('date')
            
            if transaction_type == 'income':
                transaction = self.transaction_service.create_income(
                    user=self.request.user,
                    amount=amount,
                    description=description,
                    category=category,
                    source=source,
                    date=date
                )
            elif transaction_type == 'expense':
                transaction = self.transaction_service.create_expense(
                    user=self.request.user,
                    amount=amount,
                    description=description,
                    category=category,
                    source=source,
                    date=date
                )
            else:
                # Для transfer и debt используем стандартное создание
                serializer.save(user=self.request.user)
                return
                
            # Обновляем сериализатор с созданной транзакцией
            serializer.instance = transaction
            
        except ValidationError as e:
            logger.error(f"Validation error creating transaction: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Error creating transaction: {str(e)}")
            raise
    
    @action(detail=False, methods=['get'])
    def stats(self, request):
        """Возвращает статистику транзакций пользователя"""
        try:
            stats = self.transaction_service.get_user_stats(request.user)
            serializer = TransactionStatsSerializer(stats)
            return Response(serializer.data)
        except Exception as e:
            logger.error(f"Error getting transaction stats: {str(e)}")
            return Response(
                {'error': 'Ошибка получения статистики'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['post'])
    def create_income(self, request):
        """Быстрое создание дохода"""
        try:
            amount = Decimal(str(request.data.get('amount', 0)))
            description = request.data.get('description', '')
            category_id = request.data.get('category')
            
            if amount <= 0:
                return Response(
                    {'error': 'Сумма должна быть положительной'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            category = None
            if category_id:
                from apps.categories.models import Category
                try:
                    category = Category.objects.get(id=category_id, user=request.user)
                except Category.DoesNotExist:
                    pass
            
            transaction = self.transaction_service.create_income(
                user=request.user,
                amount=amount,
                description=description,
                category=category
            )
            
            serializer = TransactionSerializer(transaction)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            logger.error(f"Error creating income: {str(e)}")
            return Response(
                {'error': 'Ошибка создания дохода'},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=False, methods=['post'])
    def create_expense(self, request):
        """Быстрое создание расхода"""
        try:
            amount = Decimal(str(request.data.get('amount', 0)))
            description = request.data.get('description', '')
            category_id = request.data.get('category')
            check_balance = request.data.get('check_balance', True)
            
            if amount <= 0:
                return Response(
                    {'error': 'Сумма должна быть положительной'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            category = None
            if category_id:
                from apps.categories.models import Category
                try:
                    category = Category.objects.get(id=category_id, user=request.user)
                except Category.DoesNotExist:
                    pass
            
            transaction = self.transaction_service.create_expense(
                user=request.user,
                amount=amount,
                description=description,
                category=category,
                check_balance=check_balance
            )
            
            serializer = TransactionSerializer(transaction)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
            
        except ValidationError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            logger.error(f"Error creating expense: {str(e)}")
            return Response(
                {'error': 'Ошибка создания расхода'},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=False, methods=['post'])
    def create_transfer(self, request):
        """Создание перевода между пользователями"""
        try:
            amount = Decimal(str(request.data.get('amount', 0)))
            receiver_phone = request.data.get('receiver_phone')
            description = request.data.get('description', '')
            
            if amount <= 0:
                return Response(
                    {'error': 'Сумма должна быть положительной'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            if not receiver_phone:
                return Response(
                    {'error': 'Номер получателя обязателен'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            try:
                receiver_user = User.objects.get(phone_number=receiver_phone)
            except User.DoesNotExist:
                return Response(
                    {'error': 'Пользователь с таким номером не найден'},
                    status=status.HTTP_404_NOT_FOUND
                )
            
            sender_tx, receiver_tx = self.transaction_service.create_transfer(
                sender_user=request.user,
                receiver_user=receiver_user,
                amount=amount,
                description=description
            )
            
            serializer = TransactionSerializer(sender_tx)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
            
        except ValidationError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            logger.error(f"Error creating transfer: {str(e)}")
            return Response(
                {'error': 'Ошибка создания перевода'},
                status=status.HTTP_400_BAD_REQUEST
            )


class DebtTransactionViewSet(viewsets.ModelViewSet):
    """ViewSet для управления долговыми транзакциями"""
    
    queryset = DebtTransaction.objects.all()
    serializer_class = DebtTransactionSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['status', 'debt_direction', 'is_closed']
    search_fields = ['debtor_name', 'description']
    ordering_fields = ['date', 'amount', 'due_date', 'created_at']
    ordering = ['-date', '-created_at']
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.transaction_service = TransactionService()
    
    def get_queryset(self):
        """Возвращает долги текущего пользователя"""
        return DebtTransaction.objects.filter(user=self.request.user).select_related(
            'user', 'category'
        )
    
    def perform_create(self, serializer):
        """Создание долга через сервис"""
        try:
            amount = serializer.validated_data['amount']
            debtor_name = serializer.validated_data['debtor_name']
            debt_direction = serializer.validated_data['debt_direction']
            description = serializer.validated_data.get('description', '')
            due_date = serializer.validated_data.get('due_date')
            category = serializer.validated_data.get('category')
            
            debt = self.transaction_service.create_debt(
                user=self.request.user,
                amount=amount,
                debtor_name=debtor_name,
                debt_direction=debt_direction,
                description=description,
                due_date=due_date,
                category=category
            )
            
            serializer.instance = debt
            
        except ValidationError as e:
            logger.error(f"Validation error creating debt: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Error creating debt: {str(e)}")
            raise
    
    @action(detail=True, methods=['post'])
    def close_debt(self, request, pk=None):
        """Закрытие долга полностью"""
        debt = self.get_object()
        
        try:
            description = request.data.get('description', '')
            self.transaction_service.close_debt(debt, description)
            
            serializer = self.get_serializer(debt)
            return Response({
                'message': 'Долг успешно закрыт',
                'debt': serializer.data
            })
            
        except ValidationError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            logger.error(f"Error closing debt {pk}: {str(e)}")
            return Response(
                {'error': 'Ошибка закрытия долга'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['post'])
    def add_payment(self, request, pk=None):
        """Добавление частичного платежа по долгу"""
        debt = self.get_object()
        
        serializer = DebtPaymentSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            payment_amount = serializer.validated_data['payment_amount']
            description = serializer.validated_data.get('description', '')
            
            is_fully_paid = self.transaction_service.add_debt_payment(
                debt, payment_amount, description
            )
            
            debt_serializer = self.get_serializer(debt)
            
            return Response({
                'message': 'Платеж успешно добавлен',
                'is_fully_paid': is_fully_paid,
                'debt': debt_serializer.data
            })
            
        except ValidationError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            logger.error(f"Error adding payment to debt {pk}: {str(e)}")
            return Response(
                {'error': 'Ошибка добавления платежа'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['get'])
    def overdue(self, request):
        """Возвращает просроченные долги"""
        overdue_debts = self.get_queryset().filter(
            due_date__lt=timezone.now(),
            status__in=['open', 'partial']
        )
        
        serializer = self.get_serializer(overdue_debts, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def summary(self, request):
        """Возвращает сводку по долгам"""
        queryset = self.get_queryset()
        
        total_debts = queryset.count()
        open_debts = queryset.filter(status='open').count()
        closed_debts = queryset.filter(status='closed').count()
        overdue_debts = queryset.filter(
            due_date__lt=timezone.now(),
            status__in=['open', 'partial']
        ).count()
        
        total_amount = sum(debt.amount for debt in queryset)
        total_paid = sum(debt.paid_amount for debt in queryset)
        total_remaining = total_amount - total_paid
        
        debts_from_me = queryset.filter(debt_direction='from_me')
        debts_to_me = queryset.filter(debt_direction='to_me')
        
        return Response({
            'total_debts': total_debts,
            'open_debts': open_debts,
            'closed_debts': closed_debts,
            'overdue_debts': overdue_debts,
            'total_amount': float(total_amount),
            'total_paid': float(total_paid),
            'total_remaining': float(total_remaining),
            'debts_from_me_count': debts_from_me.count(),
            'debts_to_me_count': debts_to_me.count(),
            'debts_from_me_amount': float(sum(d.amount for d in debts_from_me)),
            'debts_to_me_amount': float(sum(d.amount for d in debts_to_me))
        }) 