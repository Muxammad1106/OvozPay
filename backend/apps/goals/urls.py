from django.urls import path, include
from rest_framework.routers import DefaultRouter
from apps.goals.views.api import GoalViewSet

router = DefaultRouter()
router.register(r'goals', GoalViewSet)

urlpatterns = [
    path('api/', include(router.urls)),
] 