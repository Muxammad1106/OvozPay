"""
Команда для тестирования парсера команд управления
"""

from django.core.management.base import BaseCommand
from apps.bot.services.text_parser_service import TextParserService


class Command(BaseCommand):
    help = 'Тестирует парсер команд управления бота'

    def add_arguments(self, parser):
        parser.add_argument(
            '--text',
            type=str,
            help='Текст для парсинга'
        )
        parser.add_argument(
            '--language',
            type=str,
            default='ru',
            choices=['ru', 'en', 'uz'],
            help='Язык текста'
        )

    def handle(self, *args, **options):
        parser = TextParserService()
        
        if options['text']:
            # Тестируем конкретный текст
            text = options['text']
            language = options['language']
            
            self.stdout.write(f"Тестируем: '{text}' (язык: {language})")
            
            # Тестируем команды управления
            management_result = parser.parse_management_command(text, language)
            if management_result:
                self.stdout.write(self.style.SUCCESS(f"✅ Команда управления: {management_result}"))
                return
            
            # Тестируем транзакции
            transaction_result = parser.parse_transaction_text(text, language)
            if transaction_result:
                self.stdout.write(self.style.SUCCESS(f"✅ Транзакция: {transaction_result}"))
                return
            
            self.stdout.write(self.style.ERROR("❌ Не удалось распарсить"))
        else:
            # Запускаем встроенные тесты
            self.stdout.write("🧪 Запускаем тесты команд управления...")
            
            test_cases = [
                # Команды управления
                ("создай категорию такси", 'ru'),
                ("добавь категорию еда", 'ru'),
                ("поменяй язык на английский", 'ru'),
                ("смени валюту на доллары", 'ru'),
                ("change language to english", 'en'),
                ("create category transport", 'en'),
                ("kategoriya yarat oziq-ovqat", 'uz'),
                
                # Транзакции с категориями
                ("купил сигареты за 20000", 'ru'),
                ("потратил 50$ на такси", 'ru'),
                ("заработал 1000 долларов", 'ru'),
            ]
            
            for text, lang in test_cases:
                self.stdout.write(f"\n📝 Тест: '{text}' ({lang})")
                
                # Проверяем команды управления
                management_result = parser.parse_management_command(text, lang)
                if management_result:
                    self.stdout.write(self.style.SUCCESS(f"🎛️ Команда: {management_result}"))
                    continue
                
                # Проверяем транзакции
                transaction_result = parser.parse_transaction_text(text, lang)
                if transaction_result:
                    self.stdout.write(self.style.SUCCESS(f"💰 Транзакция: {transaction_result}"))
                    continue
                
                self.stdout.write(self.style.ERROR("❌ Не распознано"))
            
            self.stdout.write(self.style.SUCCESS("\n🎉 Тестирование завершено!")) 