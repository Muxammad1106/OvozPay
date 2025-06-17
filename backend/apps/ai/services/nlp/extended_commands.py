"""
Расширенные паттерны голосовых команд для полного управления всеми модулями
"""

from typing import Dict, List

class ExtendedCommandPatterns:
    """Расширенные паттерны команд для всех модулей приложения"""
    
    # Управление целями
    GOAL_COMMANDS = {
        'create_goal': {
            'ru': [
                r'создай цель (?:накопить|собрать)\s+(\d+(?:[\s,]\d{3})*(?:[.,]\d{2})?)\s*(?:сум|руб|₽|долларов?)?\s+на\s+(.+?)(?:\s+до\s+(.+))?',
                r'новая цель\s+(.+?)\s+(\d+(?:[\s,]\d{3})*(?:[.,]\d{2})?)\s*(?:сум|руб|₽|долларов?)?(?:\s+до\s+(.+))?',
                r'хочу накопить\s+(\d+(?:[\s,]\d{3})*(?:[.,]\d{2})?)\s*(?:сум|руб|₽|долларов?)?\s+на\s+(.+?)(?:\s+к\s+(.+))?',
                r'поставь цель\s+(.+?)\s+(\d+(?:[\s,]\d{3})*(?:[.,]\d{2})?)\s*(?:сум|руб|₽|долларов?)?',
            ],
            'uz': [
                r'(.+?)\s+uchun\s+(\d+(?:[\s,]\d{3})*(?:[.,]\d{2})?)\s*(?:som|dollar)?\s+maqsad\s+qoʻy',
                r'maqsad\s+yarat\s+(.+?)\s+(\d+(?:[\s,]\d{3})*(?:[.,]\d{2})?)\s*(?:som|dollar)?',
                r'(\d+(?:[\s,]\d{3})*(?:[.,]\d{2})?)\s*(?:som|dollar)?\s+(.+?)\s+uchun\s+jamʻlash',
            ],
            'en': [
                r'create goal (?:to save|for)\s+(\d+(?:[\s,]\d{3})*(?:[.,]\d{2})?)\s*(?:sum|dollars?)?\s+(?:for|to)\s+(.+?)(?:\s+by\s+(.+))?',
                r'set goal\s+(.+?)\s+(\d+(?:[\s,]\d{3})*(?:[.,]\d{2})?)\s*(?:sum|dollars?)?',
                r'save\s+(\d+(?:[\s,]\d{3})*(?:[.,]\d{2})?)\s*(?:sum|dollars?)?\s+for\s+(.+)',
            ]
        },
        'manage_goals': {
            'ru': [
                r'покажи (?:мои\s+)?цели',
                r'добавь\s+(\d+(?:[\s,]\d{3})*(?:[.,]\d{2})?)\s*(?:сум|руб|₽|долларов?)?\s+к цели\s+(.+)',
                r'пополни цель\s+(.+?)\s+на\s+(\d+(?:[\s,]\d{3})*(?:[.,]\d{2})?)\s*(?:сум|руб|₽|долларов?)?',
                r'удали цель\s+(.+)',
                r'закрой цель\s+(.+)',
                r'приостанови цель\s+(.+)',
                r'возобнови цель\s+(.+)',
                r'сколько осталось (?:до цели\s+)?(.+)',
                r'прогресс цели\s+(.+)',
            ],
            'uz': [
                r'maqsadlarimni\s+koʻrsat',
                r'(.+?)\s+maqsadiga\s+(\d+(?:[\s,]\d{3})*(?:[.,]\d{2})?)\s*(?:som|dollar)?\s+qoʻsh',
                r'(.+?)\s+maqsadni\s+oʻchir',
                r'(.+?)\s+maqsad\s+jarayoni',
            ],
            'en': [
                r'show (?:my\s+)?goals',
                r'add\s+(\d+(?:[\s,]\d{3})*(?:[.,]\d{2})?)\s*(?:sum|dollars?)?\s+to goal\s+(.+)',
                r'delete goal\s+(.+)',
                r'goal progress\s+(.+)',
            ]
        }
    }
    
    # Управление источниками доходов
    SOURCE_COMMANDS = {
        'create_source': {
            'ru': [
                r'создай источник (?:дохода\s+)?(.+)',
                r'новый источник\s+(.+)',
                r'добавь источник\s+(.+)',
                r'источник\s+(.+)\s+создай',
            ],
            'uz': [
                r'(.+?)\s+manba\s+yarat',
                r'yangi manba\s+(.+)',
                r'daromad manbasi\s+(.+)',
            ],
            'en': [
                r'create (?:income\s+)?source\s+(.+)',
                r'new source\s+(.+)',
                r'add source\s+(.+)',
            ]
        },
        'manage_sources': {
            'ru': [
                r'покажи (?:мои\s+)?источники (?:доходов?)?',
                r'удали источник\s+(.+)',
                r'переименуй источник\s+(.+?)\s+в\s+(.+)',
                r'источники доходов',
            ],
            'uz': [
                r'manbalarni\s+koʻrsat',
                r'(.+?)\s+manbani\s+oʻchir',
                r'daromad manbalari',
            ],
            'en': [
                r'show (?:my\s+)?(?:income\s+)?sources',
                r'delete source\s+(.+)',
                r'income sources',
            ]
        },
        'add_income': {
            'ru': [
                r'добавь доход\s+(\d+(?:[\s,]\d{3})*(?:[.,]\d{2})?)\s*(?:сум|руб|₽|долларов?)?\s+(?:с|от|из)\s+(.+)',
                r'получил\s+(\d+(?:[\s,]\d{3})*(?:[.,]\d{2})?)\s*(?:сум|руб|₽|долларов?)?\s+(?:с|от|из)\s+(.+)',
                r'доход\s+(\d+(?:[\s,]\d{3})*(?:[.,]\d{2})?)\s*(?:сум|руб|₽|долларов?)?\s+(.+)',
                r'пришло\s+(\d+(?:[\s,]\d{3})*(?:[.,]\d{2})?)\s*(?:сум|руб|₽|долларов?)?\s+(?:с|от)\s+(.+)',
            ],
            'uz': [
                r'(.+?)\s+dan\s+(\d+(?:[\s,]\d{3})*(?:[.,]\d{2})?)\s*(?:som|dollar)?\s+daromad\s+qoʻsh',
                r'(\d+(?:[\s,]\d{3})*(?:[.,]\d{2})?)\s*(?:som|dollar)?\s+(.+?)\s+dan\s+oldim',
                r'daromad\s+(\d+(?:[\s,]\d{3})*(?:[.,]\d{2})?)\s*(?:som|dollar)?\s+(.+)',
            ],
            'en': [
                r'add income\s+(\d+(?:[\s,]\d{3})*(?:[.,]\d{2})?)\s*(?:sum|dollars?)?\s+from\s+(.+)',
                r'received\s+(\d+(?:[\s,]\d{3})*(?:[.,]\d{2})?)\s*(?:sum|dollars?)?\s+from\s+(.+)',
                r'income\s+(\d+(?:[\s,]\d{3})*(?:[.,]\d{2})?)\s*(?:sum|dollars?)?\s+(.+)',
            ]
        }
    }
    
    # Управление настройками
    SETTINGS_COMMANDS = {
        'change_currency': {
            'ru': [
                r'смени валюту на\s+(.+)',
                r'поменяй валюту на\s+(.+)',
                r'валюта\s+(.+)',
                r'установи валюту\s+(.+)',
                r'поставь валюту\s+(.+)',
            ],
            'uz': [
                r'valyutani\s+(.+?)ga\s+oʻzgartir',
                r'(.+?)\s+valyuta\s+qoʻy',
                r'valyuta\s+(.+)',
            ],
            'en': [
                r'change currency to\s+(.+)',
                r'set currency\s+(.+)',
                r'currency\s+(.+)',
            ]
        },
        'change_language': {
            'ru': [
                r'поменяй язык на\s+(.+)',
                r'смени язык на\s+(.+)',
                r'язык\s+(.+)',
                r'переключи на\s+(.+?)\s+язык',
            ],
            'uz': [
                r'tilni\s+(.+?)ga\s+oʻzgartir',
                r'(.+?)\s+tilga\s+oʻt',
                r'til\s+(.+)',
            ],
            'en': [
                r'change language to\s+(.+)',
                r'switch to\s+(.+)',
                r'language\s+(.+)',
            ]
        },
        'manage_notifications': {
            'ru': [
                r'(?:включи|отключи)\s+уведомления\s+(?:о|про)\s+(.+)',
                r'(?:включить|отключить)\s+напоминания\s+(?:о|про)\s+(.+)',
                r'уведомления\s+(.+?)\s+(включи|отключи)',
                r'настрой уведомления',
                r'покажи настройки уведомлений',
            ],
            'uz': [
                r'(.+?)\s+haqida\s+bildirishnomalarni\s+(yoq|yoqish)',
                r'bildirishnomalar\s+sozlamalari',
            ],
            'en': [
                r'(?:enable|disable)\s+notifications?\s+(?:for|about)\s+(.+)',
                r'notification settings',
                r'turn\s+(on|off)\s+(.+?)\s+notifications?',
            ]
        }
    }
    
    # Управление напоминаниями
    REMINDER_COMMANDS = {
        'create_reminder': {
            'ru': [
                r'создай напоминание\s+(.+?)\s+на\s+(.+)',
                r'напомни\s+(.+?)\s+(?:через|в|на)\s+(.+)',
                r'поставь напоминание\s+(.+?)\s+(?:на|в)\s+(.+)',
                r'добавь напоминание\s+(.+)',
                r'не забыть\s+(.+?)\s+(?:на|в)\s+(.+)',
            ],
            'uz': [
                r'(.+?)\s+haqida\s+(.+?)da\s+eslatma\s+qoʻy',
                r'(.+?)\s+ni\s+(.+?)\s+eslatib\s+tur',
                r'eslatma\s+yarat\s+(.+)',
            ],
            'en': [
                r'create reminder\s+(.+?)\s+(?:for|on)\s+(.+)',
                r'remind me\s+(.+?)\s+(?:in|on|at)\s+(.+)',
                r'set reminder\s+(.+)',
            ]
        },
        'manage_reminders': {
            'ru': [
                r'покажи (?:мои\s+)?напоминания',
                r'удали напоминание\s+(.+)',
                r'отложи напоминание\s+(.+?)\s+на\s+(.+)',
                r'выполнено напоминание\s+(.+)',
                r'активные напоминания',
            ],
            'uz': [
                r'eslatmalarimni\s+koʻrsat',
                r'(.+?)\s+eslatmani\s+oʻchir',
                r'faol eslatmalar',
            ],
            'en': [
                r'show (?:my\s+)?reminders',
                r'delete reminder\s+(.+)',
                r'active reminders',
            ]
        }
    }
    
    # Расширенная аналитика
    ANALYTICS_COMMANDS = {
        'time_based_analytics': {
            'ru': [
                r'покажи расходы за\s+(.+)',
                r'сколько потратил (?:на\s+(.+?)\s+)?за\s+(.+)',
                r'расходы (?:по\s+(.+?)\s+)?за\s+(.+)',
                r'доходы за\s+(.+)',
                r'статистика за\s+(.+)',
                r'отчет за\s+(.+)',
                r'траты (?:на\s+(.+?)\s+)?в\s+(.+)',
                r'анализ расходов за\s+(.+)',
            ],
            'uz': [
                r'(.+?)\s+davridagi\s+xarajatlarni\s+koʻrsat',
                r'(.+?)\s+uchun\s+qancha\s+sarfladim',
                r'(.+?)\s+statistikasi',
                r'(.+?)\s+hisoboti',
            ],
            'en': [
                r'show expenses for\s+(.+)',
                r'how much (?:did I spend|spent)\s+(?:on\s+(.+?)\s+)?(?:in|for|during)\s+(.+)',
                r'expenses for\s+(.+)',
                r'report for\s+(.+)',
                r'analytics for\s+(.+)',
            ]
        },
        'category_analytics': {
            'ru': [
                r'статистика по категории\s+(.+)',
                r'расходы по\s+(.+)',
                r'сколько трачу на\s+(.+)',
                r'анализ категории\s+(.+)',
                r'топ категорий (?:по\s+(.+))?',
                r'самые затратные категории',
            ],
            'uz': [
                r'(.+?)\s+kategoriya\s+statistikasi',
                r'(.+?)ga\s+qancha\s+sarflayapman',
                r'eng\s+koʻp\s+sarflanadigan\s+kategoriyalar',
            ],
            'en': [
                r'category statistics\s+(.+)',
                r'expenses (?:for|on)\s+(.+)',
                r'how much (?:do I spend|am I spending)\s+on\s+(.+)',
                r'top categories',
                r'most expensive categories',
            ]
        },
        'comparison_analytics': {
            'ru': [
                r'сравни расходы\s+(.+?)\s+и\s+(.+)',
                r'что дороже\s+(.+?)\s+или\s+(.+)',
                r'сравнение (?:за\s+)?(.+?)\s+(?:и|с)\s+(.+)',
                r'динамика расходов',
                r'тренд (?:по\s+)?(.+)',
            ],
            'uz': [
                r'(.+?)\s+va\s+(.+?)\s+xarajatlarni\s+solishtir',
                r'xarajatlar\s+dinamikasi',
            ],
            'en': [
                r'compare expenses\s+(.+?)\s+(?:and|with)\s+(.+)',
                r'what(?:\'s| is)\s+more expensive\s+(.+?)\s+or\s+(.+)',
                r'expense trend',
            ]
        }
    }
    
    # Детальное управление долгами
    DEBT_COMMANDS = {
        'create_debt': {
            'ru': [
                r'добавь долг\s+(.+?)\s+(\d+(?:[\s,]\d{3})*(?:[.,]\d{2})?)\s*(?:сум|руб|₽|долларов?)?\s+до\s+(.+)',
                r'дал в долг\s+(.+?)\s+(\d+(?:[\s,]\d{3})*(?:[.,]\d{2})?)\s*(?:сум|руб|₽|долларов?)?(?:\s+до\s+(.+))?',
                r'взял в долг\s+у\s+(.+?)\s+(\d+(?:[\s,]\d{3})*(?:[.,]\d{2})?)\s*(?:сум|руб|₽|долларов?)?(?:\s+до\s+(.+))?',
                r'одолжил\s+(.+?)\s+(\d+(?:[\s,]\d{3})*(?:[.,]\d{2})?)\s*(?:сум|руб|₽|долларов?)?',
                r'занял у\s+(.+?)\s+(\d+(?:[\s,]\d{3})*(?:[.,]\d{2})?)\s*(?:сум|руб|₽|долларов?)?',
            ],
            'uz': [
                r'(.+?)ga\s+(\d+(?:[\s,]\d{3})*(?:[.,]\d{2})?)\s*(?:som|dollar)?\s+qarz\s+berdim',
                r'(.+?)dan\s+(\d+(?:[\s,]\d{3})*(?:[.,]\d{2})?)\s*(?:som|dollar)?\s+qarz\s+oldim',
                r'qarz\s+(.+?)\s+(\d+(?:[\s,]\d{3})*(?:[.,]\d{2})?)\s*(?:som|dollar)?',
            ],
            'en': [
                r'lent\s+(.+?)\s+(\d+(?:[\s,]\d{3})*(?:[.,]\d{2})?)\s*(?:sum|dollars?)?(?:\s+until\s+(.+))?',
                r'borrowed\s+(\d+(?:[\s,]\d{3})*(?:[.,]\d{2})?)\s*(?:sum|dollars?)?\s+from\s+(.+?)(?:\s+until\s+(.+))?',
                r'add debt\s+(.+?)\s+(\d+(?:[\s,]\d{3})*(?:[.,]\d{2})?)\s*(?:sum|dollars?)?',
            ]
        },
        'manage_debts': {
            'ru': [
                r'покажи (?:кто|что)\s+(?:мне\s+)?должен',
                r'кому (?:я\s+)?должен',
                r'мои долги',
                r'верни долг\s+(.+?)\s+(?:частично\s+)?(\d+(?:[\s,]\d{3})*(?:[.,]\d{2})?)\s*(?:сум|руб|₽|долларов?)?',
                r'вернул долг\s+(.+)',
                r'закрой долг (?:с|у)\s+(.+)',
                r'просроченные долги',
                r'долг\s+(.+?)\s+погашен',
            ],
            'uz': [
                r'kim\s+menga\s+qarzdor',
                r'kimga\s+qarzman',
                r'mening\s+qarzlarim',
                r'(.+?)ga\s+qarzni\s+(?:qisman\s+)?(\d+(?:[\s,]\d{3})*(?:[.,]\d{2})?)\s*(?:som|dollar)?\s+qaytardim',
                r'(.+?)\s+bilan\s+qarzni\s+yop',
                r'muddati\s+oʻtgan\s+qarzlar',
            ],
            'en': [
                r'who owes me',
                r'who (?:do\s+)?i owe',
                r'my debts',
                r'(?:partially\s+)?(?:paid back|returned)\s+(.+?)\s+(\d+(?:[\s,]\d{3})*(?:[.,]\d{2})?)\s*(?:sum|dollars?)?',
                r'close debt (?:with|to)\s+(.+)',
                r'overdue debts',
            ]
        }
    }
    
    @classmethod
    def get_all_patterns(cls) -> Dict[str, Dict]:
        """Возвращает все паттерны команд"""
        return {
            **cls.GOAL_COMMANDS,
            **cls.SOURCE_COMMANDS,
            **cls.SETTINGS_COMMANDS,
            **cls.REMINDER_COMMANDS,
            **cls.ANALYTICS_COMMANDS,
            **cls.DEBT_COMMANDS,
        }
    
    @classmethod
    def get_command_types(cls) -> List[str]:
        """Возвращает список всех типов команд"""
        return list(cls.get_all_patterns().keys()) 