from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter

from apps.users.models import User, Referral, UserSettings
from apps.users.serializers import UserSerializer, ReferralSerializer, UserSettingsSerializer


class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.select_related('source', 'referral', 'settings').all()
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['language', 'is_active', 'source']
    search_fields = ['phone_number']
    ordering_fields = ['created_at', 'phone_number']
    ordering = ['-created_at']

    def get_queryset(self):
        if self.action == 'list':
            return self.queryset.filter(is_active=True)
        return self.queryset

    @action(detail=True, methods=['post'])
    def activate(self, request, pk=None):
        user = self.get_object()
        user.is_active = True
        user.save()
        return Response({'status': 'activated'})

    @action(detail=True, methods=['post'])
    def deactivate(self, request, pk=None):
        user = self.get_object()
        user.is_active = False
        user.save()
        return Response({'status': 'deactivated'})


class ReferralViewSet(viewsets.ModelViewSet):
    queryset = Referral.objects.select_related('referrer').all()
    serializer_class = ReferralSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['referrer']
    ordering = ['-created_at']


class UserSettingsViewSet(viewsets.ModelViewSet):
    queryset = UserSettings.objects.select_related('user').all()
    serializer_class = UserSettingsSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['currency', 'notify_reports', 'notify_goals'] 