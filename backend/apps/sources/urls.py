from django.urls import path, include
from rest_framework.routers import DefaultRouter
from apps.sources.views.api import SourceViewSet

router = DefaultRouter()
router.register(r'sources', SourceViewSet)

urlpatterns = [
    path('api/', include(router.urls)),
] 