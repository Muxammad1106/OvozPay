"""
Исполнитель голосовых команд для управления целями
"""

import re
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, Any, Optional, List
from django.utils import timezone
from django.db import transaction

from apps.users.models import User
from apps.goals.models import Goal
from apps.goals.services import GoalService
from apps.ai.models import VoiceCommand
from apps.ai.services.nlp.extended_commands import ExtendedCommandPatterns


class GoalCommandExecutor:
    """Исполнитель команд для управления целями"""
    
    def __init__(self, user: User):
        self.user = user
        self.goal_service = GoalService()
        self.patterns = ExtendedCommandPatterns.GOAL_COMMANDS
    
    def execute_command(self, command_type: str, text: str, language: str = 'ru') -> Dict[str, Any]:
        """Выполняет команду управления целями"""
        try:
            if command_type == 'create_goal':
                return self._create_goal(text, language)
            elif command_type == 'manage_goals':
                return self._manage_goals(text, language)
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
    
    def _create_goal(self, text: str, language: str) -> Dict[str, Any]:
        """Создает новую цель"""
        patterns = self.patterns['create_goal'].get(language, [])
        
        for pattern in patterns:
            match = re.search(pattern, text.lower())
            if match:
                groups = match.groups()
                
                # Извлекаем сумму и название
                if len(groups) >= 2:
                    amount_str = groups[0] if groups[0].replace(' ', '').replace(',', '').replace('.', '').isdigit() else groups[1]
                    name = groups[1] if groups[0].replace(' ', '').replace(',', '').replace('.', '').isdigit() else groups[0]
                    deadline_str = groups[2] if len(groups) > 2 else None
                    
                    # Парсим сумму
                    amount = self._parse_amount(amount_str)
                    if not amount:
                        return {
                            'success': False,
                            'error': 'Не удалось распознать сумму'
                        }
                    
                    # Парсим дедлайн
                    deadline = self._parse_deadline(deadline_str) if deadline_str else None
                    
                    # Создаем цель
                    try:
                        with transaction.atomic():
                            goal = Goal.objects.create(
                                user=self.user,
                                name=name.strip(),
                                target_amount=amount,
                                current_amount=Decimal('0.00'),
                                deadline=deadline,
                                is_active=True
                            )
                            
                            # Логируем команду
                            VoiceCommand.objects.create(
                                user=self.user,
                                command_type='create_goal',
                                original_text=text,
                                processed_data={
                                    'goal_id': goal.id,
                                    'name': name,
                                    'amount': str(amount),
                                    'deadline': deadline.isoformat() if deadline else None
                                },
                                is_successful=True
                            )
                            
                            return {
                                'success': True,
                                'message': self._get_success_message(language, 'goal_created', {
                                    'name': name,
                                    'amount': amount,
                                    'deadline': deadline
                                }),
                                'data': {
                                    'goal_id': goal.id,
                                    'name': goal.name,
                                    'target_amount': str(goal.target_amount),
                                    'deadline': goal.deadline.isoformat() if goal.deadline else None
                                }
                            }
                    except Exception as e:
                        return {
                            'success': False,
                            'error': f'Ошибка создания цели: {str(e)}'
                        }
        
        return {
            'success': False,
            'error': 'Не удалось распознать команду создания цели'
        }
    
    def _manage_goals(self, text: str, language: str) -> Dict[str, Any]:
        """Управляет существующими целями"""
        patterns = self.patterns['manage_goals'].get(language, [])
        
        # Показать все цели
        if any(re.search(pattern, text.lower()) for pattern in [
            r'покажи.*цели', r'мои цели', r'список целей',
            r'maqsadlarimni.*koʻrsat', r'show.*goals'
        ]):
            return self._show_goals(language)
        
        # Добавить к цели
        for pattern in [
            r'добавь\s+(\d+(?:[\s,]\d{3})*(?:[.,]\d{2})?)\s*(?:сум|руб|₽|долларов?)?\s+к цели\s+(.+)',
            r'пополни цель\s+(.+?)\s+на\s+(\d+(?:[\s,]\d{3})*(?:[.,]\d{2})?)\s*(?:сум|руб|₽|долларов?)?',
        ]:
            match = re.search(pattern, text.lower())
            if match:
                groups = match.groups()
                if len(groups) >= 2:
                    if 'пополни' in pattern:
                        goal_name, amount_str = groups[0], groups[1]
                    else:
                        amount_str, goal_name = groups[0], groups[1]
                    
                    return self._add_to_goal(goal_name, amount_str, language)
        
        # Удалить цель
        for pattern in [
            r'удали цель\s+(.+)',
            r'закрой цель\s+(.+)',
            r'(.+?)\s+maqsadni\s+oʻchir',
            r'delete goal\s+(.+)',
        ]:
            match = re.search(pattern, text.lower())
            if match:
                goal_name = match.group(1)
                return self._delete_goal(goal_name, language)
        
        # Прогресс цели
        for pattern in [
            r'сколько осталось.*?(.+)',
            r'прогресс цели\s+(.+)',
            r'(.+?)\s+maqsad\s+jarayoni',
            r'goal progress\s+(.+)',
        ]:
            match = re.search(pattern, text.lower())
            if match:
                goal_name = match.group(1)
                return self._show_goal_progress(goal_name, language)
        
        return {
            'success': False,
            'error': 'Не удалось распознать команду управления целями'
        }
    
    def _show_goals(self, language: str) -> Dict[str, Any]:
        """Показывает все цели пользователя"""
        goals = Goal.objects.filter(user=self.user, is_active=True).order_by('-created_at')
        
        if not goals.exists():
            return {
                'success': True,
                'message': self._get_message(language, 'no_goals'),
                'data': {'goals': []}
            }
        
        goals_data = []
        for goal in goals:
            progress_percent = (goal.current_amount / goal.target_amount * 100) if goal.target_amount > 0 else 0
            remaining = goal.target_amount - goal.current_amount
            
            goals_data.append({
                'id': goal.id,
                'name': goal.name,
                'target_amount': str(goal.target_amount),
                'current_amount': str(goal.current_amount),
                'remaining': str(remaining),
                'progress_percent': round(progress_percent, 2),
                'deadline': goal.deadline.isoformat() if goal.deadline else None,
                'days_left': (goal.deadline - timezone.now().date()).days if goal.deadline else None
            })
        
        return {
            'success': True,
            'message': self._get_message(language, 'goals_list', {'count': len(goals_data)}),
            'data': {'goals': goals_data}
        }
    
    def _add_to_goal(self, goal_name: str, amount_str: str, language: str) -> Dict[str, Any]:
        """Добавляет сумму к цели"""
        try:
            # Находим цель
            goal = Goal.objects.filter(
                user=self.user,
                name__icontains=goal_name.strip(),
                is_active=True
            ).first()
            
            if not goal:
                return {
                    'success': False,
                    'error': self._get_message(language, 'goal_not_found', {'name': goal_name})
                }
            
            # Парсим сумму
            amount = self._parse_amount(amount_str)
            if not amount:
                return {
                    'success': False,
                    'error': 'Не удалось распознать сумму'
                }
            
            # Обновляем цель
            with transaction.atomic():
                goal.current_amount += amount
                goal.save()
                
                # Проверяем достижение цели
                is_achieved = goal.current_amount >= goal.target_amount
                
                # Логируем команду
                VoiceCommand.objects.create(
                    user=self.user,
                    command_type='add_to_goal',
                    original_text=f"Добавить {amount} к цели {goal_name}",
                    processed_data={
                        'goal_id': goal.id,
                        'amount_added': str(amount),
                        'new_total': str(goal.current_amount),
                        'is_achieved': is_achieved
                    },
                    is_successful=True
                )
                
                message_key = 'goal_achieved' if is_achieved else 'amount_added_to_goal'
                return {
                    'success': True,
                    'message': self._get_success_message(language, message_key, {
                        'name': goal.name,
                        'amount': amount,
                        'current': goal.current_amount,
                        'target': goal.target_amount
                    }),
                    'data': {
                        'goal_id': goal.id,
                        'current_amount': str(goal.current_amount),
                        'target_amount': str(goal.target_amount),
                        'is_achieved': is_achieved
                    }
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': f'Ошибка обновления цели: {str(e)}'
            }
    
    def _delete_goal(self, goal_name: str, language: str) -> Dict[str, Any]:
        """Удаляет цель"""
        try:
            goal = Goal.objects.filter(
                user=self.user,
                name__icontains=goal_name.strip(),
                is_active=True
            ).first()
            
            if not goal:
                return {
                    'success': False,
                    'error': self._get_message(language, 'goal_not_found', {'name': goal_name})
                }
            
            with transaction.atomic():
                goal.is_active = False
                goal.save()
                
                # Логируем команду
                VoiceCommand.objects.create(
                    user=self.user,
                    command_type='delete_goal',
                    original_text=f"Удалить цель {goal_name}",
                    processed_data={'goal_id': goal.id, 'goal_name': goal.name},
                    is_successful=True
                )
                
                return {
                    'success': True,
                    'message': self._get_success_message(language, 'goal_deleted', {'name': goal.name}),
                    'data': {'goal_id': goal.id}
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': f'Ошибка удаления цели: {str(e)}'
            }
    
    def _show_goal_progress(self, goal_name: str, language: str) -> Dict[str, Any]:
        """Показывает прогресс цели"""
        try:
            goal = Goal.objects.filter(
                user=self.user,
                name__icontains=goal_name.strip(),
                is_active=True
            ).first()
            
            if not goal:
                return {
                    'success': False,
                    'error': self._get_message(language, 'goal_not_found', {'name': goal_name})
                }
            
            progress_percent = (goal.current_amount / goal.target_amount * 100) if goal.target_amount > 0 else 0
            remaining = goal.target_amount - goal.current_amount
            days_left = (goal.deadline - timezone.now().date()).days if goal.deadline else None
            
            return {
                'success': True,
                'message': self._get_message(language, 'goal_progress', {
                    'name': goal.name,
                    'current': goal.current_amount,
                    'target': goal.target_amount,
                    'remaining': remaining,
                    'percent': round(progress_percent, 1),
                    'days_left': days_left
                }),
                'data': {
                    'goal_id': goal.id,
                    'name': goal.name,
                    'current_amount': str(goal.current_amount),
                    'target_amount': str(goal.target_amount),
                    'remaining': str(remaining),
                    'progress_percent': round(progress_percent, 2),
                    'days_left': days_left,
                    'is_achieved': goal.current_amount >= goal.target_amount
                }
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f'Ошибка получения прогресса цели: {str(e)}'
            }
    
    def _parse_amount(self, amount_str: str) -> Optional[Decimal]:
        """Парсит сумму из строки"""
        try:
            # Убираем пробелы, запятые как разделители тысяч
            clean_amount = amount_str.replace(' ', '').replace(',', '')
            # Заменяем точку на запятую для десятичных
            if '.' in clean_amount and len(clean_amount.split('.')[-1]) <= 2:
                clean_amount = clean_amount.replace('.', ',')
            
            # Убираем валютные символы
            clean_amount = re.sub(r'[^\d,]', '', clean_amount)
            clean_amount = clean_amount.replace(',', '.')
            
            return Decimal(clean_amount)
        except (ValueError, TypeError):
            return None
    
    def _parse_deadline(self, deadline_str: str) -> Optional[datetime.date]:
        """Парсит дедлайн из строки"""
        if not deadline_str:
            return None
        
        try:
            deadline_str = deadline_str.lower().strip()
            now = timezone.now().date()
            
            # Относительные даты
            if any(word in deadline_str for word in ['завтра', 'ertaga', 'tomorrow']):
                return now + timedelta(days=1)
            elif any(word in deadline_str for word in ['неделю', 'hafta', 'week']):
                return now + timedelta(weeks=1)
            elif any(word in deadline_str for word in ['месяц', 'oy', 'month']):
                return now + timedelta(days=30)
            elif any(word in deadline_str for word in ['год', 'yil', 'year']):
                return now + timedelta(days=365)
            
            # Попытка парсинга конкретной даты
            # Можно добавить более сложный парсинг дат
            return None
            
        except Exception:
            return None
    
    def _get_message(self, language: str, key: str, params: Dict = None) -> str:
        """Возвращает локализованное сообщение"""
        messages = {
            'ru': {
                'no_goals': 'У вас пока нет активных целей',
                'goals_list': 'У вас {count} активных целей',
                'goal_not_found': 'Цель "{name}" не найдена',
                'goal_progress': 'Цель "{name}": {current} из {target} ({percent}%). Осталось: {remaining}' + 
                               ('. Дней до дедлайна: {days_left}' if params and params.get('days_left') else ''),
            },
            'uz': {
                'no_goals': 'Sizda hali faol maqsadlar yoq',
                'goals_list': 'Sizda {count} ta faol maqsad bor',
                'goal_not_found': '"{name}" maqsadi topilmadi',
                'goal_progress': '"{name}" maqsadi: {current} / {target} ({percent}%). Qoldi: {remaining}',
            },
            'en': {
                'no_goals': 'You have no active goals yet',
                'goals_list': 'You have {count} active goals',
                'goal_not_found': 'Goal "{name}" not found',
                'goal_progress': 'Goal "{name}": {current} of {target} ({percent}%). Remaining: {remaining}',
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
                'goal_created': 'Цель "{name}" создана на сумму {amount}' + 
                              (' до {deadline}' if params and params.get('deadline') else ''),
                'amount_added_to_goal': 'Добавлено {amount} к цели "{name}". Текущий прогресс: {current} из {target}',
                'goal_achieved': '🎉 Поздравляем! Цель "{name}" достигнута!',
                'goal_deleted': 'Цель "{name}" удалена',
            },
            'uz': {
                'goal_created': '"{name}" maqsadi {amount} summaga yaratildi',
                'amount_added_to_goal': '"{name}" maqsadiga {amount} qoʻshildi. Hozirgi holat: {current} / {target}',
                'goal_achieved': '🎉 Tabriklaymiz! "{name}" maqsadi bajarildi!',
                'goal_deleted': '"{name}" maqsadi oʻchirildi',
            },
            'en': {
                'goal_created': 'Goal "{name}" created for {amount}',
                'amount_added_to_goal': 'Added {amount} to goal "{name}". Current progress: {current} of {target}',
                'goal_achieved': '🎉 Congratulations! Goal "{name}" achieved!',
                'goal_deleted': 'Goal "{name}" deleted',
            }
        }
        
        msg = messages.get(language, messages['ru']).get(key, key)
        if params:
            try:
                return msg.format(**params)
            except KeyError:
                return msg
        return msg 