# Переход на модульную структуру
from .models.transaction_models import Transaction, DebtTransaction

# Для обратной совместимости - алиас старой модели Debt
Debt = DebtTransaction

__all__ = ['Transaction', 'DebtTransaction', 'Debt']
