"""
Команда для тестирования нового UI главного меню
"""

import asyncio
import logging
from django.core.management.base import BaseCommand, CommandError
from django.conf import settings

from apps.bot.services.telegram_api_service import TelegramAPIService
from apps.bot.utils.translations import t

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    """Команда для тестирования главного меню бота"""
    
    help = 'Тестирует новое главное меню Telegram бота'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--chat-id',
            type=int,
            help='ID чата для отправки тестового меню',
            required=True
        )
        parser.add_argument(
            '--language',
            type=str,
            default='ru',
            choices=['ru', 'en', 'uz'],
            help='Язык для тестирования (ru/en/uz)'
        )
    
    def handle(self, *args, **options):
        """Основной метод команды"""
        
        try:
            # Проверяем токен
            token = getattr(settings, 'TELEGRAM_BOT_TOKEN', '')
            if not token:
                raise CommandError(
                    "❌ TELEGRAM_BOT_TOKEN не установлен в настройках"
                )
            
            chat_id = options['chat_id']
            language = options['language']
            
            self.stdout.write(
                self.style.SUCCESS(f"🚀 Тестируем главное меню для чата {chat_id} на языке {language}")
            )
            
            # Запускаем асинхронную функцию
            asyncio.run(self._test_menu_ui(chat_id, language))
            
        except Exception as e:
            raise CommandError(f"❌ Ошибка: {e}")
    
    async def _test_menu_ui(self, chat_id: int, language: str):
        """Асинхронное тестирование UI"""
        
        telegram_api = TelegramAPIService()
        
        try:
            # 1. Отправляем приветствие
            welcome_text = t.get_text('start_welcome', language)
            await telegram_api.send_message(
                chat_id=chat_id,
                text=f"🧪 **ТЕСТ UI ОБНОВЛЕНИЯ**\n\n{welcome_text}",
                parse_mode='Markdown'
            )
            
            # 2. Отправляем главное меню
            menu_text = t.get_text('main_menu', language)
            await telegram_api.send_message(
                chat_id=chat_id,
                text=menu_text,
                reply_markup=t.get_main_menu_keyboard(language)
            )
            
            # 3. Отправляем информацию об обновлениях
            updates_text = f"""
✅ **ОБНОВЛЕНИЯ UI ЗАВЕРШЕНЫ**

🔄 **Что исправлено:**

1. **Главное меню с кнопками**
   📋 Полноценное интерактивное меню
   💰 Баланс | 📊 История
   📂 Категории | 🎯 Цели 
   💸 Долги | ⚙️ Настройки
   ❓ Помощь

2. **Автообновление сообщений**
   🎤 "Обрабатываю..." → результат
   📝 Никакого засорения чата

3. **Команды**
   /menu - главное меню
   /balance - баланс  
   /settings - настройки
   /help - справка

4. **Голосовые сообщения**
   ✅ Распознавание работает
   🔄 Автоматическое редактирование
   
**Протестируйте все функции!** 🚀
            """
            
            await telegram_api.send_message(
                chat_id=chat_id,
                text=updates_text,
                parse_mode='Markdown'
            )
            
            self.stdout.write(
                self.style.SUCCESS("✅ Тестовые сообщения отправлены успешно!")
            )
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"❌ Ошибка отправки: {e}")
            )
            raise 