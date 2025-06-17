from rest_framework import viewsets, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter

from apps.categories.models import Category
from apps.categories.serializers import CategorySerializer


class CategoryViewSet(viewsets.ModelViewSet):
    queryset = Category.objects.select_related('user').all()
    serializer_class = CategorySerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['user', 'type', 'is_default']
    search_fields = ['name']
    ordering_fields = ['name', 'type', 'created_at']
    ordering = ['type', 'name']

    @action(detail=False, methods=['post'])
    def create_defaults(self, request):
        user_id = request.data.get('user_id')
        if not user_id:
            return Response({'error': 'user_id is required'}, status=400)
        
        try:
            from apps.users.models import User
            user = User.objects.get(id=user_id)
            categories = Category.create_default_categories_for_user(user)
            serializer = self.get_serializer(categories, many=True)
            return Response(serializer.data)
        except User.DoesNotExist:
            return Response({'error': 'User not found'}, status=404)
    
    @action(detail=False, methods=['get'])
    def defaults(self, request):
        default_categories = Category.get_default_categories()
        serializer = self.get_serializer(default_categories, many=True)
        return Response(serializer.data) 