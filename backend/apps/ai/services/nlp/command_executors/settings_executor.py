"""
Исполнитель голосовых команд для управления настройками приложения
"""

import re
from typing import Dict, Any
from django.db import transaction

from apps.users.models import User
from apps.users.models import UserSettings
from apps.ai.models import VoiceCommand
from apps.ai.services.nlp.extended_commands import ExtendedCommandPatterns


class SettingsCommandExecutor:
    """Исполнитель команд для управления настройками"""
    
    # Поддерживаемые валюты
    SUPPORTED_CURRENCIES = {
        'ru': {
            'сум': 'UZS',
            'узбекский сум': 'UZS',
            'доллар': 'USD',
            'долларов': 'USD',
            'рубль': 'RUB',
            'рублей': 'RUB',
            'евро': 'EUR',
        },
        'uz': {
            'som': 'UZS',
            'oʻzbek somi': 'UZS',
            'dollar': 'USD',
            'rubl': 'RUB',
            'evro': 'EUR',
        },
        'en': {
            'sum': 'UZS',
            'uzbek sum': 'UZS',
            'dollar': 'USD',
            'dollars': 'USD',
            'ruble': 'RUB',
            'rubles': 'RUB',
            'euro': 'EUR',
        }
    }
    
    # Поддерживаемые языки
    SUPPORTED_LANGUAGES = {
        'ru': {
            'русский': 'ru',
            'узбекский': 'uz',
            'английский': 'en',
        },
        'uz': {
            'rus': 'ru',
            'oʻzbek': 'uz',
            'ingliz': 'en',
        },
        'en': {
            'russian': 'ru',
            'uzbek': 'uz',
            'english': 'en',
        }
    }
    
    def __init__(self, user: User):
        self.user = user
        self.patterns = ExtendedCommandPatterns.SETTINGS_COMMANDS
    
    def execute_command(self, command_type: str, text: str, language: str = 'ru') -> Dict[str, Any]:
        """Выполняет команду управления настройками"""
        try:
            if command_type == 'change_currency':
                return self._change_currency(text, language)
            elif command_type == 'change_language':
                return self._change_language(text, language)
            elif command_type == 'manage_notifications':
                return self._manage_notifications(text, language)
            else:
                return {
                    'success': False,
                    'error': f'Неизвестный тип команды: {command_type}'
                }
        except Exception as e:
            return {
                'success': False,
                'error': f'Ошибка выполнения команды: {str(e)}'
            }
    
    def _change_currency(self, text: str, language: str) -> Dict[str, Any]:
        """Изменяет валюту пользователя"""
        patterns = self.patterns['change_currency'].get(language, [])
        
        for pattern in patterns:
            match = re.search(pattern, text.lower())
            if match:
                currency_name = match.group(1).strip().lower()
                
                # Находим код валюты
                currency_code = self._get_currency_code(currency_name, language)
                if not currency_code:
                    return {
                        'success': False,
                        'error': self._get_message(language, 'unsupported_currency', {'currency': currency_name})
                    }
                
                try:
                    with transaction.atomic():
                        # Получаем или создаем настройки пользователя
                        settings, created = UserSettings.objects.get_or_create(
                            user=self.user,
                            defaults={'currency': currency_code}
                        )
                        
                        old_currency = settings.currency
                        settings.currency = currency_code
                        settings.save()
                        
                        # Логируем команду
                        VoiceCommand.objects.create(
                            user=self.user,
                            command_type='change_currency',
                            original_text=text,
                            processed_data={
                                'old_currency': old_currency,
                                'new_currency': currency_code,
                                'currency_name': currency_name
                            },
                            is_successful=True
                        )
                        
                        return {
                            'success': True,
                            'message': self._get_success_message(language, 'currency_changed', {
                                'currency': self._get_currency_name(currency_code, language)
                            }),
                            'data': {
                                'old_currency': old_currency,
                                'new_currency': currency_code
                            }
                        }
                        
                except Exception as e:
                    return {
                        'success': False,
                        'error': f'Ошибка изменения валюты: {str(e)}'
                    }
        
        return {
            'success': False,
            'error': 'Не удалось распознать команду изменения валюты'
        }
    
    def _change_language(self, text: str, language: str) -> Dict[str, Any]:
        """Изменяет язык интерфейса"""
        patterns = self.patterns['change_language'].get(language, [])
        
        for pattern in patterns:
            match = re.search(pattern, text.lower())
            if match:
                language_name = match.group(1).strip().lower()
                
                # Находим код языка
                language_code = self._get_language_code(language_name, language)
                if not language_code:
                    return {
                        'success': False,
                        'error': self._get_message(language, 'unsupported_language', {'language': language_name})
                    }
                
                try:
                    with transaction.atomic():
                        # Получаем или создаем настройки пользователя
                        settings, created = UserSettings.objects.get_or_create(
                            user=self.user,
                            defaults={'language': language_code}
                        )
                        
                        old_language = settings.language
                        settings.language = language_code
                        settings.save()
                        
                        # Логируем команду
                        VoiceCommand.objects.create(
                            user=self.user,
                            command_type='change_language',
                            original_text=text,
                            processed_data={
                                'old_language': old_language,
                                'new_language': language_code,
                                'language_name': language_name
                            },
                            is_successful=True
                        )
                        
                        return {
                            'success': True,
                            'message': self._get_success_message(language_code, 'language_changed', {
                                'language': self._get_language_name(language_code, language_code)
                            }),
                            'data': {
                                'old_language': old_language,
                                'new_language': language_code
                            }
                        }
                        
                except Exception as e:
                    return {
                        'success': False,
                        'error': f'Ошибка изменения языка: {str(e)}'
                    }
        
        return {
            'success': False,
            'error': 'Не удалось распознать команду изменения языка'
        }
    
    def _manage_notifications(self, text: str, language: str) -> Dict[str, Any]:
        """Управляет настройками уведомлений"""
        patterns = self.patterns['manage_notifications'].get(language, [])
        
        # Показать настройки уведомлений
        if any(re.search(pattern, text.lower()) for pattern in [
            r'настрой уведомления', r'покажи настройки уведомлений',
            r'bildirishnomalar sozlamalari',
            r'notification settings'
        ]):
            return self._show_notification_settings(language)
        
        # Включить/отключить уведомления
        for pattern in patterns:
            if 'включи' in pattern or 'отключи' in pattern or 'enable' in pattern or 'disable' in pattern:
                match = re.search(pattern, text.lower())
                if match:
                    groups = match.groups()
                    
                    # Определяем действие и тип уведомлений
                    if language == 'ru':
                        if 'включи' in text.lower():
                            action = 'enable'
                        elif 'отключи' in text.lower():
                            action = 'disable'
                        else:
                            continue
                        notification_type = groups[0] if groups else 'все'
                    elif language == 'en':
                        action = 'enable' if 'enable' in text.lower() else 'disable'
                        notification_type = groups[0] if groups else 'all'
                    else:
                        action = 'enable' if 'yoq' not in text.lower() else 'disable'
                        notification_type = groups[0] if groups else 'все'
                    
                    return self._toggle_notifications(notification_type, action, language)
        
        return {
            'success': False,
            'error': 'Не удалось распознать команду управления уведомлениями'
        }
    
    def _show_notification_settings(self, language: str) -> Dict[str, Any]:
        """Показывает текущие настройки уведомлений"""
        try:
            settings = UserSettings.objects.filter(user=self.user).first()
            
            if not settings:
                settings = UserSettings.objects.create(user=self.user)
            
            # Получаем все настройки уведомлений
            notifications_data = {
                'reminders_enabled': getattr(settings, 'reminders_enabled', True),
                'goals_enabled': getattr(settings, 'goals_notifications_enabled', True),
                'debts_enabled': getattr(settings, 'debts_notifications_enabled', True),
                'analytics_enabled': getattr(settings, 'analytics_notifications_enabled', True),
            }
            
            return {
                'success': True,
                'message': self._get_message(language, 'notification_settings'),
                'data': {
                    'settings': notifications_data,
                    'language': settings.language,
                    'currency': settings.currency
                }
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f'Ошибка получения настроек: {str(e)}'
            }
    
    def _toggle_notifications(self, notification_type: str, action: str, language: str) -> Dict[str, Any]:
        """Включает/отключает уведомления определенного типа"""
        try:
            with transaction.atomic():
                settings, created = UserSettings.objects.get_or_create(user=self.user)
                
                enabled = action == 'enable'
                updated_fields = []
                
                # Определяем какие поля обновлять
                if any(word in notification_type.lower() for word in ['напоминания', 'eslatma', 'reminder']):
                    settings.reminders_enabled = enabled
                    updated_fields.append('reminders')
                elif any(word in notification_type.lower() for word in ['цели', 'maqsad', 'goal']):
                    settings.goals_notifications_enabled = enabled
                    updated_fields.append('goals')
                elif any(word in notification_type.lower() for word in ['долги', 'qarz', 'debt']):
                    settings.debts_notifications_enabled = enabled
                    updated_fields.append('debts')
                elif any(word in notification_type.lower() for word in ['аналитика', 'statistika', 'analytics']):
                    settings.analytics_notifications_enabled = enabled
                    updated_fields.append('analytics')
                else:
                    # Все уведомления
                    settings.reminders_enabled = enabled
                    settings.goals_notifications_enabled = enabled
                    settings.debts_notifications_enabled = enabled
                    settings.analytics_notifications_enabled = enabled
                    updated_fields = ['all']
                
                settings.save()
                
                # Логируем команду
                VoiceCommand.objects.create(
                    user=self.user,
                    command_type='manage_notifications',
                    original_text=f"{action} {notification_type} notifications",
                    processed_data={
                        'action': action,
                        'notification_type': notification_type,
                        'updated_fields': updated_fields
                    },
                    is_successful=True
                )
                
                return {
                    'success': True,
                    'message': self._get_success_message(language, 'notifications_updated', {
                        'action': 'включены' if enabled else 'отключены',
                        'type': notification_type
                    }),
                    'data': {
                        'action': action,
                        'notification_type': notification_type,
                        'updated_fields': updated_fields
                    }
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': f'Ошибка изменения настроек уведомлений: {str(e)}'
            }
    
    def _get_currency_code(self, currency_name: str, language: str) -> str:
        """Возвращает код валюты по названию"""
        currencies = self.SUPPORTED_CURRENCIES.get(language, {})
        return currencies.get(currency_name.lower())
    
    def _get_language_code(self, language_name: str, language: str) -> str:
        """Возвращает код языка по названию"""
        languages = self.SUPPORTED_LANGUAGES.get(language, {})
        return languages.get(language_name.lower())
    
    def _get_currency_name(self, currency_code: str, language: str) -> str:
        """Возвращает название валюты по коду"""
        currency_names = {
            'ru': {'UZS': 'сум', 'USD': 'доллар', 'RUB': 'рубль', 'EUR': 'евро'},
            'uz': {'UZS': 'som', 'USD': 'dollar', 'RUB': 'rubl', 'EUR': 'evro'},
            'en': {'UZS': 'sum', 'USD': 'dollar', 'RUB': 'ruble', 'EUR': 'euro'},
        }
        return currency_names.get(language, {}).get(currency_code, currency_code)
    
    def _get_language_name(self, language_code: str, language: str) -> str:
        """Возвращает название языка по коду"""
        language_names = {
            'ru': {'ru': 'русский', 'uz': 'узбекский', 'en': 'английский'},
            'uz': {'ru': 'rus', 'uz': 'oʻzbek', 'en': 'ingliz'},
            'en': {'ru': 'Russian', 'uz': 'Uzbek', 'en': 'English'},
        }
        return language_names.get(language, {}).get(language_code, language_code)
    
    def _get_message(self, language: str, key: str, params: Dict = None) -> str:
        """Возвращает локализованное сообщение"""
        messages = {
            'ru': {
                'unsupported_currency': 'Валюта "{currency}" не поддерживается',
                'unsupported_language': 'Язык "{language}" не поддерживается',
                'notification_settings': 'Текущие настройки уведомлений',
            },
            'uz': {
                'unsupported_currency': '"{currency}" valyutasi qoʻllab-quvvatlanmaydi',
                'unsupported_language': '"{language}" tili qoʻllab-quvvatlanmaydi',
                'notification_settings': 'Hozirgi bildirishnoma sozlamalari',
            },
            'en': {
                'unsupported_currency': 'Currency "{currency}" is not supported',
                'unsupported_language': 'Language "{language}" is not supported',
                'notification_settings': 'Current notification settings',
            }
        }
        
        msg = messages.get(language, messages['ru']).get(key, key)
        if params:
            try:
                return msg.format(**params)
            except KeyError:
                return msg
        return msg
    
    def _get_success_message(self, language: str, key: str, params: Dict = None) -> str:
        """Возвращает сообщение об успешном выполнении"""
        messages = {
            'ru': {
                'currency_changed': 'Валюта изменена на {currency}',
                'language_changed': 'Язык изменен на {language}',
                'notifications_updated': 'Уведомления "{type}" {action}',
            },
            'uz': {
                'currency_changed': 'Valyuta {currency}ga oʻzgartirildi',
                'language_changed': 'Til {language}ga oʻzgartirildi',
                'notifications_updated': '"{type}" bildirish­nomalari {action}',
            },
            'en': {
                'currency_changed': 'Currency changed to {currency}',
                'language_changed': 'Language changed to {language}',
                'notifications_updated': '"{type}" notifications {action}',
            }
        }
        
        msg = messages.get(language, messages['ru']).get(key, key)
        if params:
            try:
                return msg.format(**params)
            except KeyError:
                return msg
        return msg 