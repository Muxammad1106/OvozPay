"""
Конфигурация приложения для модуля напоминаний и планировщика OvozPay
Этап 7: Reminders & Scheduler API
"""

from django.apps import AppConfig


class RemindersConfig(AppConfig):
    """Конфигурация приложения reminders"""
    
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.reminders'
    verbose_name = 'Напоминания и планировщик'
    
    def ready(self):
        """Инициализация при запуске приложения"""
        try:
            # Импортируем сигналы, если они есть
            import apps.reminders.signals  # noqa
        except ImportError:
            pass 