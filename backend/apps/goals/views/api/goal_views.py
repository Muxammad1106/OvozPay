from rest_framework import viewsets, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from decimal import Decimal

from apps.goals.models import Goal
from apps.goals.serializers import GoalSerializer


class GoalViewSet(viewsets.ModelViewSet):
    queryset = Goal.objects.select_related('user').all()
    serializer_class = GoalSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['user', 'is_completed', 'reminder_interval']
    search_fields = ['title']
    ordering_fields = ['deadline', 'target_amount', 'created_at']
    ordering = ['deadline']

    @action(detail=True, methods=['post'])
    def add_progress(self, request, pk=None):
        goal = self.get_object()
        amount = request.data.get('amount')
        
        if not amount:
            return Response({'error': 'amount is required'}, status=400)
        
        try:
            amount = Decimal(str(amount))
            if goal.add_progress(amount):
                return Response({'status': 'progress added', 'current_amount': goal.current_amount})
            else:
                return Response({'error': 'Invalid amount'}, status=400)
        except (ValueError, TypeError):
            return Response({'error': 'Invalid amount format'}, status=400)

    @action(detail=True, methods=['post'])
    def complete(self, request, pk=None):
        goal = self.get_object()
        goal.complete_goal()
        return Response({'status': 'goal completed'})

    @action(detail=True, methods=['post'])
    def reset(self, request, pk=None):
        goal = self.get_object()
        goal.reset_progress()
        return Response({'status': 'progress reset'})

    @action(detail=False, methods=['get'])
    def overdue(self, request):
        overdue_goals = [goal for goal in self.get_queryset() if goal.is_overdue]
        serializer = self.get_serializer(overdue_goals, many=True)
        return Response(serializer.data) 