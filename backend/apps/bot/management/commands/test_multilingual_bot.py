"""
Django команда для тестирования мультиязычного бота
"""

import asyncio
import json
from django.core.management.base import BaseCommand
from django.conf import settings

from apps.bot.telegram.bot_client import TelegramBotClient
from apps.bot.services.telegram_api_service import TelegramAPIService


class Command(BaseCommand):
    help = 'Тестирует мультиязычные функции Telegram бота'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--chat-id',
            type=int,
            help='Chat ID для тестирования (если не указан, будет выведена только информация)'
        )
        parser.add_argument(
            '--language',
            type=str,
            choices=['ru', 'en', 'uz'],
            default='ru',
            help='Язык для тестирования'
        )
    
    def handle(self, *args, **options):
        self.stdout.write("🌐 Тестирование мультиязычного бота...")
        
        # Проверяем настройки
        if not self.check_settings():
            return
        
        # Инициализируем бота
        bot_client = TelegramBotClient()
        
        # Выводим информацию о боте
        self.show_bot_info(bot_client)
        
        # Если указан chat_id, тестируем функции
        chat_id = options.get('chat_id')
        if chat_id:
            language = options.get('language', 'ru')
            self.test_multilingual_functions(bot_client, chat_id, language)
        else:
            self.stdout.write(
                self.style.WARNING(
                    "💡 Для тестирования функций укажите --chat-id"
                )
            )
    
    def check_settings(self):
        """Проверяет необходимые настройки"""
        token = getattr(settings, 'TELEGRAM_BOT_TOKEN', '')
        if not token:
            self.stdout.write(
                self.style.ERROR(
                    "❌ TELEGRAM_BOT_TOKEN не установлен в настройках"
                )
            )
            return False
        
        self.stdout.write(
            self.style.SUCCESS(
                f"✅ Telegram Bot Token настроен (длина: {len(token)} символов)"
            )
        )
        return True
    
    def show_bot_info(self, bot_client):
        """Показывает информацию о боте"""
        info = bot_client.get_bot_info()
        
        self.stdout.write(f"\n📊 Информация о боте:")
        self.stdout.write(f"   Название: {info['name']}")
        self.stdout.write(f"   Версия: {info['version']}")
        
        self.stdout.write(f"\n🚀 Функции:")
        for feature in info['features']:
            self.stdout.write(f"   • {feature}")
        
        self.stdout.write(f"\n🌍 Поддерживаемые языки:")
        for lang in info['supported_languages']:
            self.stdout.write(f"   • {lang}")
        
        self.stdout.write(f"\n💱 Поддерживаемые валюты:")
        for curr in info['supported_currencies']:
            self.stdout.write(f"   • {curr}")
    
    def test_multilingual_functions(self, bot_client, chat_id, language):
        """Тестирует мультиязычные функции"""
        self.stdout.write(f"\n🧪 Тестирование для chat_id: {chat_id}, язык: {language}")
        
        # Импортируем переводы
        from apps.bot.utils.translations import t
        
        # Тестируем получение переводов
        self.test_translations(language)
        
        # Тестируем клавиатуры
        self.test_keyboards(language)
        
        # Тестируем отправку тестового сообщения
        self.test_message_sending(bot_client, chat_id, language)
    
    def test_translations(self, language):
        """Тестирует систему переводов"""
        from apps.bot.utils.translations import t
        
        self.stdout.write(f"\n📝 Тестирование переводов для языка '{language}':")
        
        test_keys = [
            'start_welcome',
            'help_title', 
            'balance_title',
            'settings_title',
            'choose_language',
            'language_set'
        ]
        
        for key in test_keys:
            text = t.get_text(key, language)
            self.stdout.write(f"   {key}: {text[:50]}...")
        
        # Тестируем форматирование через format
        formatted_text = t.get_text('currency_set', language).format('USD')
        self.stdout.write(f"   Форматирование: {formatted_text}")
    
    def test_keyboards(self, language):
        """Тестирует клавиатуры"""
        from apps.bot.utils.translations import t
        
        self.stdout.write(f"\n⌨️ Тестирование клавиатур:")
        
        # Клавиатура языков
        lang_kb = t.get_language_keyboard()
        self.stdout.write(f"   Язык: {len(lang_kb['inline_keyboard'])} рядов")
        
        # Клавиатура валют
        curr_kb = t.get_currency_keyboard(language)
        self.stdout.write(f"   Валюта: {len(curr_kb['inline_keyboard'])} рядов")
        
        # Клавиатура настроек
        settings_kb = t.get_settings_keyboard(language)
        self.stdout.write(f"   Настройки: {len(settings_kb['inline_keyboard'])} рядов")
    
    def test_message_sending(self, bot_client, chat_id, language):
        """Тестирует отправку сообщения"""
        from apps.bot.utils.translations import t
        
        self.stdout.write(f"\n📤 Отправка тестового сообщения...")
        
        # Создаём тестовое обновление
        test_update = {
            'message': {
                'chat': {'id': chat_id},
                'from': {
                    'id': 123456789,
                    'username': 'test_user',
                    'first_name': 'Test',
                    'last_name': 'User'
                },
                'text': '/start'
            }
        }
        
        try:
            # Симулируем обработку команды /start
            bot_client.handle_update(test_update)
            
            self.stdout.write(
                self.style.SUCCESS(
                    f"✅ Тестовое обновление отправлено в обработку"
                )
            )
            
            # Даём время на обработку
            import time
            time.sleep(2)
            
            self.stdout.write(
                self.style.SUCCESS(
                    "✅ Проверьте ваш Telegram - должно прийти приветственное сообщение!"
                )
            )
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(
                    f"❌ Ошибка при отправке тестового сообщения: {e}"
                )
            )
    
    def show_usage_examples(self):
        """Показывает примеры использования"""
        self.stdout.write(f"\n📖 Примеры использования:")
        self.stdout.write(f"   python manage.py test_multilingual_bot")
        self.stdout.write(f"   python manage.py test_multilingual_bot --chat-id 123456789")
        self.stdout.write(f"   python manage.py test_multilingual_bot --chat-id 123456789 --language en")
        self.stdout.write(f"   python manage.py test_multilingual_bot --chat-id 123456789 --language uz") 