import json
import logging
from django.http import HttpResponse
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.conf import settings
from .bot_client import TelegramBotClient

logger = logging.getLogger(__name__)


@method_decorator(csrf_exempt, name='dispatch')
class TelegramWebhookView(View):
    """
    Webhook для получения обновлений от Telegram Bot API
    """
    
    def post(self, request):
        """
        Обрабатывает POST запросы от Telegram
        """
        try:
            # Парсим JSON из запроса
            update_data = json.loads(request.body)
            
            # Логируем входящее обновление
            logger.info(f"📥 Получено обновление от Telegram: {update_data}")
            
            # Инициализируем бот клиент
            bot_client = TelegramBotClient()
            
            # Обрабатываем обновление
            logger.info(f"🔄 Начинаем обработку обновления...")
            bot_client.handle_update(update_data)
            logger.info(f"✅ Обновление успешно обработано")
            
            # Возвращаем успешный ответ
            return HttpResponse("OK", status=200)
            
        except json.JSONDecodeError as e:
            logger.error(f"Ошибка парсинга JSON: {e}")
            return HttpResponse("Bad Request", status=400)
            
        except Exception as e:
            logger.error(f"Ошибка обработки webhook: {e}")
            return HttpResponse("Internal Server Error", status=500)
    
    def get(self, request):
        """
        GET запросы не поддерживаются
        """
        return HttpResponse("Method not allowed", status=405) 