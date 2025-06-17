"""
Django management команда для запуска Telegram бота
"""

import logging
import os
import sys
from django.core.management.base import BaseCommand
from django.conf import settings

from apps.bot.bot_v13 import run_bot


logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Запуск Telegram бота OvozPay'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--debug',
            action='store_true',
            help='Включить отладочный режим',
        )
    
    def handle(self, *args, **options):
        """Основной метод команды"""
        
        # Настраиваем логирование
        if options['debug']:
            logging.basicConfig(
                level=logging.DEBUG,
                format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
        else:
            logging.basicConfig(
                level=logging.INFO,
                format='%(asctime)s - %(levelname)s - %(message)s'
            )
        
        # Проверяем наличие токена
        bot_token = getattr(settings, 'TELEGRAM_BOT_TOKEN', None)
        if not bot_token:
            self.stdout.write(
                self.style.ERROR('TELEGRAM_BOT_TOKEN не настроен!')
            )
            self.stdout.write(
                'Добавьте TELEGRAM_BOT_TOKEN в .env файл или переменные окружения'
            )
            sys.exit(1)
        
        self.stdout.write(
            self.style.SUCCESS('🚀 Запуск OvozPay Telegram Bot...')
        )
        
        self.stdout.write('📋 Функции бота:')
        self.stdout.write('🎤 • Голосовое управление финансами')
        self.stdout.write('📸 • Сканирование чеков (демо-режим)')
        self.stdout.write('💰 • Управление доходами и расходами')
        self.stdout.write('🎯 • Цели и накопления')
        self.stdout.write('📊 • Аналитика и отчеты')
        self.stdout.write('')
        
        try:
            # Запускаем бота
            run_bot()
            
        except KeyboardInterrupt:
            self.stdout.write('\n⛔ Остановка бота...')
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'❌ Ошибка запуска бота: {e}')
            )
            sys.exit(1)
        
        self.stdout.write(
            self.style.SUCCESS('✅ Бот остановлен')
        ) 