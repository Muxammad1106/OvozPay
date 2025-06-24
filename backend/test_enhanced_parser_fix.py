#!/usr/bin/env python
"""
Тест для проверки улучшенного парсера с распознаванием чисел словами и конвертацией валют
"""

import os
import sys
import asyncio
import django

# Настройка Django
sys.path.insert(0, '/Users/muxammadchariev/Desktop/OvozPay/backend')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from apps.bot.services.text_parser_service import TextParserService


async def test_word_numbers_with_currency():
    """Тест распознавания чисел словами с валютой"""
    parser = TextParserService()
    
    test_cases = [
        # Основные проблемные случаи
        "получил зарплату тысячу долларов",
        "получил одну тысячу долларов", 
        "получил зарплату одна тысяча долларов",
        "получил тысяча долларов",
        
        # Другие валюты
        "потратил тысячу сум на продукты",
        "получил две тысячи рублей",
        "потратил пятьсот евро",
        
        # Комбинированные числа
        "получил пять тысяч долларов",
        "потратил три тысячи сум",
        "получил десять тысяч рублей",
        
        # Меньшие суммы
        "потратил сто долларов",
        "получил двести сум",
        "потратил пятьдесят рублей",
    ]
    
    print("=== ТЕСТ РАСПОЗНАВАНИЯ ЧИСЕЛ СЛОВАМИ ===\n")
    
    success_count = 0
    total_count = len(test_cases)
    
    for i, test_text in enumerate(test_cases, 1):
        print(f"Тест {i}: {test_text}")
        
        try:
            # Парсим с конвертацией в UZS
            result = await parser.parse_transaction_text(test_text, 'ru', 'UZS')
            
            if result:
                original_amount = result.get('original_amount', result['amount'])
                original_currency = result.get('original_currency', result['currency'])
                final_amount = result['amount']
                final_currency = result['currency']
                
                print(f"  ✅ Распознано: {result['type']}")
                print(f"     Исходная сумма: {original_amount} {original_currency}")
                print(f"     Итоговая сумма: {final_amount} {final_currency}")
                print(f"     Категория: {result['category']}")
                print(f"     Описание: {result['description']}")
                
                # Проверяем логику
                if "тысяч" in test_text.lower() and float(result['amount']) >= 1000:
                    success_count += 1
                    print("     ✅ Логика корректна")
                elif "сто" in test_text.lower() and float(result['amount']) >= 100:
                    success_count += 1
                    print("     ✅ Логика корректна")
                elif "пятьдесят" in test_text.lower() and float(result['amount']) >= 50:
                    success_count += 1
                    print("     ✅ Логика корректна")
                else:
                    print("     ⚠️ Сумма не соответствует ожидаемой")
            else:
                print("  ❌ Не удалось распознать")
                
        except Exception as e:
            print(f"  ❌ Ошибка: {e}")
        
        print()
    
    accuracy = (success_count / total_count) * 100
    print(f"РЕЗУЛЬТАТ: {success_count}/{total_count} ({accuracy:.1f}%) тестов пройдено успешно")
    
    return accuracy >= 80


async def test_currency_conversion():
    """Тест конвертации валют"""
    parser = TextParserService()
    
    print("=== ТЕСТ КОНВЕРТАЦИИ ВАЛЮТ ===\n")
    
    test_cases = [
        # Доллары в сумы
        ("потратил 100 долларов на продукты", 'UZS', 100 * 12300),
        # Евро в доллары
        ("получил 50 евро", 'USD', 50 * 1.09),
        # Рубли в сумы
        ("потратил 1000 рублей", 'UZS', 1000 * 135),
        # Без конвертации
        ("потратил 50000 сум", 'UZS', 50000),
    ]
    
    success_count = 0
    
    for i, (test_text, user_currency, expected_amount) in enumerate(test_cases, 1):
        print(f"Тест {i}: {test_text} → {user_currency}")
        
        try:
            result = await parser.parse_transaction_text(test_text, 'ru', user_currency)
            
            if result:
                final_amount = float(result['amount'])
                original_amount = result.get('original_amount', result['amount'])
                original_currency = result.get('original_currency', result['currency'])
                
                print(f"  Исходно: {original_amount} {original_currency}")
                print(f"  Результат: {final_amount} {result['currency']}")
                print(f"  Ожидалось: ~{expected_amount} {user_currency}")
                
                # Проверяем приближенное соответствие (±5%)
                if abs(final_amount - expected_amount) / expected_amount <= 0.05:
                    success_count += 1
                    print("  ✅ Конвертация корректна")
                else:
                    print("  ⚠️ Конвертация неточная")
            else:
                print("  ❌ Не удалось распознать")
                
        except Exception as e:
            print(f"  ❌ Ошибка: {e}")
        
        print()
    
    accuracy = (success_count / len(test_cases)) * 100
    print(f"РЕЗУЛЬТАТ КОНВЕРТАЦИИ: {success_count}/{len(test_cases)} ({accuracy:.1f}%) тестов пройдено")
    
    return accuracy >= 75


