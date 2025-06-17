"""
Исполнитель голосовых команд для расширенной аналитики
"""

import re
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, Any, Optional, List
from django.utils import timezone
from django.db.models import Sum, Count, Q
from django.db.models.functions import TruncMonth, TruncWeek

from apps.users.models import User
from apps.transactions.models import Transaction
from apps.categories.models import Category
from apps.ai.models import VoiceCommand
from apps.ai.services.nlp.extended_commands import ExtendedCommandPatterns


class AnalyticsCommandExecutor:
    """Исполнитель команд для расширенной аналитики"""
    
    def __init__(self, user: User):
        self.user = user
        self.patterns = ExtendedCommandPatterns.ANALYTICS_COMMANDS
    
    def execute_command(self, command_type: str, text: str, language: str = 'ru') -> Dict[str, Any]:
        """Выполняет команду аналитики"""
        try:
            if command_type == 'time_based_analytics':
                return self._time_based_analytics(text, language)
            elif command_type == 'category_analytics':
                return self._category_analytics(text, language)
            elif command_type == 'comparison_analytics':
                return self._comparison_analytics(text, language)
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
    
    def _time_based_analytics(self, text: str, language: str) -> Dict[str, Any]:
        """Аналитика по временным периодам"""
        patterns = self.patterns['time_based_analytics'].get(language, [])
        
        for pattern in patterns:
            match = re.search(pattern, text.lower())
            if match:
                groups = match.groups()
                
                # Определяем период и категорию
                if len(groups) >= 2:
                    category_name = groups[0] if groups[0] else None
                    period_str = groups[1] if groups[1] else groups[0]
                elif len(groups) == 1:
                    category_name = None
                    period_str = groups[0]
                else:
                    continue
                
                # Парсим период
                start_date, end_date = self._parse_period(period_str, language)
                if not start_date or not end_date:
                    return {
                        'success': False,
                        'error': f'Не удалось распознать период: {period_str}'
                    }
                
                # Получаем аналитику
                return self._get_period_analytics(start_date, end_date, category_name, language, text)
        
        return {
            'success': False,
            'error': 'Не удалось распознать команду временной аналитики'
        }
    
    def _category_analytics(self, text: str, language: str) -> Dict[str, Any]:
        """Аналитика по категориям"""
        patterns = self.patterns['category_analytics'].get(language, [])
        
        for pattern in patterns:
            match = re.search(pattern, text.lower())
            if match:
                groups = match.groups()
                
                # Показать топ категорий
                if any(word in text.lower() for word in ['топ', 'самые', 'eng', 'most', 'top']):
                    period_str = groups[0] if groups else None
                    return self._get_top_categories(period_str, language, text)
                
                # Аналитика конкретной категории
                if groups:
                    category_name = groups[0]
                    return self._get_category_details(category_name, language, text)
        
        return {
            'success': False,
            'error': 'Не удалось распознать команду аналитики категорий'
        }
    
    def _comparison_analytics(self, text: str, language: str) -> Dict[str, Any]:
        """Сравнительная аналитика"""
        patterns = self.patterns['comparison_analytics'].get(language, [])
        
        for pattern in patterns:
            match = re.search(pattern, text.lower())
            if match:
                groups = match.groups()
                
                # Сравнение двух категорий/периодов
                if len(groups) >= 2:
                    item1, item2 = groups[0], groups[1]
                    return self._compare_items(item1, item2, language, text)
                
                # Тренд/динамика
                elif any(word in text.lower() for word in ['тренд', 'динамика', 'trend', 'dinamika']):
                    category_name = groups[0] if groups else None
                    return self._get_trend_analysis(category_name, language, text)
        
        return {
            'success': False,
            'error': 'Не удалось распознать команду сравнительной аналитики'
        }
    
    def _get_period_analytics(self, start_date: datetime.date, end_date: datetime.date, 
                            category_name: str, language: str, original_text: str) -> Dict[str, Any]:
        """Получает аналитику за период"""
        try:
            # Базовый запрос
            query = Transaction.objects.filter(
                user=self.user,
                date__gte=start_date,
                date__lte=end_date
            )
            
            # Фильтр по категории
            if category_name:
                category = Category.objects.filter(
                    name__icontains=category_name.strip()
                ).first()
                if category:
                    query = query.filter(category=category)
            
            # Получаем статистику
            expenses = query.filter(type='expense').aggregate(
                total=Sum('amount'),
                count=Count('id')
            )
            
            incomes = query.filter(type='income').aggregate(
                total=Sum('amount'),
                count=Count('id')
            )
            
            # Топ категорий за период
            top_categories = Transaction.objects.filter(
                user=self.user,
                date__gte=start_date,
                date__lte=end_date,
                type='expense'
            ).values('category__name').annotate(
                total=Sum('amount'),
                count=Count('id')
            ).order_by('-total')[:5]
            
            # Динамика по дням
            daily_stats = Transaction.objects.filter(
                user=self.user,
                date__gte=start_date,
                date__lte=end_date
            ).values('date', 'type').annotate(
                total=Sum('amount')
            ).order_by('date')
            
            # Логируем команду
            VoiceCommand.objects.create(
                user=self.user,
                command_type='time_based_analytics',
                original_text=original_text,
                processed_data={
                    'start_date': start_date.isoformat(),
                    'end_date': end_date.isoformat(),
                    'category': category_name,
                    'total_expenses': str(expenses['total'] or 0),
                    'total_incomes': str(incomes['total'] or 0)
                },
                is_successful=True
            )
            
            return {
                'success': True,
                'message': self._format_period_message(
                    start_date, end_date, expenses, incomes, category_name, language
                ),
                'data': {
                    'period': {
                        'start_date': start_date.isoformat(),
                        'end_date': end_date.isoformat()
                    },
                    'expenses': {
                        'total': str(expenses['total'] or 0),
                        'count': expenses['count']
                    },
                    'incomes': {
                        'total': str(incomes['total'] or 0),
                        'count': incomes['count']
                    },
                    'balance': str((incomes['total'] or 0) - (expenses['total'] or 0)),
                    'top_categories': list(top_categories),
                    'daily_stats': list(daily_stats)
                }
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f'Ошибка получения аналитики: {str(e)}'
            }
    
    def _get_top_categories(self, period_str: str, language: str, original_text: str) -> Dict[str, Any]:
        """Получает топ категорий"""
        try:
            # Определяем период
            if period_str:
                start_date, end_date = self._parse_period(period_str, language)
            else:
                # По умолчанию - текущий месяц
                now = timezone.now().date()
                start_date = now.replace(day=1)
                end_date = now
            
            # Получаем топ категорий
            top_categories = Transaction.objects.filter(
                user=self.user,
                type='expense',
                date__gte=start_date,
                date__lte=end_date
            ).values('category__name').annotate(
                total=Sum('amount'),
                count=Count('id'),
                avg_amount=Sum('amount') / Count('id')
            ).order_by('-total')[:10]
            
            total_expenses = sum(cat['total'] for cat in top_categories)
            
            # Добавляем процентное соотношение
            for cat in top_categories:
                cat['percentage'] = round((cat['total'] / total_expenses * 100), 1) if total_expenses > 0 else 0
            
            # Логируем команду
            VoiceCommand.objects.create(
                user=self.user,
                command_type='category_analytics',
                original_text=original_text,
                processed_data={
                    'type': 'top_categories',
                    'period': f"{start_date} - {end_date}",
                    'categories_count': len(top_categories),
                    'total_amount': str(total_expenses)
                },
                is_successful=True
            )
            
            return {
                'success': True,
                'message': self._format_top_categories_message(top_categories, start_date, end_date, language),
                'data': {
                    'period': {
                        'start_date': start_date.isoformat(),
                        'end_date': end_date.isoformat()
                    },
                    'categories': list(top_categories),
                    'total_expenses': str(total_expenses)
                }
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f'Ошибка получения топ категорий: {str(e)}'
            }
    
    def _get_category_details(self, category_name: str, language: str, original_text: str) -> Dict[str, Any]:
        """Получает детальную аналитику по категории"""
        try:
            # Находим категорию
            category = Category.objects.filter(
                name__icontains=category_name.strip()
            ).first()
            
            if not category:
                return {
                    'success': False,
                    'error': self._get_message(language, 'category_not_found', {'name': category_name})
                }
            
            # Получаем статистику за разные периоды
            now = timezone.now().date()
            
            periods = {
                'current_month': (now.replace(day=1), now),
                'last_month': self._get_last_month_range(now),
                'current_year': (now.replace(month=1, day=1), now),
                'last_30_days': (now - timedelta(days=30), now),
            }
            
            category_stats = {}
            
            for period_name, (start_date, end_date) in periods.items():
                stats = Transaction.objects.filter(
                    user=self.user,
                    category=category,
                    type='expense',
                    date__gte=start_date,
                    date__lte=end_date
                ).aggregate(
                    total=Sum('amount'),
                    count=Count('id'),
                    avg_amount=Sum('amount') / Count('id')
                )
                
                category_stats[period_name] = {
                    'total': str(stats['total'] or 0),
                    'count': stats['count'],
                    'avg_amount': str(stats['avg_amount'] or 0),
                    'start_date': start_date.isoformat(),
                    'end_date': end_date.isoformat()
                }
            
            # Получаем последние транзакции
            recent_transactions = Transaction.objects.filter(
                user=self.user,
                category=category,
                type='expense'
            ).order_by('-date')[:5].values(
                'amount', 'description', 'date'
            )
            
            # Логируем команду
            VoiceCommand.objects.create(
                user=self.user,
                command_type='category_analytics',
                original_text=original_text,
                processed_data={
                    'type': 'category_details',
                    'category_id': category.id,
                    'category_name': category.name,
                    'current_month_total': category_stats['current_month']['total']
                },
                is_successful=True
            )
            
            return {
                'success': True,
                'message': self._format_category_details_message(category, category_stats, language),
                'data': {
                    'category': {
                        'id': category.id,
                        'name': category.name
                    },
                    'periods': category_stats,
                    'recent_transactions': list(recent_transactions)
                }
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f'Ошибка получения детальной аналитики: {str(e)}'
            }
    
    def _compare_items(self, item1: str, item2: str, language: str, original_text: str) -> Dict[str, Any]:
        """Сравнивает две категории или периоды"""
        try:
            # Пытаемся найти категории
            category1 = Category.objects.filter(name__icontains=item1.strip()).first()
            category2 = Category.objects.filter(name__icontains=item2.strip()).first()
            
            if category1 and category2:
                return self._compare_categories(category1, category2, language, original_text)
            else:
                # Пытаемся парсить как периоды
                period1 = self._parse_period(item1, language)
                period2 = self._parse_period(item2, language)
                
                if period1[0] and period2[0]:
                    return self._compare_periods(period1, period2, language, original_text)
                else:
                    return {
                        'success': False,
                        'error': 'Не удалось распознать элементы для сравнения'
                    }
        
        except Exception as e:
            return {
                'success': False,
                'error': f'Ошибка сравнения: {str(e)}'
            }
    
    def _get_trend_analysis(self, category_name: str, language: str, original_text: str) -> Dict[str, Any]:
        """Получает анализ трендов"""
        try:
            # Базовый запрос
            query = Transaction.objects.filter(
                user=self.user,
                type='expense',
                date__gte=timezone.now().date() - timedelta(days=180)  # Последние 6 месяцев
            )
            
            # Фильтр по категории
            if category_name:
                category = Category.objects.filter(
                    name__icontains=category_name.strip()
                ).first()
                if category:
                    query = query.filter(category=category)
            
            # Группируем по месяцам
            monthly_stats = query.annotate(
                month=TruncMonth('date')
            ).values('month').annotate(
                total=Sum('amount'),
                count=Count('id')
            ).order_by('month')
            
            # Анализируем тренд
            monthly_totals = [float(stat['total']) for stat in monthly_stats]
            
            if len(monthly_totals) >= 2:
                # Простой анализ тренда
                recent_avg = sum(monthly_totals[-2:]) / 2 if len(monthly_totals) >= 2 else monthly_totals[-1]
                older_avg = sum(monthly_totals[:2]) / 2 if len(monthly_totals) >= 2 else monthly_totals[0]
                
                trend = 'растет' if recent_avg > older_avg else 'снижается'
                change_percent = ((recent_avg - older_avg) / older_avg * 100) if older_avg > 0 else 0
            else:
                trend = 'недостаточно данных'
                change_percent = 0
            
            # Логируем команду
            VoiceCommand.objects.create(
                user=self.user,
                command_type='comparison_analytics',
                original_text=original_text,
                processed_data={
                    'type': 'trend_analysis',
                    'category': category_name,
                    'trend': trend,
                    'change_percent': round(change_percent, 1),
                    'months_analyzed': len(monthly_stats)
                },
                is_successful=True
            )
            
            return {
                'success': True,
                'message': self._format_trend_message(category_name, trend, change_percent, language),
                'data': {
                    'category': category_name,
                    'trend': trend,
                    'change_percent': round(change_percent, 1),
                    'monthly_stats': list(monthly_stats),
                    'analysis_period': '6 months'
                }
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f'Ошибка анализа трендов: {str(e)}'
            }
    
    def _parse_period(self, period_str: str, language: str) -> tuple:
        """Парсит период из строки"""
        try:
            period_str = period_str.lower().strip()
            now = timezone.now().date()
            
            # Текущий месяц
            if any(word in period_str for word in ['этот месяц', 'текущий месяц', 'bu oy', 'this month']):
                return now.replace(day=1), now
            
            # Прошлый месяц
            elif any(word in period_str for word in ['прошлый месяц', 'o\'tgan oy', 'last month']):
                return self._get_last_month_range(now)
            
            # Текущий год
            elif any(word in period_str for word in ['этот год', 'текущий год', 'bu yil', 'this year']):
                return now.replace(month=1, day=1), now
            
            # Прошлый год
            elif any(word in period_str for word in ['прошлый год', 'o\'tgan yil', 'last year']):
                last_year = now.year - 1
                return datetime(last_year, 1, 1).date(), datetime(last_year, 12, 31).date()
            
            # Неделя
            elif any(word in period_str for word in ['неделю', 'hafta', 'week']):
                return now - timedelta(days=7), now
            
            # 30 дней
            elif any(word in period_str for word in ['30 дней', '30 kun', '30 days']):
                return now - timedelta(days=30), now
            
            # По умолчанию - текущий месяц
            return now.replace(day=1), now
            
        except Exception:
            return None, None
    
    def _get_last_month_range(self, current_date: datetime.date) -> tuple:
        """Возвращает диапазон прошлого месяца"""
        if current_date.month == 1:
            last_month = 12
            year = current_date.year - 1
        else:
            last_month = current_date.month - 1
            year = current_date.year
        
        start_date = datetime(year, last_month, 1).date()
        
        # Последний день прошлого месяца
        if last_month == 12:
            end_date = datetime(year + 1, 1, 1).date() - timedelta(days=1)
        else:
            end_date = datetime(year, last_month + 1, 1).date() - timedelta(days=1)
        
        return start_date, end_date
    
    def _format_period_message(self, start_date, end_date, expenses, incomes, category_name, language):
        """Форматирует сообщение о периодной аналитике"""
        period_str = f"{start_date.strftime('%d.%m.%Y')} - {end_date.strftime('%d.%m.%Y')}"
        
        if language == 'ru':
            msg = f"Аналитика за период {period_str}"
            if category_name:
                msg += f" по категории '{category_name}'"
            msg += f":\n💸 Расходы: {expenses['total'] or 0}\n💰 Доходы: {incomes['total'] or 0}"
            msg += f"\n📊 Баланс: {(incomes['total'] or 0) - (expenses['total'] or 0)}"
        elif language == 'uz':
            msg = f"{period_str} davr uchun analitika"
            if category_name:
                msg += f" '{category_name}' kategoriyasi bo'yicha"
            msg += f":\n💸 Xarajatlar: {expenses['total'] or 0}\n💰 Daromadlar: {incomes['total'] or 0}"
        else:
            msg = f"Analytics for period {period_str}"
            if category_name:
                msg += f" for category '{category_name}'"
            msg += f":\n💸 Expenses: {expenses['total'] or 0}\n💰 Income: {incomes['total'] or 0}"
        
        return msg
    
    def _format_top_categories_message(self, categories, start_date, end_date, language):
        """Форматирует сообщение о топ категориях"""
        if not categories:
            return self._get_message(language, 'no_expenses_in_period')
        
        if language == 'ru':
            msg = f"🏆 Топ категорий за период {start_date.strftime('%d.%m')} - {end_date.strftime('%d.%m')}:\n"
            for i, cat in enumerate(categories[:5], 1):
                msg += f"{i}. {cat['category__name']}: {cat['total']} ({cat['percentage']}%)\n"
        elif language == 'uz':
            msg = f"🏆 {start_date.strftime('%d.%m')} - {end_date.strftime('%d.%m')} davr uchun top kategoriyalar:\n"
            for i, cat in enumerate(categories[:5], 1):
                msg += f"{i}. {cat['category__name']}: {cat['total']} ({cat['percentage']}%)\n"
        else:
            msg = f"🏆 Top categories for {start_date.strftime('%d.%m')} - {end_date.strftime('%d.%m')}:\n"
            for i, cat in enumerate(categories[:5], 1):
                msg += f"{i}. {cat['category__name']}: {cat['total']} ({cat['percentage']}%)\n"
        
        return msg
    
    def _format_category_details_message(self, category, stats, language):
        """Форматирует сообщение о детальной аналитике категории"""
        if language == 'ru':
            msg = f"📊 Детальная аналитика по категории '{category.name}':\n"
            msg += f"• Текущий месяц: {stats['current_month']['total']} ({stats['current_month']['count']} транзакций)\n"
            msg += f"• Прошлый месяц: {stats['last_month']['total']} ({stats['last_month']['count']} транзакций)\n"
            msg += f"• За год: {stats['current_year']['total']}\n"
        elif language == 'uz':
            msg = f"📊 '{category.name}' kategoriyasi bo'yicha batafsil analitika:\n"
            msg += f"• Joriy oy: {stats['current_month']['total']} ({stats['current_month']['count']} ta tranzaksiya)\n"
            msg += f"• O'tgan oy: {stats['last_month']['total']} ({stats['last_month']['count']} ta tranzaksiya)\n"
        else:
            msg = f"📊 Detailed analytics for category '{category.name}':\n"
            msg += f"• Current month: {stats['current_month']['total']} ({stats['current_month']['count']} transactions)\n"
            msg += f"• Last month: {stats['last_month']['total']} ({stats['last_month']['count']} transactions)\n"
        
        return msg
    
    def _format_trend_message(self, category_name, trend, change_percent, language):
        """Форматирует сообщение о тренде"""
        if language == 'ru':
            msg = f"📈 Анализ трендов"
            if category_name:
                msg += f" по категории '{category_name}'"
            msg += f":\nТренд: {trend}"
            if change_percent != 0:
                msg += f" ({abs(change_percent):.1f}%)"
        elif language == 'uz':
            msg = f"📈 Trend tahlili"
            if category_name:
                msg += f" '{category_name}' kategoriyasi uchun"
            msg += f":\nTrend: {trend}"
        else:
            msg = f"📈 Trend analysis"
            if category_name:
                msg += f" for category '{category_name}'"
            msg += f":\nTrend: {trend}"
        
        return msg
    
    def _get_message(self, language: str, key: str, params: Dict = None) -> str:
        """Возвращает локализованное сообщение"""
        messages = {
            'ru': {
                'category_not_found': 'Категория "{name}" не найдена',
                'no_expenses_in_period': 'Нет расходов за указанный период',
            },
            'uz': {
                'category_not_found': '"{name}" kategoriyasi topilmadi',
                'no_expenses_in_period': 'Belgilangan davr uchun xarajatlar yo\'q',
            },
            'en': {
                'category_not_found': 'Category "{name}" not found',
                'no_expenses_in_period': 'No expenses for the specified period',
            }
        }
        
        msg = messages.get(language, messages['ru']).get(key, key)
        if params:
            try:
                return msg.format(**params)
            except KeyError:
                return msg
        return msg 