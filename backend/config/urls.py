from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from rest_framework import permissions
from drf_yasg.views import get_schema_view
from drf_yasg import openapi
from apps.bot.telegram.webhook_view import TelegramWebhookView

schema_view = get_schema_view(
    openapi.Info(
        title="OvozPay API",
        default_version='v1',
        description="API для голосового помощника управления финансами OvozPay",
        contact=openapi.Contact(email="admin@ovozpay.uz"),
        license=openapi.License(name="BSD License"),
    ),
    public=True,
    permission_classes=[permissions.AllowAny],
)

urlpatterns = [
    path('admin/', admin.site.urls),
    
    path('swagger/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    path('redoc/', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),
    
    path('api/users/', include('apps.users.urls')),
    path('api/transactions/', include('apps.transactions.urls')),
    path('api/categories/', include('apps.categories.urls')),
    path('api/goals/', include('apps.goals.urls')),
    path('api/analytics/', include('apps.analytics.urls')),
    path('api/sources/', include('apps.sources.urls')),
    path('api/broadcast/', include('apps.broadcast.urls')),
    path('api/bot/', include('apps.bot.urls')),
    
    # Telegram Webhook
    path('telegram/webhook/', TelegramWebhookView.as_view(), name='telegram_webhook'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