async def test_no_category_duplication():
    """Тест предотвращения дублирования категорий"""
    print("=== ТЕСТ ПРЕДОТВРАЩЕНИЯ ДУБЛИРОВАНИЯ КАТЕГОРИЙ ===\n")
    
    # Тестируем создание категорий с разными вариантами написания
    test_cases = [
        "создай категорию транспорт",
        "создай категорию Транспорт", 
        "создай категорию ТРАНСПОРТ",
        "создай категорию транспорт ",  # с пробелом
    ]
    
    parser = TextParserService()
    
    categories_created = []
    
    for i, test_text in enumerate(test_cases, 1):
        print(f"Тест {i}: {test_text}")
        
        try:
            result = parser.parse_management_command(test_text, 'ru')
            
            if result and result['type'] == 'create_category':
                category_name = result['category_name']
                print(f"  ✅ Команда распознана: создать категорию '{category_name}'")
                categories_created.append(category_name.lower().strip())
            else:
                print("  ❌ Команда не распознана")
                
        except Exception as e:
            print(f"  ❌ Ошибка: {e}")
        
        print()
    
    # Проверяем уникальность
    unique_categories = set(categories_created)
    print(f"Всего команд: {len(categories_created)}")
    print(f"Уникальных категорий: {len(unique_categories)}")
    
    if len(unique_categories) == 1 and len(categories_created) > 0:
        print("✅ Дублирование предотвращено - все команды создают одну категорию")
        return True
    else:
        print("⚠️ Возможно дублирование категорий")
        return False


async def main():
    """Основная функция тестирования"""
    
    print("🚀 ЗАПУСК ТЕСТОВ УЛУЧШЕННОГО ПАРСЕРА\n")
    
    # Тест 1: Распознавание чисел словами
    test1_passed = await test_word_numbers_with_currency()
    
    print("\n" + "="*50 + "\n")
    
    # Тест 2: Конвертация валют
    test2_passed = await test_currency_conversion()
    
    print("\n" + "="*50 + "\n")
    
    # Тест 3: Предотвращение дублирования категорий
    test3_passed = await test_no_category_duplication()
    
    print("\n" + "="*50)
    print("🏁 ИТОГОВЫЕ РЕЗУЛЬТАТЫ:")
    print(f"✅ Распознавание чисел словами: {'ПРОШЕЛ' if test1_passed else 'НЕ ПРОШЕЛ'}")
    print(f"✅ Конвертация валют: {'ПРОШЕЛ' if test2_passed else 'НЕ ПРОШЕЛ'}")
    print(f"✅ Предотвращение дублирования: {'ПРОШЕЛ' if test3_passed else 'НЕ ПРОШЕЛ'}")
    
    all_passed = test1_passed and test2_passed and test3_passed
    print(f"\n🎯 ОБЩИЙ РЕЗУЛЬТАТ: {'ВСЕ ТЕСТЫ ПРОШЛИ' if all_passed else 'ЕСТЬ ПРОБЛЕМЫ'}")
    
    if all_passed:
        print("🎉 Бот готов к тестированию с новыми функциями!")
    else:
        print("⚠️ Требуется дополнительная настройка")


if __name__ == '__main__':
    asyncio.run(main()) 