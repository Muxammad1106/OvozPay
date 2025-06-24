"""
Text Processing Module
Модуль для обработки естественного языка и извлечения финансовых данных
"""

from .nlp_service import NLPService, nlp_service, parse_financial_text

__all__ = [
    'NLPService',
    'nlp_service',
    'parse_financial_text'
] 