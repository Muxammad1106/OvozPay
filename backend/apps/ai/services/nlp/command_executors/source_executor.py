"""
Исполнитель голосовых команд для управления источниками доходов
"""

import re
from decimal import Decimal
from typing import Dict, Any, Optional
from django.db import transaction
from django.utils import timezone

from apps.users.models import User
from apps.sources.models import Source
from apps.transactions.models import Transaction
from apps.ai.models import VoiceCommand
from apps.ai.services.nlp.extended_commands import ExtendedCommandPatterns


class SourceCommandExecutor:
    """Исполнитель команд для управления источниками доходов"""
    
    def __init__(self, user: User):
        self.user = user
        self.patterns = ExtendedCommandPatterns.SOURCE_COMMANDS
    
    def execute_command(self, command_type: str, text: str, language: str = 'ru') -> Dict[str, Any]:
        """Выполняет команду управления источниками"""
        try:
            if command_type == 'create_source':
                return self._create_source(text, language)
            elif command_type == 'manage_sources':
                return self._manage_sources(text, language)
            elif command_type == 'add_income':
                return self._add_income(text, language)
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
    
    def _create_source(self, text: str, language: str) -> Dict[str, Any]:
        """Создает новый источник дохода"""
        patterns = self.patterns['create_source'].get(language, [])
        
        for pattern in patterns:
            match = re.search(pattern, text.lower())
            if match:
                source_name = match.group(1).strip()
                
                # Проверяем, не существует ли уже такой источник
                existing_source = Source.objects.filter(
                    user=self.user,
                    name__iexact=source_name,
                    is_active=True
                ).first()
                
                if existing_source:
                    return {
                        'success': False,
                        'error': self._get_message(language, 'source_exists', {'name': source_name})
                    }
                
                try:
                    with transaction.atomic():
                        source = Source.objects.create(
                            user=self.user,
                            name=source_name,
                            is_active=True
                        )
                        
                        # Логируем команду
                        VoiceCommand.objects.create(
                            user=self.user,
                            command_type='create_source',
                            original_text=text,
                            processed_data={
                                'source_id': source.id,
                                'name': source_name
                            },
                            is_successful=True
                        )
                        
                        return {
                            'success': True,
                            'message': self._get_success_message(language, 'source_created', {'name': source_name}),
                            'data': {
                                'source_id': source.id,
                                'name': source.name
                            }
                        }
                        
                except Exception as e:
                    return {
                        'success': False,
                        'error': f'Ошибка создания источника: {str(e)}'
                    }
        
        return {
            'success': False,
            'error': 'Не удалось распознать команду создания источника'
        }
    
    def _manage_sources(self, text: str, language: str) -> Dict[str, Any]:
        """Управляет существующими источниками"""
        
        # Показать все источники
        if any(re.search(pattern, text.lower()) for pattern in [
            r'покажи.*источники', r'мои источники', r'источники доходов',
            r'manbalarni.*koʻrsat', r'daromad manbalari',
            r'show.*sources', r'income sources'
        ]):
            return self._show_sources(language)
        
        # Удалить источник
        for pattern in [
            r'удали источник\s+(.+)',
            r'(.+?)\s+manbani\s+oʻchir',
            r'delete source\s+(.+)',
        ]:
            match = re.search(pattern, text.lower())
            if match:
                source_name = match.group(1)
                return self._delete_source(source_name, language)
        
        # Переименовать источник
        for pattern in [
            r'переименуй источник\s+(.+?)\s+в\s+(.+)',
        ]:
            match = re.search(pattern, text.lower())
            if match:
                old_name, new_name = match.groups()
                return self._rename_source(old_name, new_name, language)
        
        return {
            'success': False,
            'error': 'Не удалось распознать команду управления источниками'
        }
    
    def _add_income(self, text: str, language: str) -> Dict[str, Any]:
        """Добавляет доход от источника"""
        patterns = self.patterns['add_income'].get(language, [])
        
        for pattern in patterns:
            match = re.search(pattern, text.lower())
            if match:
                groups = match.groups()
                
                # Определяем порядок параметров в зависимости от паттерна
                if language == 'ru':
                    if 'добавь доход' in pattern or 'получил' in pattern or 'пришло' in pattern:
                        amount_str, source_name = groups[0], groups[1]
                    else:  # 'доход'
                        amount_str, source_name = groups[0], groups[1]
                elif language == 'uz':
                    if 'dan' in pattern:
                        source_name, amount_str = groups[0], groups[1]
                    else:
                        amount_str, source_name = groups[0], groups[1]
                else:  # English
                    amount_str, source_name = groups[0], groups[1]
                
                # Парсим сумму
                amount = self._parse_amount(amount_str)
                if not amount:
                    return {
                        'success': False,
                        'error': 'Не удалось распознать сумму'
                    }
                
                # Находим или создаем источник
                source = Source.objects.filter(
                    user=self.user,
                    name__icontains=source_name.strip(),
                    is_active=True
                ).first()
                
                if not source:
                    # Создаем новый источник
                    source = Source.objects.create(
                        user=self.user,
                        name=source_name.strip(),
                        is_active=True
                    )
                
                try:
                    with transaction.atomic():
                        # Создаем транзакцию дохода
                        transaction_obj = Transaction.objects.create(
                            user=self.user,
                            type='income',
                            amount=amount,
                            source=source,
                            description=f'Доход от {source.name}',
                            date=timezone.now().date()
                        )
                        
                        # Логируем команду
                        VoiceCommand.objects.create(
                            user=self.user,
                            command_type='add_income',
                            original_text=text,
                            processed_data={
                                'transaction_id': transaction_obj.id,
                                'source_id': source.id,
                                'amount': str(amount),
                                'source_name': source.name
                            },
                            is_successful=True
                        )
                        
                        return {
                            'success': True,
                            'message': self._get_success_message(language, 'income_added', {
                                'amount': amount,
                                'source': source.name
                            }),
                            'data': {
                                'transaction_id': transaction_obj.id,
                                'source_id': source.id,
                                'amount': str(amount),
                                'source_name': source.name
                            }
                        }
                        
                except Exception as e:
                    return {
                        'success': False,
                        'error': f'Ошибка добавления дохода: {str(e)}'
                    }
        
        return {
            'success': False,
            'error': 'Не удалось распознать команду добавления дохода'
        }
    
    def _show_sources(self, language: str) -> Dict[str, Any]:
        """Показывает все источники пользователя"""
        sources = Source.objects.filter(user=self.user, is_active=True).order_by('name')
        
        if not sources.exists():
            return {
                'success': True,
                'message': self._get_message(language, 'no_sources'),
                'data': {'sources': []}
            }
        
        # Получаем статистику по источникам
        sources_data = []
        for source in sources:
            total_income = Transaction.objects.filter(
                user=self.user,
                source=source,
                type='income'
            ).aggregate(total=models.Sum('amount'))['total'] or Decimal('0')
            
            last_income = Transaction.objects.filter(
                user=self.user,
                source=source,
                type='income'
            ).order_by('-date').first()
            
            sources_data.append({
                'id': source.id,
                'name': source.name,
                'total_income': str(total_income),
                'last_income_date': last_income.date.isoformat() if last_income else None,
                'last_income_amount': str(last_income.amount) if last_income else None
            })
        
        return {
            'success': True,
            'message': self._get_message(language, 'sources_list', {'count': len(sources_data)}),
            'data': {'sources': sources_data}
        }
    
    def _delete_source(self, source_name: str, language: str) -> Dict[str, Any]:
        """Удаляет источник"""
        try:
            source = Source.objects.filter(
                user=self.user,
                name__icontains=source_name.strip(),
                is_active=True
            ).first()
            
            if not source:
                return {
                    'success': False,
                    'error': self._get_message(language, 'source_not_found', {'name': source_name})
                }
            
            # Проверяем, есть ли связанные транзакции
            transactions_count = Transaction.objects.filter(source=source).count()
            
            with transaction.atomic():
                source.is_active = False
                source.save()
                
                # Логируем команду
                VoiceCommand.objects.create(
                    user=self.user,
                    command_type='delete_source',
                    original_text=f"Удалить источник {source_name}",
                    processed_data={
                        'source_id': source.id,
                        'source_name': source.name,
                        'transactions_count': transactions_count
                    },
                    is_successful=True
                )
                
                return {
                    'success': True,
                    'message': self._get_success_message(language, 'source_deleted', {
                        'name': source.name,
                        'transactions': transactions_count
                    }),
                    'data': {'source_id': source.id}
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': f'Ошибка удаления источника: {str(e)}'
            }
    
    def _rename_source(self, old_name: str, new_name: str, language: str) -> Dict[str, Any]:
        """Переименовывает источник"""
        try:
            source = Source.objects.filter(
                user=self.user,
                name__icontains=old_name.strip(),
                is_active=True
            ).first()
            
            if not source:
                return {
                    'success': False,
                    'error': self._get_message(language, 'source_not_found', {'name': old_name})
                }
            
            # Проверяем, не существует ли уже источник с новым именем
            existing_source = Source.objects.filter(
                user=self.user,
                name__iexact=new_name.strip(),
                is_active=True
            ).exclude(id=source.id).first()
            
            if existing_source:
                return {
                    'success': False,
                    'error': self._get_message(language, 'source_exists', {'name': new_name})
                }
            
            with transaction.atomic():
                old_source_name = source.name
                source.name = new_name.strip()
                source.save()
                
                # Логируем команду
                VoiceCommand.objects.create(
                    user=self.user,
                    command_type='rename_source',
                    original_text=f"Переименовать источник {old_name} в {new_name}",
                    processed_data={
                        'source_id': source.id,
                        'old_name': old_source_name,
                        'new_name': source.name
                    },
                    is_successful=True
                )
                
                return {
                    'success': True,
                    'message': self._get_success_message(language, 'source_renamed', {
                        'old_name': old_source_name,
                        'new_name': source.name
                    }),
                    'data': {'source_id': source.id, 'new_name': source.name}
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': f'Ошибка переименования источника: {str(e)}'
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
    
    def _get_message(self, language: str, key: str, params: Dict = None) -> str:
        """Возвращает локализованное сообщение"""
        messages = {
            'ru': {
                'no_sources': 'У вас пока нет источников доходов',
                'sources_list': 'У вас {count} источников доходов',
                'source_not_found': 'Источник "{name}" не найден',
                'source_exists': 'Источник "{name}" уже существует',
            },
            'uz': {
                'no_sources': 'Sizda hali daromad manbalari yoq',
                'sources_list': 'Sizda {count} ta daromad manbasi bor',
                'source_not_found': '"{name}" manbasi topilmadi',
                'source_exists': '"{name}" manbasi allaqachon mavjud',
            },
            'en': {
                'no_sources': 'You have no income sources yet',
                'sources_list': 'You have {count} income sources',
                'source_not_found': 'Source "{name}" not found',
                'source_exists': 'Source "{name}" already exists',
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
                'source_created': 'Источник дохода "{name}" создан',
                'source_deleted': 'Источник "{name}" удален' + 
                                (' (было {transactions} транзакций)' if params and params.get('transactions', 0) > 0 else ''),
                'source_renamed': 'Источник "{old_name}" переименован в "{new_name}"',
                'income_added': 'Добавлен доход {amount} от источника "{source}"',
            },
            'uz': {
                'source_created': '"{name}" daromad manbasi yaratildi',
                'source_deleted': '"{name}" manbasi oʻchirildi',
                'source_renamed': '"{old_name}" manbasi "{new_name}" ga oʻzgartirildi',
                'income_added': '"{source}" manbasidan {amount} daromad qoʻshildi',
            },
            'en': {
                'source_created': 'Income source "{name}" created',
                'source_deleted': 'Source "{name}" deleted',
                'source_renamed': 'Source "{old_name}" renamed to "{new_name}"',
                'income_added': 'Added income {amount} from source "{source}"',
            }
        }
        
        msg = messages.get(language, messages['ru']).get(key, key)
        if params:
            try:
                return msg.format(**params)
            except KeyError:
                return msg
        return msg 