from django.urls import path, include
from rest_framework.routers import DefaultRouter
from apps.categories.views.api import CategoryViewSet

router = DefaultRouter()
router.register(r'categories', CategoryViewSet)

urlpatterns = [
    path('api/', include(router.urls)),
] 