"""
Команда для тестирования парсера текстовых команд
"""

from django.core.management.base import BaseCommand
from apps.bot.services.text_parser_service import TextParserService


class Command(BaseCommand):
    help = 'Тестирует парсер текстовых команд бота'

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
            result = parser.parse_transaction_text(text, language)
            
            if result:
                self.stdout.write(self.style.SUCCESS(f"✅ Результат: {result}"))
            else:
                self.stdout.write(self.style.ERROR("❌ Не удалось распарсить"))
        else:
            # Запускаем встроенные тесты
            self.stdout.write("🧪 Запускаем тесты парсера...")
            
            test_cases = [
                ("потратил 10000 сум на продукты", 'ru'),
                ("купил молоко за 5000", 'ru'),
                ("заработал 1000 долларов", 'ru'),
                ("потратил 50$ на бензин", 'ru'),
                ("заплатил 200 евро за одежду", 'ru'),
                ("получил зарплату 2000000 сум", 'ru'),
                ("spent 100 dollars on groceries", 'en'),
                ("earned 500$ for work", 'en'),
                ("5000 so'm mahsulotlarga sarfladim", 'uz'),
                ("100 dollar ishlab topdim", 'uz'),
            ]
            
            for text, lang in test_cases:
                self.stdout.write(f"\n📝 Тест: '{text}' ({lang})")
                result = parser.parse_transaction_text(text, lang)
                
                if result:
                    self.stdout.write(self.style.SUCCESS(f"✅ {result}"))
                else:
                    self.stdout.write(self.style.ERROR("❌ Не распознано"))
            
            self.stdout.write(self.style.SUCCESS("\n🎉 Тестирование завершено!")) 