import asyncio
import aiohttp
from django.core.management.base import BaseCommand
from django.conf import settings


class Command(BaseCommand):
    help = 'Проверяет статус webhook Telegram бота'

    def handle(self, *args, **options):
        bot_token = settings.TELEGRAM_BOT_TOKEN
        url = f"https://api.telegram.org/bot{bot_token}/getWebhookInfo"

        result = asyncio.run(self._check_webhook_info(url))
        
        if result.get('ok'):
            webhook_info = result.get('result', {})
            
            self.stdout.write(self.style.SUCCESS('📊 Статус Webhook:'))
            self.stdout.write(f"URL: {webhook_info.get('url', 'Не установлен')}")
            self.stdout.write(f"Сертификат: {'Да' if webhook_info.get('has_custom_certificate') else 'Нет'}")
            self.stdout.write(f"Ожидающих обновлений: {webhook_info.get('pending_update_count', 0)}")
            
            allowed_updates = webhook_info.get('allowed_updates', [])
            if allowed_updates:
                self.stdout.write(f"Разрешенные обновления: {', '.join(allowed_updates)}")
            else:
                self.stdout.write("Разрешенные обновления: Все")
                
            last_error = webhook_info.get('last_error_message')
            if last_error:
                self.stdout.write(
                    self.style.WARNING(f"⚠️ Последняя ошибка: {last_error}")
                )
                last_error_date = webhook_info.get('last_error_date')
                if last_error_date:
                    from datetime import datetime
                    error_date = datetime.fromtimestamp(last_error_date)
                    self.stdout.write(f"Время ошибки: {error_date}")
            
            if webhook_info.get('url'):
                self.stdout.write(self.style.SUCCESS('✅ Webhook активен'))
            else:
                self.stdout.write(self.style.WARNING('❌ Webhook не установлен'))
                
        else:
            error_msg = result.get('description', 'Неизвестная ошибка')
            self.stdout.write(
                self.style.ERROR(f'❌ Ошибка получения информации: {error_msg}')
            )

    async def _check_webhook_info(self, url):
        """Получает информацию о webhook асинхронно"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    return await response.json()
        except Exception as e:
            return {'ok': False, 'description': str(e)} 