from rest_framework import viewsets, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter

from apps.bot.models import VoiceCommand, BotSession
from apps.bot.serializers import VoiceCommandLogSerializer, BotSessionSerializer


class VoiceCommandLogViewSet(viewsets.ModelViewSet):
    queryset = VoiceCommand.objects.select_related('user').all()
    serializer_class = VoiceCommandLogSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['user', 'command_type', 'status']
    search_fields = ['text']
    ordering_fields = ['received_at', 'created_at']
    ordering = ['-received_at']

    @action(detail=False, methods=['get'])
    def user_stats(self, request):
        user_id = request.query_params.get('user_id')
        days = int(request.query_params.get('days', 30))
        
        if not user_id:
            return Response({'error': 'user_id is required'}, status=400)
        
        try:
            from apps.users.models import User
            user = User.objects.get(id=user_id)
            stats = VoiceCommand.get_user_stats(user, days)
            return Response(stats)
        except User.DoesNotExist:
            return Response({'error': 'User not found'}, status=404)


class BotSessionViewSet(viewsets.ModelViewSet):
    queryset = BotSession.objects.select_related('user').all()
    serializer_class = BotSessionSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['user', 'is_active', 'session_type']
    ordering_fields = ['started_at', 'last_activity_at']
    ordering = ['-started_at']

    @action(detail=True, methods=['post'])
    def end_session(self, request, pk=None):
        session = self.get_object()
        session.end_session()
        return Response({'status': 'session ended'})

    @action(detail=False, methods=['post'])
    def end_inactive(self, request):
        hours = int(request.data.get('hours', 24))
        ended_count = BotSession.end_inactive_sessions(hours)
        return Response({'ended_sessions': ended_count}) 