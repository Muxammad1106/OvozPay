import json
import logging
import asyncio
from django.http import HttpResponse, HttpResponseBadRequest
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.views.decorators.http import require_http_methods
from apps.bot.telegram.bot_client import bot_client

logger = logging.getLogger(__name__)


@method_decorator(csrf_exempt, name='dispatch')
class TelegramWebhookView(View):
    def post(self, request):
        try:
            if request.content_type != 'application/json':
                logger.warning(f"Invalid content type: {request.content_type}")
                return HttpResponseBadRequest("Invalid content type")
            
            body = request.body.decode('utf-8')
            
            if not body:
                logger.warning("Empty request body")
                return HttpResponseBadRequest("Empty body")
            
            try:
                update_data = json.loads(body)
                logger.info(f"Received webhook update: {update_data.get('update_id', 'no_id')}")
            except json.JSONDecodeError as e:
                logger.error(f"Invalid JSON in webhook: {str(e)}")
                return HttpResponseBadRequest("Invalid JSON")
            
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(bot_client.process_update(update_data))
                loop.close()
            except Exception as e:
                logger.error(f"Error processing update in webhook: {str(e)}")
                return HttpResponse("Error processing update", status=500)
            
            return HttpResponse("OK", status=200)
            
        except Exception as e:
            logger.error(f"Unexpected error in webhook: {str(e)}")
            return HttpResponse("Internal server error", status=500)
    
    def get(self, request):
        return HttpResponse("Telegram Webhook is active", status=200)


@csrf_exempt
@require_http_methods(["POST"])
def telegram_webhook_function_view(request):
    """
    Function-based view альтернатива для webhook
    """
    try:
        if request.content_type != 'application/json':
            return HttpResponseBadRequest("Invalid content type")
        
        body = request.body.decode('utf-8')
        update_data = json.loads(body)
        
        logger.info(f"Function webhook received: {update_data.get('update_id', 'no_id')}")
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(bot_client.process_update(update_data))
        loop.close()
        
        return HttpResponse("OK", status=200)
        
    except Exception as e:
        logger.error(f"Error in function webhook: {str(e)}")
        return HttpResponse("Error", status=500) 