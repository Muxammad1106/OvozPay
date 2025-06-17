from django.urls import path, include
from rest_framework.routers import DefaultRouter
from apps.broadcast.views.api import BroadcastMessageViewSet, BroadcastUserLogViewSet

router = DefaultRouter()
router.register(r'messages', BroadcastMessageViewSet)
router.register(r'logs', BroadcastUserLogViewSet)

urlpatterns = [
    path('api/', include(router.urls)),
] 