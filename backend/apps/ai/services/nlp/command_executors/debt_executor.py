"""
Исполнитель голосовых команд для детального управления долгами
"""

import re
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, Any, Optional
from django.utils import timezone
from django.db import transaction
from django.db.models import Sum, Q

from apps.users.models import User
from apps.transactions.models import DebtTransaction
from apps.ai.models import VoiceCommand
from apps.ai.services.nlp.extended_commands import ExtendedCommandPatterns


class DebtCommandExecutor:
    """Исполнитель команд для детального управления долгами"""
    
    def __init__(self, user: User):
        self.user = user
        self.patterns = ExtendedCommandPatterns.DEBT_COMMANDS
    
    def execute_command(self, command_type: str, text: str, language: str = 'ru') -> Dict[str, Any]:
        """Выполняет команду управления долгами"""
        try:
            if command_type == 'create_debt':
                return self._create_debt(text, language)
            elif command_type == 'manage_debts':
                return self._manage_debts(text, language)
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
    
    def _create_debt(self, text: str, language: str) -> Dict[str, Any]:
        """Создает новый долг"""
        patterns = self.patterns['create_debt'].get(language, [])
        
        for pattern in patterns:
            match = re.search(pattern, text.lower())
            if match:
                groups = match.groups()
                
                if len(groups) >= 2:
                    # Определяем порядок параметров в зависимости от паттерна
                    if 'дал в долг' in pattern or 'одолжил' in pattern or 'lent' in pattern:
                        # Я дал в долг
                        person_name = groups[0].strip()
                        amount_str = groups[1]
                        debt_type = 'lent'  # я дал
                        due_date_str = groups[2] if len(groups) > 2 else None
                    elif 'взял в долг' in pattern or 'занял у' in pattern or 'borrowed' in pattern:
                        # Я взял в долг
                        person_name = groups[0].strip()
                        amount_str = groups[1]
                        debt_type = 'borrowed'  # я взял
                        due_date_str = groups[2] if len(groups) > 2 else None
                    else:
                        # Общий формат: добавь долг [кто] [сумма]
                        person_name = groups[0].strip()
                        amount_str = groups[1]
                        debt_type = 'lent'  # по умолчанию - дал в долг
                        due_date_str = groups[2] if len(groups) > 2 else None
                    
                    # Парсим сумму
                    amount = self._parse_amount(amount_str)
                    if not amount:
                        return {
                            'success': False,
                            'error': 'Не удалось распознать сумму'
                        }
                    
                    # Парсим дату возврата
                    due_date = self._parse_due_date(due_date_str) if due_date_str else None
                    
                    try:
                        with transaction.atomic():
                            debt = DebtTransaction.objects.create(
                                user=self.user,
                                debtor_name=person_name,
                                amount=amount,
                                debt_direction='from_me' if debt_type == 'lent' else 'to_me',
                                due_date=due_date,
                                description=f'Голосовая команда: {text}'
                            )
                            
                            # Логируем команду
                            VoiceCommand.objects.create(
                                user=self.user,
                                command_type='create_debt',
                                original_text=text,
                                processed_data={
                                    'debt_id': debt.id,
                                    'person_name': person_name,
                                    'amount': str(amount),
                                    'debt_type': debt_type,
                                    'due_date': due_date.isoformat() if due_date else None
                                },
                                is_successful=True
                            )
                            
                            return {
                                'success': True,
                                'message': self._get_success_message(language, 'debt_created', {
                                    'type': debt_type,
                                    'person': person_name,
                                    'amount': amount,
                                    'due_date': due_date.strftime('%d.%m.%Y') if due_date else None
                                }),
                                'data': {
                                    'debt_id': debt.id,
                                    'person_name': debt.debtor_name,
                                    'amount': str(debt.amount),
                                    'debt_type': debt.debt_direction,
                                    'due_date': debt.due_date.isoformat() if debt.due_date else None
                                }
                            }
                            
                    except Exception as e:
                        return {
                            'success': False,
                            'error': f'Ошибка создания долга: {str(e)}'
                        }
        
        return {
            'success': False,
            'error': 'Не удалось распознать команду создания долга'
        }
    
    def _manage_debts(self, text: str, language: str) -> Dict[str, Any]:
        """Управляет существующими долгами"""
        
        # Показать кто должен мне
        if any(re.search(pattern, text.lower()) for pattern in [
            r'кто.*должен', r'мне.*должен', r'kim.*qarzdor',
            r'who owes me'
        ]):
            return self._show_debts_to_me(language)
        
        # Показать кому я должен
        elif any(re.search(pattern, text.lower()) for pattern in [
            r'кому.*должен', r'я.*должен', r'мои долги', r'kimga.*qarzman',
            r'who.*i owe', r'my debts'
        ]):
            return self._show_my_debts(language)
        
        # Показать просроченные долги
        elif any(re.search(pattern, text.lower()) for pattern in [
            r'просроченные долги', r'muddati.*o\'tgan', r'overdue debts'
        ]):
            return self._show_overdue_debts(language)
        
        # Частичный возврат долга
        for pattern in [
            r'верни долг\s+(.+?)\s+(?:частично\s+)?(\d+(?:[\s,]\d{3})*(?:[.,]\d{2})?)\s*(?:сум|руб|₽|долларов?)?',
            r'вернул долг\s+(.+)',
            r'(.+?)ga\s+qarzni\s+(?:qisman\s+)?(\d+(?:[\s,]\d{3})*(?:[.,]\d{2})?)\s*(?:som|dollar)?\s+qaytardim',
            r'(?:partially\s+)?(?:paid back|returned)\s+(.+?)\s+(\d+(?:[\s,]\d{3})*(?:[.,]\d{2})?)\s*(?:sum|dollars?)?',
        ]:
            match = re.search(pattern, text.lower())
            if match:
                groups = match.groups()
                if len(groups) >= 2:
                    person_name = groups[0].strip()
                    amount_str = groups[1]
                    return self._partial_debt_payment(person_name, amount_str, language)
                elif len(groups) == 1:
                    # Полный возврат
                    person_name = groups[0].strip()
                    return self._close_debt(person_name, language)
        
        # Закрыть долг
        for pattern in [
            r'закрой долг (?:с|у)\s+(.+)',
            r'(.+?)\s+bilan\s+qarzni\s+yop',
            r'close debt (?:with|to)\s+(.+)',
        ]:
            match = re.search(pattern, text.lower())
            if match:
                person_name = match.group(1).strip()
                return self._close_debt(person_name, language)
        
        return {
            'success': False,
            'error': 'Не удалось распознать команду управления долгами'
        }
    
    def _show_debts_to_me(self, language: str) -> Dict[str, Any]:
        """Показывает кто мне должен"""
        debts = DebtTransaction.objects.filter(
            user=self.user,
            debt_direction='from_me',
            status__in=['open', 'partial']
        ).order_by('due_date')
        
        if not debts.exists():
            return {
                'success': True,
                'message': self._get_message(language, 'no_debts_to_me'),
                'data': {'debts': []}
            }
        
        debts_data = []
        total_amount = Decimal('0')
        
        for debt in debts:
            remaining = debt.amount - debt.paid_amount
            total_amount += remaining
            debts_data.append({
                'id': debt.id,
                'person_name': debt.debtor_name,
                'amount': str(debt.amount),
                'remaining_amount': str(remaining),
                'due_date': debt.due_date.isoformat() if debt.due_date else None,
                'status': debt.status,
                'paid_amount': str(debt.paid_amount)
            })
        
        return {
            'success': True,
            'message': self._get_message(language, 'debts_to_me_list', {'count': len(debts_data), 'total': total_amount}),
            'data': {
                'debts': debts_data,
                'total_amount': str(total_amount)
            }
        }
    
    def _show_my_debts(self, language: str) -> Dict[str, Any]:
        """Показывает кому я должен"""
        try:
            debts = DebtTransaction.objects.filter(
                user=self.user,
                debt_direction='to_me',
                status__in=['open', 'partial']
            ).order_by('due_date')
            
            if not debts.exists():
                return {
                    'success': True,
                    'message': self._get_message(language, 'no_my_debts'),
                    'data': {'debts': []}
                }
            
            debts_data = []
            total_amount = Decimal('0')
            
            for debt in debts:
                remaining = debt.amount - debt.paid_amount
                total_amount += remaining
                debts_data.append({
                    'id': debt.id,
                    'person_name': debt.debtor_name,
                    'amount': str(debt.amount),
                    'remaining_amount': str(remaining),
                    'due_date': debt.due_date.isoformat() if debt.due_date else None,
                    'status': debt.status,
                    'paid_amount': str(debt.paid_amount)
                })
            
            return {
                'success': True,
                'message': self._get_message(language, 'my_debts_list', {'count': len(debts_data), 'total': total_amount}),
                'data': {
                    'debts': debts_data,
                    'total_amount': str(total_amount)
                }
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f'Ошибка получения моих долгов: {str(e)}'
            }
    
    def _show_overdue_debts(self, language: str) -> Dict[str, Any]:
        """Показывает просроченные долги"""
        try:
            current_date = timezone.now().date()
            debts = DebtTransaction.objects.filter(
                user=self.user,
                status='overdue'
            ).order_by('due_date')
            
            if not debts.exists():
                return {
                    'success': True,
                    'message': self._get_message(language, 'no_overdue_debts'),
                    'data': {'debts': []}
                }
            
            debts_data = []
            for debt in debts:
                remaining = debt.amount - debt.paid_amount
                days_overdue = (current_date - debt.due_date.date()).days if debt.due_date else 0
                debts_data.append({
                    'id': debt.id,
                    'person_name': debt.debtor_name,
                    'amount': str(debt.amount),
                    'remaining_amount': str(remaining),
                    'debt_type': debt.debt_direction,
                    'due_date': debt.due_date.isoformat(),
                    'days_overdue': days_overdue,
                    'paid_amount': str(debt.paid_amount)
                })
            
            return {
                'success': True,
                'message': self._get_message(language, 'overdue_debts_list', {'count': len(debts_data)}),
                'data': {'debts': debts_data}
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f'Ошибка получения просроченных долгов: {str(e)}'
            }
    
    def _partial_debt_payment(self, person_name: str, amount_str: str, language: str) -> Dict[str, Any]:
        """Частичный возврат долга"""
        try:
            # Находим долг
            debt = DebtTransaction.objects.filter(
                user=self.user,
                debtor_name__icontains=person_name.strip(),
                status__in=['open', 'partial']
            ).first()
            
            if not debt:
                return {
                    'success': False,
                    'error': self._get_message(language, 'debt_not_found', {'person': person_name})
                }
            
            # Парсим сумму
            amount = self._parse_amount(amount_str)
            if not amount:
                return {
                    'success': False,
                    'error': 'Не удалось распознать сумму'
                }
            
            # Проверяем, что сумма не превышает остаток
            remaining = debt.amount - debt.paid_amount
            if amount > remaining:
                return {
                    'success': False,
                    'error': self._get_message(language, 'payment_exceeds_debt', {
                        'amount': amount,
                        'remaining': remaining
                    })
                }
            
            with transaction.atomic():
                debt.add_payment(amount)
                
                # Логируем команду
                VoiceCommand.objects.create(
                    user=self.user,
                    command_type='partial_debt_payment',
                    original_text=f'{person_name} {amount_str}',
                    processed_data={
                        'debt_id': debt.id,
                        'person_name': debt.debtor_name,
                        'payment_amount': str(amount),
                        'remaining_amount': str(debt.amount - debt.paid_amount),
                        'status': debt.status
                    },
                    is_successful=True
                )
                
                message_key = 'debt_payment_recorded'
                if debt.status == 'closed':
                    message_key = 'debt_fully_paid'
                
                return {
                    'success': True,
                    'message': self._get_success_message(language, message_key, {
                        'person': debt.debtor_name,
                        'amount': amount,
                        'remaining': debt.amount - debt.paid_amount
                    }),
                    'data': {
                        'debt_id': debt.id,
                        'payment_amount': str(amount),
                        'remaining_amount': str(debt.amount - debt.paid_amount),
                        'status': debt.status
                    }
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': f'Ошибка частичного возврата долга: {str(e)}'
            }
    
    def _close_debt(self, person_name: str, language: str) -> Dict[str, Any]:
        """Полностью закрывает долг"""
        try:
            debt = DebtTransaction.objects.filter(
                user=self.user,
                debtor_name__icontains=person_name.strip(),
                status__in=['open', 'partial']
            ).first()
            
            if not debt:
                return {
                    'success': False,
                    'error': self._get_message(language, 'debt_not_found', {'person': person_name})
                }
            
            with transaction.atomic():
                remaining_amount = debt.amount - debt.paid_amount
                debt.close_debt()
                
                # Логируем команду
                VoiceCommand.objects.create(
                    user=self.user,
                    command_type='close_debt',
                    original_text=f"Закрыть долг {person_name}",
                    processed_data={
                        'debt_id': debt.id,
                        'person_name': debt.debtor_name,
                        'closed_amount': str(remaining_amount),
                        'debt_type': debt.debt_direction
                    },
                    is_successful=True
                )
                
                return {
                    'success': True,
                    'message': self._get_success_message(language, 'debt_closed', {
                        'person': debt.debtor_name,
                        'amount': remaining_amount
                    }),
                    'data': {
                        'debt_id': debt.id,
                        'closed_amount': str(remaining_amount)
                    }
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': f'Ошибка закрытия долга: {str(e)}'
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
    
    def _parse_due_date(self, date_str: str) -> Optional[datetime.date]:
        """Парсит дату возврата из строки"""
        if not date_str:
            return None
        
        try:
            date_str = date_str.lower().strip()
            now = timezone.now().date()
            
            # Относительные даты
            if any(word in date_str for word in ['завтра', 'ertaga', 'tomorrow']):
                return now + timedelta(days=1)
            elif any(word in date_str for word in ['неделю', 'hafta', 'week']):
                return now + timedelta(weeks=1)
            elif any(word in date_str for word in ['месяц', 'oy', 'month']):
                return now + timedelta(days=30)
            
            # Попытка парсинга конкретной даты
            date_match = re.search(r'(\d{1,2})\.(\d{1,2})(?:\.(\d{2,4}))?', date_str)
            if date_match:
                day, month = int(date_match.group(1)), int(date_match.group(2))
                year = int(date_match.group(3)) if date_match.group(3) else now.year
                
                if year < 100:
                    year += 2000
                
                return datetime(year, month, day).date()
            
            return None
            
        except Exception:
            return None
    
    def _get_message(self, language: str, key: str, params: Dict = None) -> str:
        """Возвращает локализованное сообщение"""
        messages = {
            'ru': {
                'no_debts_to_me': 'Никто вам не должен',
                'no_my_debts': 'У вас нет долгов',
                'no_overdue_debts': 'Нет просроченных долгов',
                'debt_not_found': 'Долг с "{person}" не найден',
                'debts_to_me_list': 'Вам должны {count} человек на общую сумму {total}' + 
                                  (' ({overdue} просроченных)' if params and params.get('overdue', 0) > 0 else ''),
                'my_debts_list': 'Вы должны {count} человекам на общую сумму {total}' + 
                               (' ({overdue} просроченных)' if params and params.get('overdue', 0) > 0 else ''),
                'overdue_debts_list': 'У вас {count} просроченных долгов',
            },
            'uz': {
                'no_debts_to_me': 'Hech kim sizga qarz emas',
                'no_my_debts': 'Sizda qarzlar yo\'q',
                'no_overdue_debts': 'Muddati o\'tgan qarzlar yo\'q',
                'debt_not_found': '"{person}" bilan qarz topilmadi',
                'debts_to_me_list': 'Sizga {count} kishi {total} summaga qarz',
                'my_debts_list': 'Siz {count} kishiga {total} summaga qarz',
                'overdue_debts_list': 'Sizda {count} ta muddati o\'tgan qarz bor',
            },
            'en': {
                'no_debts_to_me': 'Nobody owes you money',
                'no_my_debts': 'You have no debts',
                'no_overdue_debts': 'No overdue debts',
                'debt_not_found': 'Debt with "{person}" not found',
                'debts_to_me_list': '{count} people owe you {total} in total',
                'my_debts_list': 'You owe {count} people {total} in total',
                'overdue_debts_list': 'You have {count} overdue debts',
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
                'debt_created': 'Долг добавлен: {person} {amount}' + 
                              (' до {due_date}' if params and params.get('due_date') else ''),
                'debt_partially_paid': 'Частичный возврат: {person} вернул {amount}. Осталось: {remaining}',
                'debt_fully_paid': '✅ Долг полностью погашен: {person} вернул {amount}',
                'debt_closed': '✅ Долг с {person} закрыт на сумму {amount}',
            },
            'uz': {
                'debt_created': 'Qarz qo\'shildi: {person} {amount}',
                'debt_partially_paid': 'Qisman qaytarish: {person} {amount} qaytardi. Qoldi: {remaining}',
                'debt_fully_paid': '✅ Qarz to\'liq to\'landi: {person} {amount} qaytardi',
                'debt_closed': '✅ {person} bilan qarz {amount} summaga yopildi',
            },
            'en': {
                'debt_created': 'Debt added: {person} {amount}',
                'debt_partially_paid': 'Partial payment: {person} returned {amount}. Remaining: {remaining}',
                'debt_fully_paid': '✅ Debt fully paid: {person} returned {amount}',
                'debt_closed': '✅ Debt with {person} closed for {amount}',
            }
        }
        
        msg = messages.get(language, messages['ru']).get(key, key)
        if params:
            try:
                return msg.format(**params)
            except KeyError:
                return msg
        return msg 