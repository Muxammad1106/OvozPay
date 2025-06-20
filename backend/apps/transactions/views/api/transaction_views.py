from rest_framework import viewsets, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from django.db.models import Sum, Q
from decimal import Decimal

from apps.transactions.models import Transaction, Debt
from apps.transactions.serializers import TransactionSerializer, DebtSerializer


class TransactionViewSet(viewsets.ModelViewSet):
    queryset = Transaction.objects.select_related('user', 'category').all()
    serializer_class = TransactionSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['user', 'type', 'category']
    search_fields = ['description']
    ordering_fields = ['date', 'amount', 'created_at']
    ordering = ['-date', '-created_at']

    @action(detail=False, methods=['get'])
    def statistics(self, request):
        user_id = request.query_params.get('user')
        queryset = self.get_queryset()
        
        if user_id:
            queryset = queryset.filter(user_id=user_id)
        
        income_sum = queryset.filter(type='income').aggregate(
            total=Sum('amount')
        )['total'] or Decimal('0')
        
        expense_sum = queryset.filter(type='expense').aggregate(
            total=Sum('amount')
        )['total'] or Decimal('0')
        
        return Response({
            'total_income': income_sum,
            'total_expense': expense_sum,
            'balance': income_sum - expense_sum,
            'transactions_count': queryset.count()
        })


class DebtViewSet(viewsets.ModelViewSet):
    queryset = Debt.objects.select_related('user').all()
    serializer_class = DebtSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['user', 'direction', 'status']
    search_fields = ['debtor_name', 'description']
    ordering_fields = ['date', 'amount', 'created_at']
    ordering = ['-date', '-created_at']

    @action(detail=True, methods=['post'])
    def close_debt(self, request, pk=None):
        debt = self.get_object()
        debt.close_debt()
        return Response({'status': 'closed'})

    @action(detail=False, methods=['get'])
    def overdue(self, request):
        overdue_debts = [debt for debt in self.get_queryset() if debt.is_overdue]
        serializer = self.get_serializer(overdue_debts, many=True)
        return Response(serializer.data) 