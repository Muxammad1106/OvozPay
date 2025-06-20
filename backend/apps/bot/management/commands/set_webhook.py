import asyncio
from django.core.management.base import BaseCommand
from django.conf import settings
from apps.bot.telegram.services.telegram_api_service import TelegramAPIService


class Command(BaseCommand):
    help = 'Устанавливает webhook для Telegram бота'

    def add_arguments(self, parser):
        parser.add_argument(
            '--url',
            type=str,
            help='URL для webhook (по умолчанию из настроек)',
        )
        parser.add_argument(
            '--delete',
            action='store_true',
            help='Удалить webhook вместо установки',
        )

    def handle(self, *args, **options):
        telegram_service = TelegramAPIService()

        if options['delete']:
            self.stdout.write('Удаляем webhook...')
            result = asyncio.run(telegram_service.delete_webhook())
        else:
            webhook_url = options['url'] or settings.TELEGRAM_WEBHOOK_URL
            self.stdout.write(f'Устанавливаем webhook: {webhook_url}')
            result = asyncio.run(telegram_service.set_webhook(webhook_url))

        if result.get('ok'):
            if options['delete']:
                self.stdout.write(
                    self.style.SUCCESS('✅ Webhook успешно удален')
                )
            else:
                self.stdout.write(
                    self.style.SUCCESS('✅ Webhook успешно установлен')
                )
        else:
            error_msg = result.get('description', 'Неизвестная ошибка')
            self.stdout.write(
                self.style.ERROR(f'❌ Ошибка: {error_msg}')
            ) 