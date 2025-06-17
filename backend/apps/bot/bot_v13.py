"""
Главный модуль Telegram Bot для OvozPay (совместимость с python-telegram-bot 13.15)
Интеграция с AI модулем для голосового управления
"""

import logging
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

from .handlers.voice_handler_v13 import voice_handler
from .handlers.photo_handler_v13 import photo_handler


logger = logging.getLogger(__name__)


class OvozPayBot:
    """Основной класс Telegram Bot для OvozPay (v13 совместимый)"""
    
    def __init__(self):
        self.updater = None
        self.is_running = False
    
    def setup_bot(self) -> Updater:
        """Настройка и конфигурация бота"""
        try:
            # Создаем Updater
            self.updater = Updater(
                token=settings.TELEGRAM_BOT_TOKEN,
                use_context=True
            )
            
            # Получаем диспетчер
            dispatcher = self.updater.dispatcher
            
            # Регистрируем обработчики
            self._register_handlers(dispatcher)
            
            logger.info("Telegram Bot настроен успешно")
            return self.updater
            
        except Exception as e:
            logger.error(f"Ошибка настройки бота: {e}")
            raise
    
    def _register_handlers(self, dispatcher):
        """Регистрация обработчиков сообщений"""
        
        # Команды
        dispatcher.add_handler(CommandHandler("start", self.start_command))
        dispatcher.add_handler(CommandHandler("help", self.help_command))
        dispatcher.add_handler(CommandHandler("balance", self.balance_command))
        dispatcher.add_handler(CommandHandler("stats", self.stats_command))
        dispatcher.add_handler(CommandHandler("goals", self.goals_command))
        dispatcher.add_handler(CommandHandler("reminders", self.reminders_command))
        dispatcher.add_handler(CommandHandler("settings", self.settings_command))
        
        # Голосовые сообщения - ГЛАВНАЯ ФИЧА
        dispatcher.add_handler(
            MessageHandler(Filters.voice, voice_handler.handle_voice_message)
        )
        
        # Фото сообщения - СКАНИРОВАНИЕ ЧЕКОВ
        dispatcher.add_handler(
            MessageHandler(Filters.photo, photo_handler.handle_photo_message)
        )
        
        # Текстовые сообщения (резервный способ)
        dispatcher.add_handler(
            MessageHandler(Filters.text & ~Filters.command, self.handle_text_message)
        )
        
        logger.info("Обработчики зарегистрированы")
    
    def start_command(self, update: Update, context: CallbackContext):
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
        
        update.message.reply_text(welcome_message)
    
    def help_command(self, update: Update, context: CallbackContext):
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
        
        update.message.reply_text(help_message)
    
    def balance_command(self, update: Update, context: CallbackContext):
        """Обработчик команды /balance"""
        update.message.reply_text(
            "💰 Для получения баланса отправьте голосовое сообщение:\n"
            "🎤 \"Покажи мой баланс\""
        )
    
    def stats_command(self, update: Update, context: CallbackContext):
        """Обработчик команды /stats"""
        update.message.reply_text(
            "📊 Для получения статистики отправьте голосовое сообщение:\n"
            "🎤 \"Покажи статистику\" или \"Мои расходы\""
        )
    
    def goals_command(self, update: Update, context: CallbackContext):
        """Обработчик команды /goals"""
        update.message.reply_text(
            "🎯 Для управления целями отправьте голосовое сообщение:\n"
            "🎤 \"Покажи мои цели\" или \"Создай цель накопить [сумма] на [название]\""
        )
    
    def reminders_command(self, update: Update, context: CallbackContext):
        """Обработчик команды /reminders"""
        update.message.reply_text(
            "⏰ Для управления напоминаниями отправьте голосовое сообщение:\n"
            "🎤 \"Покажи напоминания\" или \"Создай напоминание [текст] на [время]\""
        )
    
    def settings_command(self, update: Update, context: CallbackContext):
        """Обработчик команды /settings"""
        update.message.reply_text(
            "⚙️ Для изменения настроек отправьте голосовое сообщение:\n"
            "🎤 \"Смени валюту на доллар\" или \"Поменяй язык на узбекский\""
        )
    
    def handle_text_message(self, update: Update, context: CallbackContext):
        """Обработчик текстовых сообщений"""
        text = update.message.text.lower()
        
        # Простые текстовые команды
        if any(word in text for word in ['баланс', 'balance', 'balans']):
            update.message.reply_text(
                "💰 Для получения точного баланса лучше использовать голосовое сообщение:\n"
                "🎤 \"Покажи мой баланс\""
            )
        elif any(word in text for word in ['помощь', 'help', 'yordam']):
            self.help_command(update, context)
        else:
            update.message.reply_text(
                "🎤 **Отправьте голосовое сообщение** для полного управления финансами!\n\n"
                "📸 **Или отправьте фото чека** для автоматического сканирования!\n\n"
                "💡 Или используйте команды: /help, /balance, /goals, /stats\n\n"
                "🗣️ Примеры голосовых команд:\n"
                "• \"Покажи баланс\"\n"
                "• \"Добавь расход хлеб 5000\"\n"
                "• \"Создай цель на машину\""
            )
    
    def start_polling(self):
        """Запуск бота в режиме polling"""
        try:
            if not self.updater:
                self.setup_bot()
            
            logger.info("Запуск Telegram Bot...")
            self.is_running = True
            
            # Запускаем бота
            self.updater.start_polling()
            
            logger.info("🤖 OvozPay Bot запущен и готов к работе!")
            logger.info("📱 Отправьте /start боту для начала работы")
            logger.info("🎤 Поддерживаются голосовые сообщения")
            logger.info("📸 Поддерживается сканирование чеков")
            
            # Ждем остановки
            self.updater.idle()
            
        except Exception as e:
            logger.error(f"Ошибка запуска бота: {e}")
            raise
        finally:
            self.stop()
    
    def stop(self):
        """Остановка бота"""
        try:
            if self.updater and self.is_running:
                logger.info("Остановка Telegram Bot...")
                
                self.updater.stop()
                
                self.is_running = False
                logger.info("Telegram Bot остановлен")
                
        except Exception as e:
            logger.error(f"Ошибка остановки бота: {e}")


# Глобальный экземпляр бота
bot = OvozPayBot()


# Функция для запуска бота из Django management command
def run_bot():
    """Запуск бота"""
    try:
        bot.start_polling()
    except KeyboardInterrupt:
        logger.info("Получен сигнал остановки")
        bot.stop()
    except Exception as e:
        logger.error(f"Критическая ошибка бота: {e}")
        raise


def get_bot_application():
    """Получение экземпляра бота для использования в других модулях"""
    if not bot.updater:
        bot.setup_bot()
    return bot.updater 