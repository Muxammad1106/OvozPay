from rest_framework import viewsets, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import OrderingFilter
from datetime import date, timedelta

from apps.analytics.models import Report, Balance
from apps.analytics.serializers import ReportSerializer, BalanceSerializer


class ReportViewSet(viewsets.ModelViewSet):
    queryset = Report.objects.select_related('user').all()
    serializer_class = ReportSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['user']
    ordering_fields = ['period_start', 'period_end', 'created_at']
    ordering = ['-period_end']

    @action(detail=False, methods=['post'])
    def generate(self, request):
        user_id = request.data.get('user_id')
        period_start = request.data.get('period_start')
        period_end = request.data.get('period_end')
        
        if not all([user_id, period_start, period_end]):
            return Response({
                'error': 'user_id, period_start and period_end are required'
            }, status=400)
        
        try:
            from apps.users.models import User
            from datetime import datetime
            
            user = User.objects.get(id=user_id)
            start_date = datetime.strptime(period_start, '%Y-%m-%d').date()
            end_date = datetime.strptime(period_end, '%Y-%m-%d').date()
            
            report = Report.generate_report(user, start_date, end_date)
            serializer = self.get_serializer(report)
            return Response(serializer.data)
            
        except User.DoesNotExist:
            return Response({'error': 'User not found'}, status=404)
        except ValueError:
            return Response({'error': 'Invalid date format'}, status=400)


class BalanceViewSet(viewsets.ModelViewSet):
    queryset = Balance.objects.select_related('user').all()
    serializer_class = BalanceSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['user']

    @action(detail=True, methods=['post'])
    def update_balance(self, request, pk=None):
        balance = self.get_object()
        new_amount = balance.update_balance()
        return Response({'amount': new_amount})

    @action(detail=False, methods=['post'])
    def get_or_create(self, request):
        user_id = request.data.get('user_id')
        
        if not user_id:
            return Response({'error': 'user_id is required'}, status=400)
        
        try:
            from apps.users.models import User
            user = User.objects.get(id=user_id)
            balance = Balance.get_or_create_for_user(user)
            serializer = self.get_serializer(balance)
            return Response(serializer.data)
            
        except User.DoesNotExist:
            return Response({'error': 'User not found'}, status=404) 