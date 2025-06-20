#!/usr/bin/env python
"""
Тестовый скрипт для проверки Telegram аутентификации
"""
import requests
import json

# Настройки
BASE_URL = 'http://localhost:8000'
TEST_TELEGRAM_CHAT_ID = 123456789
TEST_PHONE_NUMBER = '+998901234567'

def test_telegram_auth():
    """Тестирует аутентификацию по Telegram ID"""
    print("🧪 Тестирование Telegram аутентификации...")
    
    # URL для аутентификации
    auth_url = f"{BASE_URL}/api/users/auth/telegram-login/"
    
    # Данные для запроса
    auth_data = {
        'telegram_chat_id': TEST_TELEGRAM_CHAT_ID,
        'phone_number': TEST_PHONE_NUMBER
    }
    
    try:
        # Отправляем запрос
        response = requests.post(auth_url, json=auth_data)
        
        print(f"📤 Запрос: POST {auth_url}")
        print(f"📦 Данные: {json.dumps(auth_data, indent=2)}")
        print(f"📡 Статус: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print("✅ Аутентификация успешна!")
            print(f"🔑 Access Token: {data.get('access', '')[:50]}...")
            print(f"🔄 Refresh Token: {data.get('refresh', '')[:50]}...")
            print(f"👤 User ID: {data.get('user_id')}")
            print(f"📱 Phone: {data.get('phone_number')}")
            print(f"🆕 New User: {data.get('is_new_user')}")
            
            return data.get('access')
        else:
            print("❌ Ошибка аутентификации!")
            print(f"📄 Ответ: {response.text}")
            return None
            
    except requests.exceptions.ConnectionError:
        print("❌ Ошибка подключения к серверу!")
        print("💡 Убедитесь, что Django сервер запущен: python manage.py runserver")
        return None
    except Exception as e:
        print(f"❌ Неожиданная ошибка: {e}")
        return None

def test_api_with_token(access_token):
    """Тестирует API запрос с токеном"""
    if not access_token:
        return
    
    print("\n🧪 Тестирование API с токеном...")
    
    # URL для получения пользователей
    users_url = f"{BASE_URL}/api/users/api/users/"
    
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json'
    }
    
    try:
        response = requests.get(users_url, headers=headers)
        
        print(f"📤 Запрос: GET {users_url}")
        print(f"🔒 Authorization: Bearer {access_token[:20]}...")
        print(f"📡 Статус: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print("✅ API запрос успешен!")
            print(f"📊 Данные: {json.dumps(data, indent=2, ensure_ascii=False)}")
        else:
            print("❌ Ошибка API запроса!")
            print(f"📄 Ответ: {response.text}")
            
    except Exception as e:
        print(f"❌ Ошибка API запроса: {e}")

def test_webhook_endpoint():
    """Тестирует webhook endpoint"""
    print("\n🧪 Тестирование Webhook endpoint...")
    
    webhook_url = f"{BASE_URL}/telegram/webhook/"
    
    # Тестовое обновление от Telegram
    test_update = {
        "update_id": 123456789,
        "message": {
            "message_id": 123,
            "from": {
                "id": TEST_TELEGRAM_CHAT_ID,
                "is_bot": False,
                "first_name": "Test",
                "username": "test_user"
            },
            "chat": {
                "id": TEST_TELEGRAM_CHAT_ID,
                "first_name": "Test",
                "username": "test_user",
                "type": "private"
            },
            "date": 1640995200,
            "text": "/start"
        }
    }
    
    try:
        response = requests.post(webhook_url, json=test_update)
        
        print(f"📤 Запрос: POST {webhook_url}")
        print(f"📦 Тестовое обновление отправлено")
        print(f"📡 Статус: {response.status_code}")
        
        if response.status_code == 200:
            print("✅ Webhook успешно обработал обновление!")
        else:
            print("❌ Ошибка webhook!")
            print(f"📄 Ответ: {response.text}")
            
    except Exception as e:
        print(f"❌ Ошибка webhook запроса: {e}")

if __name__ == "__main__":
    print("🚀 Запуск тестов Telegram Bot API")
    print("=" * 50)
    
    # Тест 1: Аутентификация
    access_token = test_telegram_auth()
    
    # Тест 2: API с токеном
    test_api_with_token(access_token)
    
    # Тест 3: Webhook
    test_webhook_endpoint()
    
    print("\n" + "=" * 50)
    print("🏁 Тесты завершены") 