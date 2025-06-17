"""
Исполнители голосовых команд для различных модулей
Разделены по функциональности для модульности
"""

from .goal_executor import GoalCommandExecutor
from .source_executor import SourceCommandExecutor
from .settings_executor import SettingsCommandExecutor
from .reminder_executor import ReminderCommandExecutor
from .analytics_executor import AnalyticsCommandExecutor
from .debt_executor import DebtCommandExecutor

__all__ = [
    'GoalCommandExecutor',
    'SourceCommandExecutor', 
    'SettingsCommandExecutor',
    'ReminderCommandExecutor',
    'AnalyticsCommandExecutor',
    'DebtCommandExecutor',
] 