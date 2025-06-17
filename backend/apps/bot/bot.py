"""
Главный модуль Telegram Bot для OvozPay
Интеграция с AI модулем для голосового управления
"""

import logging
import asyncio
from typing import Dict, Any

from telegram import Update, BotCommand
from telegram.ext import (
    Updater, 
    CommandHandler, 
    MessageHandler, 
    Filters,
    CallbackContext
)

from django.conf import settings

from .handlers.voice_handler import voice_handler
from .handlers.photo_handler import photo_handler


logger = logging.getLogger(__name__)


class OvozPayBot:
    """Основной класс Telegram Bot для OvozPay"""
    
    def __init__(self):
        self.application = None
        self.is_running = False
    
    def setup_bot(self) -> Updater:
        """Настройка и конфигурация бота"""
        try:
            # Создаем приложение
            self.application = Updater(
                settings.TELEGRAM_BOT_TOKEN
            )
            
            # Регистрируем обработчики
            self._register_handlers()
            
            # Устанавливаем команды бота
            asyncio.create_task(self._setup_bot_commands())
            
            logger.info("Telegram Bot настроен успешно")
            return self.application
            
        except Exception as e:
            logger.error(f"Ошибка настройки бота: {e}")
            raise
    
    def _register_handlers(self):
        """Регистрация обработчиков сообщений"""
        
        # Команды
        self.application.dispatcher.add_handler(CommandHandler("start", self.start_command))
        self.application.dispatcher.add_handler(CommandHandler("help", self.help_command))
        self.application.dispatcher.add_handler(CommandHandler("balance", self.balance_command))
        self.application.dispatcher.add_handler(CommandHandler("stats", self.stats_command))
        self.application.dispatcher.add_handler(CommandHandler("goals", self.goals_command))
        self.application.dispatcher.add_handler(CommandHandler("reminders", self.reminders_command))
        self.application.dispatcher.add_handler(CommandHandler("settings", self.settings_command))
        
        # Голосовые сообщения - ГЛАВНАЯ ФИЧА
        self.application.dispatcher.add_handler(
            MessageHandler(Filters.voice, voice_handler.handle_voice_message)
        )
        
        # Фото сообщения - СКАНИРОВАНИЕ ЧЕКОВ
        self.application.dispatcher.add_handler(
            MessageHandler(Filters.photo, photo_handler.handle_photo_message)
        )
        
        # Текстовые сообщения (резервный способ)
        self.application.dispatcher.add_handler(
            MessageHandler(Filters.text & ~Filters.command, self.handle_text_message)
        )
        
        logger.info("Обработчики зарегистрированы")
    
    async def _setup_bot_commands(self):
        """Устанавливает список команд бота"""
        try:
            commands = [
                BotCommand("start", "🚀 Начать работу с ботом"),
                BotCommand("help", "❓ Помощь и инструкции"),
                BotCommand("balance", "💰 Показать баланс"),
                BotCommand("stats", "📊 Статистика расходов"),
                BotCommand("goals", "🎯 Управление целями"),
                BotCommand("reminders", "⏰ Управление напоминаниями"),
                BotCommand("settings", "⚙️ Настройки"),
            ]
            
            await self.application.bot.set_my_commands(commands)
            logger.info("Команды бота установлены")
            
        except Exception as e:
            logger.error(f"Ошибка установки команд: {e}")
    
    async def start_command(self, update: Update, context: CallbackContext):
        """Обработчик команды /start"""
        welcome_message = """
🎉 Добро пожаловать в OvozPay!

💬 Я умею управлять вашими финансами голосом и фото!

🎤 **Отправьте голосовое сообщение** и скажите:
• "Покажи мой баланс"
• "Добавь расход хлеб 5000 сум"  
• "Создай цель накопить миллион на машину"
• "Покажи мои цели"
• "Создай напоминание купить молоко завтра"
• "Покажи расходы за месяц"
• "Смени валюту на доллар"

📸 **Отправьте фото чека** и я:
• Автоматически распознаю все товары и цены
• Создам транзакцию расхода  
• Покажу детальную информацию о покупке
• Добавлю в нужную категорию

🌍 Поддерживаю языки: Русский, Узбекский, English

📝 Также можете использовать текстовые команды:
/balance - баланс
/stats - статистика  
/goals - цели
/reminders - напоминания
/settings - настройки
/help - помощь

🚀 Начните с голосового сообщения или фото чека!
        """
        
        await update.message.reply_text(welcome_message)
    
    async def help_command(self, update: Update, context: CallbackContext):
        """Обработчик команды /help"""
        help_message = """
❓ **Помощь по OvozPay**

🎤 **ГОЛОСОВЫЕ КОМАНДЫ** (основной способ):

💰 **Финансы:**
• "Покажи баланс"
• "Добавь расход [описание] [сумма]"
• "Добавь доход [сумма] от [источник]"

🎯 **Цели:**
• "Создай цель накопить [сумма] на [название]"
• "Покажи мои цели"
• "Добавь [сумма] к цели [название]"

⏰ **Напоминания:**
• "Создай напоминание [текст] на [время]"
• "Покажи напоминания"
• "Удали напоминание [название]"

📊 **Аналитика:**
• "Покажи расходы за [период]"
• "Статистика по категории [название]"
• "Топ категорий"

💳 **Долги:**
• "Кто мне должен"
• "Кому я должен"
• "Дал в долг [имя] [сумма]"

⚙️ **Настройки:**
• "Смени валюту на [валюта]"
• "Поменяй язык на [язык]"

📸 **ФОТО ЧЕКОВ** (автоматическое сканирование):
• Отправьте фото чека - я распознаю все товары и цены
• Автоматически создам транзакцию расхода
• Определю категорию покупки
• Покажу детальную информацию

💡 **Советы:**
• Для голоса: говорите четко и не торопясь
• Для фото: хорошее освещение, четкий текст чека
• Поддерживаю чеки на русском, узбекском, английском

🌍 **Языки:** русский, узбекский, английский
        """
        
        await update.message.reply_text(help_message)
    
    async def balance_command(self, update: Update, context: CallbackContext):
        """Обработчик команды /balance"""
        await update.message.reply_text(
            "💰 Для получения баланса отправьте голосовое сообщение:\n"
            "🎤 \"Покажи мой баланс\""
        )
    
    async def stats_command(self, update: Update, context: CallbackContext):
        """Обработчик команды /stats"""
        await update.message.reply_text(
            "📊 Для получения статистики отправьте голосовое сообщение:\n"
            "🎤 \"Покажи статистику\" или \"Мои расходы\""
        )
    
    async def goals_command(self, update: Update, context: CallbackContext):
        """Обработчик команды /goals"""
        await update.message.reply_text(
            "🎯 Для управления целями отправьте голосовое сообщение:\n"
            "🎤 \"Покажи мои цели\" или \"Создай цель накопить [сумма] на [название]\""
        )
    
    async def reminders_command(self, update: Update, context: CallbackContext):
        """Обработчик команды /reminders"""
        await update.message.reply_text(
            "⏰ Для управления напоминаниями отправьте голосовое сообщение:\n"
            "🎤 \"Покажи напоминания\" или \"Создай напоминание [текст] на [время]\""
        )
    
    async def settings_command(self, update: Update, context: CallbackContext):
        """Обработчик команды /settings"""
        await update.message.reply_text(
            "⚙️ Для изменения настроек отправьте голосовое сообщение:\n"
            "🎤 \"Смени валюту на доллар\" или \"Поменяй язык на узбекский\""
        )
    
    async def handle_text_message(self, update: Update, context: CallbackContext):
        """Обработчик текстовых сообщений"""
        text = update.message.text.lower()
        
        # Простые текстовые команды
        if any(word in text for word in ['баланс', 'balance', 'balans']):
            await update.message.reply_text(
                "💰 Для получения точного баланса лучше использовать голосовое сообщение:\n"
                "🎤 \"Покажи мой баланс\""
            )
        elif any(word in text for word in ['помощь', 'help', 'yordam']):
            await self.help_command(update, context)
        else:
            await update.message.reply_text(
                "🎤 **Отправьте голосовое сообщение** для полного управления финансами!\n\n"
                "💡 Или используйте команды: /help, /balance, /goals, /stats\n\n"
                "🗣️ Примеры голосовых команд:\n"
                "• \"Покажи баланс\"\n"
                "• \"Добавь расход хлеб 5000\"\n"
                "• \"Создай цель на машину\""
            )
    
    async def start_polling(self):
        """Запуск бота в режиме polling"""
        try:
            if not self.application:
                self.setup_bot()
            
            logger.info("Запуск Telegram Bot...")
            self.is_running = True
            
            # Запускаем бота
            await self.application.start()
            await self.application.updater.start_polling(
                allowed_updates=["message", "callback_query"]
            )
            
            logger.info("🤖 OvozPay Bot запущен и готов к работе!")
            
            # Ждем остановки
            await self.application.updater.idle()
            
        except Exception as e:
            logger.error(f"Ошибка запуска бота: {e}")
            raise
        finally:
            await self.stop()
    
    async def stop(self):
        """Остановка бота"""
        try:
            if self.application and self.is_running:
                logger.info("Остановка Telegram Bot...")
                
                await self.application.updater.stop()
                await self.application.stop()
                await self.application.shutdown()
                
                self.is_running = False
                logger.info("Telegram Bot остановлен")
                
        except Exception as e:
            logger.error(f"Ошибка остановки бота: {e}")


# Глобальный экземпляр бота
bot = OvozPayBot()


# Функция для запуска бота из Django management command
async def run_bot():
    """Запуск бота"""
    try:
        await bot.start_polling()
    except KeyboardInterrupt:
        logger.info("Получен сигнал остановки")
    except Exception as e:
        logger.error(f"Критическая ошибка бота: {e}")
        raise
    finally:
        await bot.stop()


# Функция для интеграции с Django
def get_bot_application():
    """Возвращает настроенное приложение бота для интеграции с Django"""
    return bot.setup_bot() 