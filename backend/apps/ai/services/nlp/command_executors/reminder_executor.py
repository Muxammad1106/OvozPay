"""
Исполнитель голосовых команд для управления напоминаниями
"""

import re
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from django.utils import timezone
from django.db import transaction

from apps.users.models import User
from apps.reminders.models import Reminder
from apps.ai.models import VoiceCommand
from apps.ai.services.nlp.extended_commands import ExtendedCommandPatterns


class ReminderCommandExecutor:
    """Исполнитель команд для управления напоминаниями"""
    
    def __init__(self, user: User):
        self.user = user
        self.patterns = ExtendedCommandPatterns.REMINDER_COMMANDS
    
    def execute_command(self, command_type: str, text: str, language: str = 'ru') -> Dict[str, Any]:
        """Выполняет команду управления напоминаниями"""
        try:
            if command_type == 'create_reminder':
                return self._create_reminder(text, language)
            elif command_type == 'manage_reminders':
                return self._manage_reminders(text, language)
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
    
    def _create_reminder(self, text: str, language: str) -> Dict[str, Any]:
        """Создает новое напоминание"""
        patterns = self.patterns['create_reminder'].get(language, [])
        
        for pattern in patterns:
            match = re.search(pattern, text.lower())
            if match:
                groups = match.groups()
                
                if len(groups) >= 2:
                    reminder_text = groups[0].strip()
                    time_str = groups[1].strip()
                    
                    # Парсим время напоминания
                    reminder_time = self._parse_reminder_time(time_str, language)
                    if not reminder_time:
                        return {
                            'success': False,
                            'error': 'Не удалось распознать время напоминания'
                        }
                    
                    try:
                        with transaction.atomic():
                            reminder = Reminder.objects.create(
                                user=self.user,
                                title=reminder_text,
                                description=f'Голосовое напоминание: {reminder_text}',
                                reminder_time=reminder_time,
                                is_active=True,
                                is_completed=False
                            )
                            
                            # Логируем команду
                            VoiceCommand.objects.create(
                                user=self.user,
                                command_type='create_reminder',
                                original_text=text,
                                processed_data={
                                    'reminder_id': reminder.id,
                                    'title': reminder_text,
                                    'reminder_time': reminder_time.isoformat()
                                },
                                is_successful=True
                            )
                            
                            return {
                                'success': True,
                                'message': self._get_success_message(language, 'reminder_created', {
                                    'title': reminder_text,
                                    'time': reminder_time.strftime('%d.%m.%Y %H:%M')
                                }),
                                'data': {
                                    'reminder_id': reminder.id,
                                    'title': reminder.title,
                                    'reminder_time': reminder.reminder_time.isoformat()
                                }
                            }
                            
                    except Exception as e:
                        return {
                            'success': False,
                            'error': f'Ошибка создания напоминания: {str(e)}'
                        }
                elif len(groups) == 1:
                    # Только текст напоминания, время не указано
                    reminder_text = groups[0].strip()
                    
                    try:
                        with transaction.atomic():
                            # Создаем напоминание на завтра в 10:00
                            tomorrow = timezone.now() + timedelta(days=1)
                            reminder_time = tomorrow.replace(hour=10, minute=0, second=0, microsecond=0)
                            
                            reminder = Reminder.objects.create(
                                user=self.user,
                                title=reminder_text,
                                description=f'Голосовое напоминание: {reminder_text}',
                                reminder_time=reminder_time,
                                is_active=True,
                                is_completed=False
                            )
                            
                            # Логируем команду
                            VoiceCommand.objects.create(
                                user=self.user,
                                command_type='create_reminder',
                                original_text=text,
                                processed_data={
                                    'reminder_id': reminder.id,
                                    'title': reminder_text,
                                    'reminder_time': reminder_time.isoformat(),
                                    'default_time': True
                                },
                                is_successful=True
                            )
                            
                            return {
                                'success': True,
                                'message': self._get_success_message(language, 'reminder_created_default', {
                                    'title': reminder_text,
                                    'time': reminder_time.strftime('%d.%m.%Y %H:%M')
                                }),
                                'data': {
                                    'reminder_id': reminder.id,
                                    'title': reminder.title,
                                    'reminder_time': reminder.reminder_time.isoformat()
                                }
                            }
                            
                    except Exception as e:
                        return {
                            'success': False,
                            'error': f'Ошибка создания напоминания: {str(e)}'
                        }
        
        return {
            'success': False,
            'error': 'Не удалось распознать команду создания напоминания'
        }
    
    def _manage_reminders(self, text: str, language: str) -> Dict[str, Any]:
        """Управляет существующими напоминаниями"""
        
        # Показать все напоминания
        if any(re.search(pattern, text.lower()) for pattern in [
            r'покажи.*напоминания', r'мои напоминания', r'активные напоминания',
            r'eslatmalarimni.*koʻrsat', r'faol eslatmalar',
            r'show.*reminders', r'active reminders'
        ]):
            return self._show_reminders(language)
        
        # Удалить напоминание
        for pattern in [
            r'удали напоминание\s+(.+)',
            r'(.+?)\s+eslatmani\s+oʻchir',
            r'delete reminder\s+(.+)',
        ]:
            match = re.search(pattern, text.lower())
            if match:
                reminder_title = match.group(1)
                return self._delete_reminder(reminder_title, language)
        
        # Отложить напоминание
        for pattern in [
            r'отложи напоминание\s+(.+?)\s+на\s+(.+)',
        ]:
            match = re.search(pattern, text.lower())
            if match:
                reminder_title, new_time_str = match.groups()
                return self._postpone_reminder(reminder_title, new_time_str, language)
        
        # Выполнить напоминание
        for pattern in [
            r'выполнено напоминание\s+(.+)',
            r'готово напоминание\s+(.+)',
            r'сделано\s+(.+)',
        ]:
            match = re.search(pattern, text.lower())
            if match:
                reminder_title = match.group(1)
                return self._complete_reminder(reminder_title, language)
        
        return {
            'success': False,
            'error': 'Не удалось распознать команду управления напоминаниями'
        }
    
    def _show_reminders(self, language: str) -> Dict[str, Any]:
        """Показывает все активные напоминания"""
        reminders = Reminder.objects.filter(
            user=self.user,
            is_active=True,
            is_completed=False
        ).order_by('reminder_time')
        
        if not reminders.exists():
            return {
                'success': True,
                'message': self._get_message(language, 'no_reminders'),
                'data': {'reminders': []}
            }
        
        now = timezone.now()
        reminders_data = []
        
        for reminder in reminders:
            is_overdue = reminder.reminder_time < now
            time_diff = reminder.reminder_time - now
            
            if is_overdue:
                time_diff = now - reminder.reminder_time
                status = 'overdue'
            else:
                status = 'upcoming'
            
            reminders_data.append({
                'id': reminder.id,
                'title': reminder.title,
                'description': reminder.description,
                'reminder_time': reminder.reminder_time.isoformat(),
                'status': status,
                'is_overdue': is_overdue,
                'time_diff_hours': int(time_diff.total_seconds() / 3600),
                'formatted_time': reminder.reminder_time.strftime('%d.%m.%Y %H:%M')
            })
        
        return {
            'success': True,
            'message': self._get_message(language, 'reminders_list', {
                'count': len(reminders_data),
                'overdue': len([r for r in reminders_data if r['is_overdue']])
            }),
            'data': {'reminders': reminders_data}
        }
    
    def _delete_reminder(self, reminder_title: str, language: str) -> Dict[str, Any]:
        """Удаляет напоминание"""
        try:
            reminder = Reminder.objects.filter(
                user=self.user,
                title__icontains=reminder_title.strip(),
                is_active=True,
                is_completed=False
            ).first()
            
            if not reminder:
                return {
                    'success': False,
                    'error': self._get_message(language, 'reminder_not_found', {'title': reminder_title})
                }
            
            with transaction.atomic():
                reminder.is_active = False
                reminder.save()
                
                # Логируем команду
                VoiceCommand.objects.create(
                    user=self.user,
                    command_type='delete_reminder',
                    original_text=f"Удалить напоминание {reminder_title}",
                    processed_data={
                        'reminder_id': reminder.id,
                        'title': reminder.title
                    },
                    is_successful=True
                )
                
                return {
                    'success': True,
                    'message': self._get_success_message(language, 'reminder_deleted', {'title': reminder.title}),
                    'data': {'reminder_id': reminder.id}
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': f'Ошибка удаления напоминания: {str(e)}'
            }
    
    def _postpone_reminder(self, reminder_title: str, new_time_str: str, language: str) -> Dict[str, Any]:
        """Откладывает напоминание на новое время"""
        try:
            reminder = Reminder.objects.filter(
                user=self.user,
                title__icontains=reminder_title.strip(),
                is_active=True,
                is_completed=False
            ).first()
            
            if not reminder:
                return {
                    'success': False,
                    'error': self._get_message(language, 'reminder_not_found', {'title': reminder_title})
                }
            
            # Парсим новое время
            new_time = self._parse_reminder_time(new_time_str, language)
            if not new_time:
                return {
                    'success': False,
                    'error': 'Не удалось распознать новое время'
                }
            
            with transaction.atomic():
                old_time = reminder.reminder_time
                reminder.reminder_time = new_time
                reminder.save()
                
                # Логируем команду
                VoiceCommand.objects.create(
                    user=self.user,
                    command_type='postpone_reminder',
                    original_text=f"Отложить напоминание {reminder_title} на {new_time_str}",
                    processed_data={
                        'reminder_id': reminder.id,
                        'title': reminder.title,
                        'old_time': old_time.isoformat(),
                        'new_time': new_time.isoformat()
                    },
                    is_successful=True
                )
                
                return {
                    'success': True,
                    'message': self._get_success_message(language, 'reminder_postponed', {
                        'title': reminder.title,
                        'new_time': new_time.strftime('%d.%m.%Y %H:%M')
                    }),
                    'data': {
                        'reminder_id': reminder.id,
                        'new_time': new_time.isoformat()
                    }
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': f'Ошибка переноса напоминания: {str(e)}'
            }
    
    def _complete_reminder(self, reminder_title: str, language: str) -> Dict[str, Any]:
        """Отмечает напоминание как выполненное"""
        try:
            reminder = Reminder.objects.filter(
                user=self.user,
                title__icontains=reminder_title.strip(),
                is_active=True,
                is_completed=False
            ).first()
            
            if not reminder:
                return {
                    'success': False,
                    'error': self._get_message(language, 'reminder_not_found', {'title': reminder_title})
                }
            
            with transaction.atomic():
                reminder.is_completed = True
                reminder.save()
                
                # Логируем команду
                VoiceCommand.objects.create(
                    user=self.user,
                    command_type='complete_reminder',
                    original_text=f"Выполнено напоминание {reminder_title}",
                    processed_data={
                        'reminder_id': reminder.id,
                        'title': reminder.title
                    },
                    is_successful=True
                )
                
                return {
                    'success': True,
                    'message': self._get_success_message(language, 'reminder_completed', {'title': reminder.title}),
                    'data': {'reminder_id': reminder.id}
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': f'Ошибка выполнения напоминания: {str(e)}'
            }
    
    def _parse_reminder_time(self, time_str: str, language: str) -> Optional[datetime]:
        """Парсит время напоминания из строки"""
        try:
            time_str = time_str.lower().strip()
            now = timezone.now()
            
            # Относительные времена
            if any(word in time_str for word in ['завтра', 'ertaga', 'tomorrow']):
                base_time = now + timedelta(days=1)
                
                # Проверяем, указано ли время
                time_match = re.search(r'(\d{1,2}):(\d{2})', time_str)
                if time_match:
                    hour, minute = int(time_match.group(1)), int(time_match.group(2))
                    return base_time.replace(hour=hour, minute=minute, second=0, microsecond=0)
                else:
                    return base_time.replace(hour=10, minute=0, second=0, microsecond=0)
            
            elif any(word in time_str for word in ['через час', 'bir soatdan keyin', 'in an hour']):
                return now + timedelta(hours=1)
            
            elif any(word in time_str for word in ['через', 'keyin', 'in']):
                # Парсим "через X часов/минут"
                hours_match = re.search(r'(\d+)\s*(?:час|soat|hour)', time_str)
                if hours_match:
                    hours = int(hours_match.group(1))
                    return now + timedelta(hours=hours)
                
                minutes_match = re.search(r'(\d+)\s*(?:минут|daqiqa|minute)', time_str)
                if minutes_match:
                    minutes = int(minutes_match.group(1))
                    return now + timedelta(minutes=minutes)
            
            elif any(word in time_str for word in ['в', 'da', 'at']):
                # Парсим конкретное время "в 15:30"
                time_match = re.search(r'(\d{1,2}):(\d{2})', time_str)
                if time_match:
                    hour, minute = int(time_match.group(1)), int(time_match.group(2))
                    target_time = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
                    
                    # Если время уже прошло сегодня, переносим на завтра
                    if target_time <= now:
                        target_time += timedelta(days=1)
                    
                    return target_time
            
            # Попытка парсинга времени в формате HH:MM
            time_match = re.search(r'(\d{1,2}):(\d{2})', time_str)
            if time_match:
                hour, minute = int(time_match.group(1)), int(time_match.group(2))
                target_time = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
                
                if target_time <= now:
                    target_time += timedelta(days=1)
                
                return target_time
            
            # Попытка парсинга даты
            date_match = re.search(r'(\d{1,2})\.(\d{1,2})(?:\.(\d{2,4}))?', time_str)
            if date_match:
                day, month = int(date_match.group(1)), int(date_match.group(2))
                year = int(date_match.group(3)) if date_match.group(3) else now.year
                
                if year < 100:
                    year += 2000
                
                target_date = datetime(year, month, day, 10, 0, 0)
                return timezone.make_aware(target_date)
            
            return None
            
        except Exception:
            return None
    
    def _get_message(self, language: str, key: str, params: Dict = None) -> str:
        """Возвращает локализованное сообщение"""
        messages = {
            'ru': {
                'no_reminders': 'У вас нет активных напоминаний',
                'reminders_list': 'У вас {count} активных напоминаний' + 
                                (' ({overdue} просроченных)' if params and params.get('overdue', 0) > 0 else ''),
                'reminder_not_found': 'Напоминание "{title}" не найдено',
            },
            'uz': {
                'no_reminders': 'Sizda faol eslatmalar yoq',
                'reminders_list': 'Sizda {count} ta faol eslatma bor',
                'reminder_not_found': '"{title}" eslatmasi topilmadi',
            },
            'en': {
                'no_reminders': 'You have no active reminders',
                'reminders_list': 'You have {count} active reminders',
                'reminder_not_found': 'Reminder "{title}" not found',
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
                'reminder_created': 'Напоминание "{title}" создано на {time}',
                'reminder_created_default': 'Напоминание "{title}" создано на {time} (по умолчанию)',
                'reminder_deleted': 'Напоминание "{title}" удалено',
                'reminder_postponed': 'Напоминание "{title}" перенесено на {new_time}',
                'reminder_completed': '✅ Напоминание "{title}" выполнено',
            },
            'uz': {
                'reminder_created': '"{title}" eslatmasi {time} ga yaratildi',
                'reminder_created_default': '"{title}" eslatmasi {time} ga yaratildi (standart)',
                'reminder_deleted': '"{title}" eslatmasi oʻchirildi',
                'reminder_postponed': '"{title}" eslatmasi {new_time} ga koʻchirildi',
                'reminder_completed': '✅ "{title}" eslatmasi bajarildi',
            },
            'en': {
                'reminder_created': 'Reminder "{title}" created for {time}',
                'reminder_created_default': 'Reminder "{title}" created for {time} (default)',
                'reminder_deleted': 'Reminder "{title}" deleted',
                'reminder_postponed': 'Reminder "{title}" postponed to {new_time}',
                'reminder_completed': '✅ Reminder "{title}" completed',
            }
        }
        
        msg = messages.get(language, messages['ru']).get(key, key)
        if params:
            try:
                return msg.format(**params)
            except KeyError:
                return msg
        return msg 