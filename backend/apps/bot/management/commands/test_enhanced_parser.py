"""
Тестирование расширенного парсера с товарами и командами удаления
"""

from django.core.management.base import BaseCommand
from apps.bot.services.text_parser_service import TextParserService


class Command(BaseCommand):
    help = 'Тестирует расширенный парсер товаров и команды удаления'

    def handle(self, *args, **options):
        parser = TextParserService()
        
        self.stdout.write('\n🧪 ТЕСТИРОВАНИЕ РАСШИРЕННОГО ПАРСЕРА\n')
        
        # Тесты товаров и продуктов
        product_tests = [
            "купил молоко за 5000 сум",
            "потратил 15000 на хлеб и масло",
            "купил сигареты за 20$", 
            "заплатил за яблоки 3000 сум",
            "потратил на кроссовки 50$",
            "купил куртку за 100 долларов",
            "заплатил за стрижку 25000 сум",
            "купил книги для учебы 30$",
            "потратил на корм для кота 8000 сум",
            "заплатил за такси 15000 сум"
        ]
        
        self.stdout.write('📦 ТЕСТИРОВАНИЕ ТОВАРОВ:')
        for test_text in product_tests:
            result = parser.parse_transaction_text(test_text, 'ru')
            if result:
                self.stdout.write(
                    f"✅ '{test_text}' → {result['category']} | {result['amount']} {result['currency']}"
                )
            else:
                self.stdout.write(self.style.ERROR(f"❌ '{test_text}' → Не распознано"))
        
        # Тесты команд удаления
        delete_tests = [
            "удали категорию продукты",
            "удалить транзакцию молоко", 
            "убери категорию такси",
            "отмени операцию хлеб",
            "delete category food",
            "remove transaction taxi",
            "kategoriyani o'chir transport",
            "tranzaksiyani o'chir sut"
        ]
        
        self.stdout.write('\n🗑️ ТЕСТИРОВАНИЕ КОМАНД УДАЛЕНИЯ:')
        for test_text in delete_tests:
            result = parser.parse_management_command(test_text, 'ru')
            if result:
                command_type = result['type']
                target = result.get('category_name') or result.get('target', 'неизвестно')
                self.stdout.write(
                    f"✅ '{test_text}' → {command_type} | {target}"
                )
            else:
                self.stdout.write(self.style.ERROR(f"❌ '{test_text}' → Не распознано"))
        
        # Тесты валют
        currency_tests = [
            "потратил 50 000 сум на продукты",
            "купил за 25.50$ еду",
            "заплатил 100,5 евро за одежду",
            "потратил 2000₽ на бензин",
            "купил за 15 баксов сигареты"
        ]
        
        self.stdout.write('\n💰 ТЕСТИРОВАНИЕ ВАЛЮТ:')
        for test_text in currency_tests:
            result = parser.parse_transaction_text(test_text, 'ru')
            if result:
                self.stdout.write(
                    f"✅ '{test_text}' → {result['amount']} {result['currency']}"
                )
            else:
                self.stdout.write(self.style.ERROR(f"❌ '{test_text}' → Не распознано"))
        
        self.stdout.write('\n✨ Тестирование завершено!') 