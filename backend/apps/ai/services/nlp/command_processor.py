"""
NLP сервис для обработки голосовых команд
Распознавание команд на русском, узбекском и английском языках
Интеграция с расширенными исполнителями команд
"""

import re
import logging
from typing import Dict, List, Optional, Tuple, Any
from decimal import Decimal, InvalidOperation

from django.db import transaction
from django.core.exceptions import ValidationError

from apps.categories.models import Category
from apps.transactions.models import Transaction
from apps.goals.models import Goal

# Импорт новых исполнителей команд
from .command_executors import (
    GoalCommandExecutor,
    SourceCommandExecutor,
    SettingsCommandExecutor,
    ReminderCommandExecutor,
    AnalyticsCommandExecutor,
    DebtCommandExecutor,
)
from .extended_commands import ExtendedCommandPatterns


logger = logging.getLogger(__name__)


class VoiceCommandProcessor:
    """Процессор голосовых команд с расширенным функционалом"""
    
    def __init__(self, user):
        """Инициализация процессора с исполнителями команд"""
        self.user = user
        self.goal_executor = GoalCommandExecutor(user)
        self.source_executor = SourceCommandExecutor(user)
        self.settings_executor = SettingsCommandExecutor(user)
        self.reminder_executor = ReminderCommandExecutor(user)
        self.analytics_executor = AnalyticsCommandExecutor(user)
        self.debt_executor = DebtCommandExecutor(user)
        
        # Объединяем все паттерны команд
        self.extended_patterns = ExtendedCommandPatterns.get_all_patterns()
    
    # Паттерны команд для разных языков (базовые команды)
    COMMAND_PATTERNS = {
        'create_category': {
            'ru': [
                r'создай(?:\s+новую)?\s+категорию\s+(.+)',
                r'добавь\s+категорию\s+(.+)',
                r'новая\s+категория\s+(.+)',
                r'создать\s+категорию\s+(.+)',
            ],
            'uz': [
                r'yangi\s+kategoriya\s+(.+)\s+yarat',
                r'(.+)\s+kategoriyasini\s+yarat',
                r'kategoriya\s+(.+)\s+qoʻsh',
                r'(.+)\s+kategoriya\s+qoʻsh',
            ],
            'en': [
                r'create\s+(?:new\s+)?category\s+(.+)',
                r'add\s+category\s+(.+)',
                r'new\s+category\s+(.+)',
                r'make\s+category\s+(.+)',
            ]
        },
        'add_expense': {
            'ru': [
                r'добавь(?:\s+в)?\s+расходы?\s+(.+?)\s+(\d+(?:[\s,]\d{3})*(?:[.,]\d{2})?)\s*(?:сум|руб|₽|тысяч?|рублей?)?',
                r'потратил(?:\s+на)?\s+(.+?)\s+(\d+(?:[\s,]\d{3})*(?:[.,]\d{2})?)\s*(?:сум|руб|₽|тысяч?|рублей?)?',
                r'купил\s+(.+?)\s+(?:за\s+)?(\d+(?:[\s,]\d{3})*(?:[.,]\d{2})?)\s*(?:сум|руб|₽|тысяч?|рублей?)?',
                r'заплатил\s+(?:за\s+)?(.+?)\s+(\d+(?:[\s,]\d{3})*(?:[.,]\d{2})?)\s*(?:сум|руб|₽|тысяч?|рублей?)?',
                r'(.+?)\s+(?:стоил[оа]?|обошел[лс]ся|стоит)\s+(\d+(?:[\s,]\d{3})*(?:[.,]\d{2})?)\s*(?:сум|руб|₽|тысяч?|рублей?)?',
            ],
            'uz': [
                r'(.+?)\s+uchun\s+(\d+(?:[\s,]\d{3})*(?:[.,]\d{2})?)\s*(?:som|ming)?\s+sarfladim',
                r'(.+?)ga\s+(\d+(?:[\s,]\d{3})*(?:[.,]\d{2})?)\s*(?:som|ming)?\s+toʻladim',
                r'(.+?)\s+sotib\s+oldim\s+(\d+(?:[\s,]\d{3})*(?:[.,]\d{2})?)\s*(?:som|ming)?',
                r'xarajat\s+(.+?)\s+(\d+(?:[\s,]\d{3})*(?:[.,]\d{2})?)\s*(?:som|ming)?',
            ],
            'en': [
                r'(?:add\s+expense|spent)\s+(.+?)\s+(\d+(?:[\s,]\d{3})*(?:[.,]\d{2})?)\s*(?:sum|dollars?|usd)?',
                r'bought\s+(.+?)\s+(?:for\s+)?(\d+(?:[\s,]\d{3})*(?:[.,]\d{2})?)\s*(?:sum|dollars?|usd)?',
                r'paid\s+(.+?)\s+(\d+(?:[\s,]\d{3})*(?:[.,]\d{2})?)\s*(?:sum|dollars?|usd)?',
                r'(.+?)\s+cost\s+(\d+(?:[\s,]\d{3})*(?:[.,]\d{2})?)\s*(?:sum|dollars?|usd)?',
            ]
        },
        'show_balance': {
            'ru': [
                r'покажи\s+(?:мой\s+)?баланс',
                r'сколько\s+(?:у\s+меня\s+)?денег',
                r'мой\s+баланс',
                r'показать\s+баланс',
                r'какой\s+(?:у\s+меня\s+)?баланс',
            ],
            'uz': [
                r'balansimni\s+koʻrsat',
                r'mening\s+balansim',
                r'qancha\s+pulim\s+bor',
                r'balans\s+koʻrsat',
            ],
            'en': [
                r'show\s+(?:my\s+)?balance',
                r'what(?:\'s|s)\s+my\s+balance',
                r'how\s+much\s+money',
                r'my\s+balance',
                r'check\s+balance',
            ]
        },
        'delete_category': {
            'ru': [
                r'удали\s+категорию\s+(.+)',
                r'убери\s+категорию\s+(.+)',
                r'удалить\s+категорию\s+(.+)',
                r'категорию\s+(.+)\s+удали',
            ],
            'uz': [
                r'(.+)\s+kategoriyasini\s+oʻchir',
                r'kategoriya\s+(.+)\s+oʻchir',
                r'(.+)\s+kategoriya\s+oʻchir',
            ],
            'en': [
                r'delete\s+category\s+(.+)',
                r'remove\s+category\s+(.+)',
                r'category\s+(.+)\s+delete',
            ]
        },
        'manage_debt': {
            'ru': [
                r'кто\s+(?:мне\s+)?должен',
                r'мои\s+долги',
                r'покажи\s+долги',
                r'кому\s+(?:я\s+)?должен',
                r'(?:долг|долги)\s+(.+?)\s+(\d+(?:[\s,]\d{3})*(?:[.,]\d{2})?)\s*(?:сум|руб|₽|тысяч?|рублей?)?',
            ],
            'uz': [
                r'kim\s+menga\s+qarzdor',
                r'mening\s+qarzlarim',
                r'qarzlarni\s+koʻrsat',
                r'kimga\s+qarzman',
            ],
            'en': [
                r'who\s+owes\s+me',
                r'my\s+debts',
                r'show\s+debts',
                r'who\s+(?:do\s+)?i\s+owe',
            ]
        },
        'show_stats': {
            'ru': [
                r'покажи\s+статистику',
                r'мои\s+расходы',
                r'статистика\s+(?:по\s+)?расходам',
                r'отчет\s+(?:по\s+)?тратам',
                r'анализ\s+расходов',
            ],
            'uz': [
                r'statistikani\s+koʻrsat',
                r'mening\s+xarajatlarim',
                r'xarajatlar\s+statistikasi',
                r'hisobot',
            ],
            'en': [
                r'show\s+(?:me\s+)?stats',
                r'my\s+expenses',
                r'expense\s+statistics',
                r'spending\s+report',
                r'analysis',
            ]
        }
    }
    
    # Числительные для конвертации
    NUMBER_WORDS = {
        'ru': {
            'один': 1, 'два': 2, 'три': 3, 'четыре': 4, 'пять': 5,
            'шесть': 6, 'семь': 7, 'восемь': 8, 'девять': 9, 'десять': 10,
            'тысяча': 1000, 'тысячи': 1000, 'тысяч': 1000,
            'миллион': 1000000, 'миллиона': 1000000, 'миллионов': 1000000
        },
        'uz': {
            'bir': 1, 'ikki': 2, 'uch': 3, 'toʻrt': 4, 'besh': 5,
            'olti': 6, 'yetti': 7, 'sakkiz': 8, 'toʻqqiz': 9, 'oʻn': 10,
            'ming': 1000, 'million': 1000000
        },
        'en': {
            'one': 1, 'two': 2, 'three': 3, 'four': 4, 'five': 5,
            'six': 6, 'seven': 7, 'eight': 8, 'nine': 9, 'ten': 10,
            'thousand': 1000, 'million': 1000000
        }
    }
    
    def parse_command(
        self, 
        text: str, 
        language: str, 
        user=None
    ) -> Optional[Dict[str, Any]]:
        """
        Парсинг голосовой команды из текста
        
        Args:
            text: Распознанный текст
            language: Определенный язык
            user: Пользователь (опционально, используется self.user если не указан)
            
        Returns:
            Dict: Информация о команде или None
        """
        if not text.strip():
            return None
        
        # Используем пользователя из инициализации, если не передан
        if user is None:
            user = self.user
        
        # Нормализуем текст
        normalized_text = self._normalize_command_text(text)
        
        # Сначала проверяем расширенные команды
        extended_result = self._parse_extended_commands(normalized_text, language, user)
        if extended_result:
            return extended_result
        
        # Затем проверяем базовые команды
        # Пробуем все типы команд
        for command_type, language_patterns in self.COMMAND_PATTERNS.items():
            # Проверяем паттерны для определенного языка
            patterns_to_check = []
            
            if language in language_patterns:
                patterns_to_check.extend(language_patterns[language])
            
            # Также проверяем паттерны всех языков (на случай неточного определения языка)
            for lang, patterns in language_patterns.items():
                if lang != language:
                    patterns_to_check.extend(patterns)
            
            for pattern in patterns_to_check:
                match = re.search(pattern, normalized_text, re.IGNORECASE)
                if match:
                    # Извлекаем параметры
                    params = self._extract_command_params(
                        command_type, match, normalized_text, language, user
                    )
                    
                    # Оценка уверенности
                    confidence = self._calculate_command_confidence(
                        command_type, match, normalized_text, language
                    )
                    
                    return {
                        'type': command_type,
                        'params': params,
                        'confidence': confidence,
                        'original_text': text,
                        'matched_pattern': pattern
                    }
        
        return None
    
    def _parse_extended_commands(self, text: str, language: str, user) -> Optional[Dict[str, Any]]:
        """Парсинг расширенных команд"""
        try:
            # Проверяем каждый тип расширенных команд
            for command_type, patterns in self.extended_patterns.items():
                if language in patterns:
                    for pattern in patterns[language]:
                        match = re.search(pattern, text.lower())
                        if match:
                            return {
                                'type': command_type,
                                'text': text,
                                'language': language,
                                'confidence': self._calculate_extended_command_confidence(
                                    command_type, match, text, language
                                ),
                                'params': {
                                    'original_text': text,
                                    'match_groups': match.groups(),
                                    'pattern': pattern
                                }
                            }
            
            return None
            
        except Exception as e:
            logger.error(f"Ошибка парсинга расширенных команд: {e}")
            return None
    
    def _calculate_extended_command_confidence(self, command_type: str, match: re.Match, 
                                             text: str, language: str) -> float:
        """Рассчитывает уверенность для расширенных команд"""
        base_confidence = 0.8
        
        # Учитываем длину совпадения
        match_length = len(match.group(0))
        text_length = len(text)
        coverage = match_length / text_length if text_length > 0 else 0
        
        # Учитываем количество извлеченных параметров
        params_count = len([g for g in match.groups() if g])
        params_bonus = min(params_count * 0.05, 0.15)
        
        # Учитываем специфичность команды
        specificity_bonus = 0.1 if command_type in [
            'create_goal', 'add_income', 'change_currency', 
            'create_reminder', 'time_based_analytics'
        ] else 0.05
        
        final_confidence = min(base_confidence + (coverage * 0.1) + params_bonus + specificity_bonus, 1.0)
        return final_confidence
    
    def _normalize_command_text(self, text: str) -> str:
        """Нормализация текста команды"""
        # Приводим к нижнему регистру
        text = text.lower().strip()
        
        # Убираем лишние пробелы
        text = ' '.join(text.split())
        
        # Заменяем некоторые сокращения
        replacements = {
            'тыс': 'тысяч',
            'т.': 'тысяч',
            'млн': 'миллион',
            'к': 'тысяч',
            'руб': 'рублей',
        }
        
        for old, new in replacements.items():
            text = text.replace(old, new)
        
        return text
    
    def _extract_command_params(
        self, 
        command_type: str, 
        match: re.Match, 
        text: str, 
        language: str,
        user
    ) -> Dict[str, Any]:
        """Извлечение параметров команды"""
        params = {}
        
        if command_type == 'create_category':
            if match.groups():
                params['category_name'] = match.group(1).strip()
        
        elif command_type == 'add_expense':
            if len(match.groups()) >= 2:
                params['description'] = match.group(1).strip()
                amount_str = match.group(2).strip()
                params['amount'] = self._parse_amount(amount_str, language)
                
                # Пытаемся определить категорию
                params['category'] = self._guess_category_from_text(
                    params['description'], user
                )
        
        elif command_type == 'delete_category':
            if match.groups():
                params['category_name'] = match.group(1).strip()
        
        elif command_type == 'manage_debt':
            if len(match.groups()) >= 2:
                params['person'] = match.group(1).strip()
                amount_str = match.group(2).strip()
                params['amount'] = self._parse_amount(amount_str, language)
        
        return params
    
    def _parse_amount(self, amount_str: str, language: str) -> Decimal:
        """Парсинг суммы из текста"""
        try:
            # Убираем лишние символы
            clean_amount = re.sub(r'[^\d.,\s]', '', amount_str)
            clean_amount = clean_amount.replace(' ', '').replace(',', '.')
            
            if not clean_amount:
                return Decimal('0')
            
            # Конвертируем в число
            amount = Decimal(clean_amount)
            
            # Проверяем контекст для умножителей
            original_lower = amount_str.lower()
            
            # Множители
            multipliers = {
                'тысяч': 1000, 'тыс': 1000, 'к': 1000,
                'миллион': 1000000, 'млн': 1000000,
                'ming': 1000, 'million': 1000000,
                'thousand': 1000
            }
            
            for word, multiplier in multipliers.items():
                if word in original_lower:
                    amount *= multiplier
                    break
            
            return amount
            
        except (ValueError, InvalidOperation):
            return Decimal('0')
    
    def _guess_category_from_text(self, description: str, user) -> Optional[str]:
        """Угадывание категории по описанию"""
        try:
            # Используем импорт здесь, чтобы избежать циклических импортов
            from apps.ai.services.nlp.category_matcher import CategoryMatcher
            
            matcher = CategoryMatcher()
            category, confidence = matcher.match_category(description, user)
            
            if category and confidence > 0.5:
                return category.name
                
        except Exception as e:
            logger.warning(f"Could not guess category: {e}")
        
        return None
    
    def _calculate_command_confidence(
        self, 
        command_type: str, 
        match: re.Match, 
        text: str, 
        language: str
    ) -> float:
        """Расчет уверенности в команде"""
        base_confidence = 0.7
        
        # Увеличиваем уверенность для точных совпадений
        if match.group(0) == text:
            base_confidence += 0.2
        
        # Учитываем полноту извлеченных параметров
        if command_type in ['add_expense', 'manage_debt']:
            if len(match.groups()) >= 2:
                base_confidence += 0.1
        elif command_type in ['create_category', 'delete_category']:
            if match.groups() and match.group(1).strip():
                base_confidence += 0.1
        
        # Учитываем язык
        if language in ['ru', 'uz', 'en']:
            base_confidence += 0.05
        
        return min(1.0, base_confidence)
    
    def execute_command(self, voice_command) -> Dict[str, Any]:
        """
        Выполнение голосовой команды
        
        Args:
            voice_command: VoiceCommand объект
            
        Returns:
            Dict: Результат выполнения
        """
        command_type = voice_command.command_type
        params = voice_command.extracted_params
        user = voice_command.user
        original_text = voice_command.original_text
        language = getattr(voice_command, 'language', 'ru')
        
        try:
            # Выполнение расширенных команд
            if command_type in self.extended_patterns:
                return self._execute_extended_command(command_type, original_text, language, user)
            
            # Выполнение базовых команд
            elif command_type == 'create_category':
                return self._execute_create_category(params, user)
            
            elif command_type == 'add_expense':
                return self._execute_add_expense(params, user)
            
            elif command_type == 'show_balance':
                return self._execute_show_balance(user)
            
            elif command_type == 'delete_category':
                return self._execute_delete_category(params, user)
            
            elif command_type == 'manage_debt':
                return self._execute_manage_debt(params, user)
            
            elif command_type == 'show_stats':
                return self._execute_show_stats(user)
            
            else:
                return {'success': False, 'error': 'Unknown command type'}
                
        except Exception as e:
            logger.error(f"Command execution failed: {e}")
            return {'success': False, 'error': str(e)}
    
    def _execute_extended_command(self, command_type: str, text: str, language: str, user) -> Dict[str, Any]:
        """Выполнение расширенных команд через соответствующие исполнители"""
        try:
            # Команды управления целями
            if command_type in ['create_goal', 'manage_goals']:
                return self.goal_executor.execute_command(command_type, text, language)
            
            # Команды управления источниками
            elif command_type in ['create_source', 'manage_sources', 'add_income']:
                return self.source_executor.execute_command(command_type, text, language)
            
            # Команды настроек
            elif command_type in ['change_currency', 'change_language', 'manage_notifications']:
                return self.settings_executor.execute_command(command_type, text, language)
            
            # Команды напоминаний
            elif command_type in ['create_reminder', 'manage_reminders']:
                return self.reminder_executor.execute_command(command_type, text, language)
            
            # Команды аналитики
            elif command_type in ['time_based_analytics', 'category_analytics', 'comparison_analytics']:
                return self.analytics_executor.execute_command(command_type, text, language)
            
            # Команды управления долгами
            elif command_type in ['create_debt', 'manage_debts']:
                return self.debt_executor.execute_command(command_type, text, language)
            
            else:
                return {
                    'success': False,
                    'error': f'Неподдерживаемая расширенная команда: {command_type}'
                }
                
        except Exception as e:
            logger.error(f"Ошибка выполнения расширенной команды {command_type}: {e}")
            return {
                'success': False,
                'error': f'Ошибка выполнения команды: {str(e)}'
            }
    
    @transaction.atomic
    def _execute_create_category(self, params: Dict, user) -> Dict[str, Any]:
        """Создание новой категории"""
        category_name = params.get('category_name')
        if not category_name:
            return {'success': False, 'error': 'Category name not provided'}
        
        # Проверяем, существует ли уже такая категория
        existing = Category.objects.filter(
            user=user, 
            name__iexact=category_name
        ).first()
        
        if existing:
            return {
                'success': False, 
                'error': f'Category "{category_name}" already exists',
                'category_id': existing.id
            }
        
        # Создаем новую категорию
        category = Category.objects.create(
            user=user,
            name=category_name,
            description=f'Создано голосовой командой'
        )
        
        return {
            'success': True,
            'message': f'Category "{category_name}" created successfully',
            'category_id': category.id,
            'category_name': category.name
        }
    
    @transaction.atomic
    def _execute_add_expense(self, params: Dict, user) -> Dict[str, Any]:
        """Добавление расхода"""
        description = params.get('description')
        amount = params.get('amount')
        category_name = params.get('category')
        
        if not description or not amount or amount <= 0:
            return {'success': False, 'error': 'Invalid expense data'}
        
        # Определяем категорию
        category = None
        if category_name:
            category = Category.objects.filter(
                user=user,
                name__icontains=category_name
            ).first()
        
        if not category:
            # Создаем категорию "Прочее" если нет подходящей
            category, created = Category.objects.get_or_create(
                user=user,
                name='Прочее',
                defaults={'description': 'Автоматически созданная категория'}
            )
        
        # Создаем транзакцию
        transaction_obj = Transaction.objects.create(
            user=user,
            category=category,
            amount=-abs(amount),  # Расход - отрицательная сумма
            description=description,
            transaction_type='expense'
        )
        
        return {
            'success': True,
            'message': f'Expense "{description}" ({amount}) added successfully',
            'transaction_id': transaction_obj.id,
            'category': category.name,
            'amount': str(amount)
        }
    
    def _execute_show_balance(self, user) -> Dict[str, Any]:
        """Показать баланс пользователя"""
        try:
            # Подсчитываем баланс по транзакциям
            from django.db.models import Sum
            
            total_balance = Transaction.objects.filter(
                user=user
            ).aggregate(
                total=Sum('amount')
            )['total'] or Decimal('0')
            
            return {
                'success': True,
                'message': f'Your current balance is {total_balance}',
                'balance': str(total_balance)
            }
            
        except Exception as e:
            return {'success': False, 'error': f'Could not calculate balance: {e}'}
    
    @transaction.atomic
    def _execute_delete_category(self, params: Dict, user) -> Dict[str, Any]:
        """Удаление категории"""
        category_name = params.get('category_name')
        if not category_name:
            return {'success': False, 'error': 'Category name not provided'}
        
        # Ищем категорию
        category = Category.objects.filter(
            user=user,
            name__icontains=category_name
        ).first()
        
        if not category:
            return {'success': False, 'error': f'Category "{category_name}" not found'}
        
        # Проверяем, есть ли связанные транзакции
        transaction_count = Transaction.objects.filter(category=category).count()
        
        if transaction_count > 0:
            return {
                'success': False, 
                'error': f'Category "{category_name}" has {transaction_count} transactions and cannot be deleted'
            }
        
        category_name_for_response = category.name
        category.delete()
        
        return {
            'success': True,
            'message': f'Category "{category_name_for_response}" deleted successfully'
        }
    
    def _execute_manage_debt(self, params: Dict, user) -> Dict[str, Any]:
        """Управление долгами"""
        # Это заглушка для будущей функциональности долгов
        return {
            'success': True,
            'message': 'Debt management feature is coming soon',
            'debts': []
        }
    
    def _execute_show_stats(self, user) -> Dict[str, Any]:
        """Показать статистику расходов"""
        try:
            from django.db.models import Sum, Count
            from datetime import datetime, timedelta
            
            # Статистика за последний месяц
            last_month = datetime.now() - timedelta(days=30)
            
            stats = Transaction.objects.filter(
                user=user,
                created_at__gte=last_month,
                transaction_type='expense'
            ).aggregate(
                total_spent=Sum('amount'),
                transaction_count=Count('id')
            )
            
            # Статистика по категориям
            category_stats = Transaction.objects.filter(
                user=user,
                created_at__gte=last_month,
                transaction_type='expense'
            ).values(
                'category__name'
            ).annotate(
                total=Sum('amount'),
                count=Count('id')
            )
            
            return {
                'success': True,
                'message': 'Statistics for the last 30 days',
                'total_spent': str(abs(stats['total_spent'] or 0)),
                'transaction_count': stats['transaction_count'],
                'categories': list(category_stats)
            }
            
        except Exception as e:
            return {'success': False, 'error': f'Could not generate statistics: {e}'}
    
    def get_supported_commands(self, language: str = 'ru') -> List[Dict[str, str]]:
        """
        Возвращает список поддерживаемых команд
        
        Args:
            language: Язык для примеров команд
            
        Returns:
            List[Dict]: Список команд с примерами
        """
        commands = []
        
        for command_type, lang_patterns in self.COMMAND_PATTERNS.items():
            if language in lang_patterns and lang_patterns[language]:
                # Берем первый паттерн как пример
                example_pattern = lang_patterns[language][0]
                # Убираем regex символы для примера
                example = re.sub(r'[().*+?^${}|[\]\\]', '', example_pattern)
                example = example.replace('\\s+', ' ').replace('\\b', '')
                
                commands.append({
                    'type': command_type,
                    'example': example,
                    'description': self._get_command_description(command_type, language)
                })
        
        return commands
    
    def _get_command_description(self, command_type: str, language: str) -> str:
        """Получение описания команды"""
        descriptions = {
            'ru': {
                'create_category': 'Создание новой категории расходов',
                'add_expense': 'Добавление нового расхода',
                'show_balance': 'Показать текущий баланс',
                'delete_category': 'Удаление категории',
                'manage_debt': 'Управление долгами',
                'show_stats': 'Показать статистику расходов'
            },
            'uz': {
                'create_category': 'Yangi xarajat kategoriyasini yaratish',
                'add_expense': 'Yangi xarajat qoʻshish',
                'show_balance': 'Joriy balansni koʻrsatish',
                'delete_category': 'Kategoriyani oʻchirish',
                'manage_debt': 'Qarzlarni boshqarish',
                'show_stats': 'Xarajatlar statistikasini koʻrsatish'
            },
            'en': {
                'create_category': 'Create new expense category',
                'add_expense': 'Add new expense',
                'show_balance': 'Show current balance',
                'delete_category': 'Delete category',
                'manage_debt': 'Manage debts',
                'show_stats': 'Show expense statistics'
            }
        }
        
        return descriptions.get(language, {}).get(command_type, 'Unknown command') 