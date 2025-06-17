#!/usr/bin/env python3
import os
import sys
import requests
import json

# Добавляем путь к Django проекту
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

import django
django.setup()

from apps.bot.telegram.services.telegram_api_service import TelegramAPIService

def test_bot_info():
    print("🤖 Тестирование Telegram Bot API...")
    
    service = TelegramAPIService()
    bot_info = service.get_me()
    
    if bot_info and bot_info.get('ok'):
        result = bot_info['result']
        print(f"✅ Бот работает!")
        print(f"📛 Имя: {result.get('first_name')}")
        print(f"🔗 Username: @{result.get('username')}")
        print(f"🆔 ID: {result.get('id')}")
        return True
    else:
        print("❌ Ошибка при подключении к боту")
        print(f"Ответ: {bot_info}")
        return False

def test_webhook_endpoint():
    print("\n📡 Тестирование webhook endpoint...")
    
    try:
        response = requests.get('http://localhost:8000/telegram/webhook/')
        
        if response.status_code == 200:
            print(f"✅ Webhook endpoint доступен: {response.text}")
            return True
        else:
            print(f"❌ Webhook endpoint не доступен: {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print("❌ Сервер не запущен на порту 8000")
        return False

def test_auth_endpoints():
    print("\n🔐 Тестирование аутентификации...")
    
    test_data = {
        "telegram_chat_id": "123456789",
        "phone_number": "+998901234567"
    }
    
    try:
        response = requests.post(
            'http://localhost:8000/api/auth/telegram-login/',
            json=test_data,
            headers={'Content-Type': 'application/json'}
        )
        
        if response.status_code in [200, 201]:
            result = response.json()
            print("✅ Аутентификация работает!")
            print(f"📝 Access Token: {result.get('access', 'N/A')[:50]}...")
            print(f"👤 User ID: {result.get('user', {}).get('id', 'N/A')}")
            return True
        else:
            print(f"❌ Ошибка аутентификации: {response.status_code}")
            print(f"Ответ: {response.text}")
            return False
    except requests.exceptions.ConnectionError:
        print("❌ Сервер не запущен на порту 8000")
        return False

def test_api_endpoints():
    print("\n📊 Тестирование API endpoints...")
    
    endpoints = [
        'http://localhost:8000/api/users/api/users/',
        'http://localhost:8000/api/transactions/api/transactions/',
        'http://localhost:8000/api/categories/api/categories/',
        'http://localhost:8000/swagger/',
    ]
    
    success_count = 0
    
    for endpoint in endpoints:
        try:
            response = requests.get(endpoint)
            if response.status_code in [200, 401]:  # 401 ожидаем для защищенных эндпоинтов
                print(f"✅ {endpoint} - доступен")
                success_count += 1
            else:
                print(f"❌ {endpoint} - ошибка {response.status_code}")
        except:
            print(f"❌ {endpoint} - недоступен")
    
    return success_count == len(endpoints)

def main():
    print("🚀 Тестирование OvozPay Telegram Bot интеграции\n")
    
    results = []
    
    # Тест 1: Проверка Bot API
    results.append(test_bot_info())
    
    # Тест 2: Проверка webhook
    results.append(test_webhook_endpoint())
    
    # Тест 3: Проверка аутентификации
    results.append(test_auth_endpoints())
    
    # Тест 4: Проверка API endpoints
    results.append(test_api_endpoints())
    
    print(f"\n📈 Результаты тестирования:")
    print(f"✅ Успешно: {sum(results)}/4")
    print(f"❌ Неудачно: {4 - sum(results)}/4")
    
    if all(results):
        print("\n🎉 Все тесты прошли успешно! Telegram Bot готов к работе.")
        print("\n📋 Следующие шаги:")
        print("1. Установите ngrok: brew install ngrok")
        print("2. Запустите: ngrok http 8000")
        print("3. Установите webhook: curl -X POST 'https://api.telegram.org/bot8115661165:AAHWkrF_VVfppRcGjxu5ATlt0uOs5qWLJSw/setWebhook' -d 'url=https://your-ngrok-url.ngrok.io/telegram/webhook/'")
        print("4. Найдите бота в Telegram и протестируйте команды /start, /balance, /help")
    else:
        print("\n⚠️ Некоторые тесты не прошли. Проверьте конфигурацию.")

if __name__ == '__main__':
    main() 