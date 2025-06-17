from rest_framework import viewsets, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter

from apps.broadcast.models import BroadcastMessage, BroadcastUserLog
from apps.broadcast.serializers import BroadcastMessageSerializer, BroadcastUserLogSerializer


class BroadcastMessageViewSet(viewsets.ModelViewSet):
    queryset = BroadcastMessage.objects.all()
    serializer_class = BroadcastMessageSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['status', 'target_audience']
    search_fields = ['title', 'body']
    ordering_fields = ['send_at', 'created_at']
    ordering = ['-created_at']

    @action(detail=True, methods=['post'])
    def schedule(self, request, pk=None):
        message = self.get_object()
        send_at = request.data.get('send_at')
        
        if send_at:
            from datetime import datetime
            try:
                send_at_datetime = datetime.fromisoformat(send_at.replace('Z', '+00:00'))
                message.schedule_broadcast(send_at_datetime)
                return Response({'status': 'scheduled'})
            except ValueError:
                return Response({'error': 'Invalid datetime format'}, status=400)
        else:
            message.schedule_broadcast()
            return Response({'status': 'scheduled'})

    @action(detail=True, methods=['post'])
    def start_sending(self, request, pk=None):
        message = self.get_object()
        if message.start_sending():
            return Response({'status': 'sending started'})
        else:
            return Response({'error': 'Cannot start sending'}, status=400)


class BroadcastUserLogViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = BroadcastUserLog.objects.select_related('message', 'user').all()
    serializer_class = BroadcastUserLogSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['message', 'user', 'status']
    ordering = ['-created_at'] 