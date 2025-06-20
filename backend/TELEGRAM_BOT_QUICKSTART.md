# 🚀 Быстрый запуск Telegram Bot OvozPay

## 📋 Чек-лист для тестирования

### 1. ✅ Зависимости установлены
```bash
pip install -r requirements.txt
```

### 2. ✅ Миграции применены
```bash
python manage.py migrate
```

### 3. ✅ Проект проходит проверку
```bash
python manage.py check
```

## 🧪 Быстрое тестирование

### 1. Запустите сервер
```bash
python manage.py runserver 8000
```

### 2. Запустите тестовый скрипт
```bash
python test_telegram_auth.py
```

### 3. Проверьте API в браузере
- Swagger UI: http://localhost:8000/swagger/
- Admin панель: http://localhost:8000/admin/

## 🔧 Настройка webhook для продакшена

### 1. Проверьте статус webhook
```bash
python manage.py check_webhook
```

### 2. Установите webhook
```bash
python manage.py set_webhook --url https://your-domain.com/telegram/webhook/
```

### 3. Удалите webhook (если нужно)
```bash
python manage.py set_webhook --delete
```

## 🎯 Тестирование с реальным ботом

### 1. Создайте бота через @BotFather
1. Найдите `@BotFather` в Telegram
2. Отправьте `/newbot`
3. Укажите имя и username бота
4. Получите токен

### 2. Обновите настройки
```python
# backend/config/settings.py или .env
TELEGRAM_BOT_TOKEN = "your_bot_token_here"
TELEGRAM_WEBHOOK_URL = "https://your-domain.com/telegram/webhook/"
```

### 3. Установите webhook
```bash
python manage.py set_webhook --url https://your-domain.com/telegram/webhook/
```

### 4. Протестируйте команды
- Найдите бота в Telegram
- Отправьте `/start`
- Попробуйте `/balance`, `/help`
- Отправьте голосовое сообщение

## 📊 Мониторинг

### Логи Django
```bash
tail -f logs/django.log  # если настроено логирование в файл
```

### Проверка webhook статуса
```bash
python manage.py check_webhook
```

### Проверка пользователей в базе
```bash
python manage.py shell
>>> from apps.users.models import User
>>> User.objects.filter(telegram_chat_id__isnull=False)
```

## 🐛 Устранение проблем

### Webhook не получает обновления
1. Проверьте, что сервер доступен по HTTPS
2. Проверьте URL webhook: `python manage.py check_webhook`
3. Убедитесь, что порт открыт

### Ошибка 401 в API
1. Проверьте токен в заголовке Authorization
2. Убедитесь, что токен не истек
3. Попробуйте обновить токен через `/api/users/auth/refresh-token/`

### Бот не отвечает
1. Проверьте логи Django
2. Убедитесь, что webhook установлен
3. Проверьте токен бота

## 🔗 Полезные ссылки

- [Telegram Bot API](https://core.telegram.org/bots/api)
- [Полная документация](docs/BOT_API_DOCUMENTATION.md)
- [Django REST Framework](https://www.django-rest-framework.org/)
- [Simple JWT](https://django-rest-framework-simplejwt.readthedocs.io/)

---

**Готово к тестированию! 🎉** 