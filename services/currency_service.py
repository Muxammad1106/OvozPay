"""
CurrencyService - Работа с курсами валют
Получает курсы от ЦБ Узбекистана с кэшированием
"""

import asyncio
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
from decimal import Decimal
import httpx
from django.core.cache import cache
from django.conf import settings

logger = logging.getLogger(__name__)


class CurrencyService:
    """Сервис для работы с курсами валют"""
    
    def __init__(self):
        self.cbu_api_url = getattr(
            settings, 
            'CBU_API_URL', 
            'https://cbu.uz/uz/arkhiv-kursov-valyut/json/'
        )
        self.cache_timeout = getattr(settings, 'CURRENCY_CACHE_TIMEOUT', 3600)  # 1 час
        self.supported_currencies = ['UZS', 'USD', 'EUR', 'RUB']
        self.base_currency = 'UZS'  # Узбекский сум как базовая валюта
    
    async def get_exchange_rates(self, force_refresh: bool = False) -> Optional[Dict[str, float]]:
        """
        Получает актуальные курсы валют от ЦБ Узбекистана
        
        Args:
            force_refresh: Принудительно обновить кэш
            
        Returns:
            Словарь с курсами валют к UZS или None при ошибке
        """
        cache_key = 'ovozpay_currency_rates'
        
        # Проверяем кэш (если не принудительное обновление)
        if not force_refresh:
            cached_rates = cache.get(cache_key)
            if cached_rates:
                logger.debug("Курсы валют получены из кэша")
                return cached_rates
        
        try:
            logger.info("Запрашиваем актуальные курсы валют от ЦБ Узбекистана")
            
            rates = await self._fetch_rates_from_cbu()
            
            if rates:
                # Сохраняем в кэш
                cache.set(cache_key, rates, self.cache_timeout)
                logger.info(f"Курсы валют обновлены и сохранены в кэш: {rates}")
                return rates
            else:
                # Если не удалось получить новые курсы, пытаемся вернуть кэш
                cached_rates = cache.get(cache_key)
                if cached_rates:
                    logger.warning("Используем устаревшие курсы из кэша")
                    return cached_rates
                
                # Если и кэша нет, возвращаем курсы по умолчанию
                default_rates = self._get_default_rates()
                logger.warning(f"Используем курсы по умолчанию: {default_rates}")
                return default_rates
                
        except Exception as e:
            logger.error(f"Ошибка получения курсов валют: {e}")
            
            # Пытаемся вернуть кэшированные курсы
            cached_rates = cache.get(cache_key)
            if cached_rates:
                return cached_rates
            
            # В крайнем случае возвращаем курсы по умолчанию
            return self._get_default_rates()
    
    async def _fetch_rates_from_cbu(self) -> Optional[Dict[str, float]]:
        """Запрашивает курсы от API ЦБ Узбекистана"""
        try:
            timeout = httpx.Timeout(10.0)
            
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.get(self.cbu_api_url)
                
                if response.status_code == 200:
                    data = response.json()
                    return self._parse_cbu_response(data)
                else:
                    logger.error(f"CBU API вернул статус {response.status_code}")
                    return None
                    
        except httpx.TimeoutException:
            logger.error("Таймаут при запросе к CBU API")
            return None
        except Exception as e:
            logger.error(f"Ошибка запроса к CBU API: {e}")
            return None
    
    def _parse_cbu_response(self, data: list) -> Dict[str, float]:
        """Парсит ответ от API ЦБ Узбекистана"""
        rates = {
            'UZS': 1.0  # Базовая валюта
        }
        
        try:
            for currency_data in data:
                code = currency_data.get('Ccy', '').upper()
                rate = currency_data.get('Rate')
                
                if code in self.supported_currencies and rate:
                    # Курс показывает сколько сумов за единицу валюты
                    rates[code] = float(rate)
            
            logger.debug(f"Парсинг курсов завершён: {rates}")
            return rates
            
        except Exception as e:
            logger.error(f"Ошибка парсинга ответа CBU: {e}")
            return self._get_default_rates()
    
    def _get_default_rates(self) -> Dict[str, float]:
        """Возвращает курсы по умолчанию"""
        return {
            'UZS': 1.0,
            'USD': 12300.0,    # Примерный курс
            'EUR': 13500.0,    # Примерный курс  
            'RUB': 135.0       # Примерный курс
        }
    
    async def convert_amount(
        self,
        amount: float,
        from_currency: str,
        to_currency: str
    ) -> Optional[float]:
        """
        Конвертирует сумму между валютами
        
        Args:
            amount: Сумма для конвертации
            from_currency: Исходная валюта
            to_currency: Целевая валюта
            
        Returns:
            Конвертированная сумма или None при ошибке
        """
        try:
            if from_currency == to_currency:
                return amount
            
            # Нормализуем коды валют
            from_currency = from_currency.upper()
            to_currency = to_currency.upper()
            
            # Получаем актуальные курсы
            rates = await self.get_exchange_rates()
            if not rates:
                logger.error("Не удалось получить курсы валют для конвертации")
                return None
            
            # Проверяем поддержку валют
            if from_currency not in rates or to_currency not in rates:
                logger.error(f"Неподдерживаемые валюты: {from_currency} -> {to_currency}")
                return None
            
            # Конвертируем через базовую валюту (UZS)
            if from_currency == 'UZS':
                # UZS -> другая валюта
                result = amount / rates[to_currency]
            elif to_currency == 'UZS':
                # Другая валюта -> UZS
                result = amount * rates[from_currency]
            else:
                # Другая валюта -> другая валюта (через UZS)
                uzs_amount = amount * rates[from_currency]
                result = uzs_amount / rates[to_currency]
            
            logger.debug(
                f"Конвертация: {amount} {from_currency} = {result:.2f} {to_currency}"
            )
            
            return round(result, 2)
            
        except Exception as e:
            logger.error(f"Ошибка конвертации валют: {e}")
            return None
    
    def format_amount(self, amount: float, currency: str) -> str:
        """
        Форматирует сумму с валютой для отображения
        
        Args:
            amount: Сумма
            currency: Код валюты
            
        Returns:
            Отформатированная строка
        """
        currency = currency.upper()
        
        # Форматируем число с разделителями тысяч
        if amount >= 1000:
            formatted_amount = f"{amount:,.0f}".replace(',', ' ')
        else:
            formatted_amount = f"{amount:.2f}".rstrip('0').rstrip('.')
        
        # Добавляем символ валюты
        symbols = {
            'UZS': 'сум',
            'USD': '$',
            'EUR': '€',
            'RUB': '₽'
        }
        
        symbol = symbols.get(currency, currency)
        
        if currency == 'USD':
            return f"${formatted_amount}"
        elif currency == 'EUR':
            return f"€{formatted_amount}"
        else:
            return f"{formatted_amount} {symbol}"

    def get_supported_currencies(self) -> List[str]:
        """
        Возвращает список поддерживаемых валют
        
        Returns:
            Список кодов валют
        """
        return self.supported_currencies

    async def get_current_rates(self) -> Optional[Dict[str, float]]:
        """
        Получает текущие курсы валют (алиас для get_exchange_rates)
        
        Returns:
            Словарь с курсами валют
        """
        return await self.get_exchange_rates()

    def get_service_status(self) -> Dict[str, Any]:
        """
        Возвращает статус сервиса валют
        
        Returns:
            Словарь со статусом сервиса
        """
        return {
            'service': 'CurrencyService',
            'status': 'active',
            'supported_currencies': self.supported_currencies,
            'base_currency': self.base_currency,
            'api_url': self.cbu_api_url,
            'cache_timeout': self.cache_timeout
        }


# Глобальный экземпляр сервиса
currency_service = CurrencyService()


# Функции-обёртки для удобства использования
async def get_current_rates() -> Optional[Dict[str, float]]:
    """Получает текущие курсы валют"""
    return await currency_service.get_exchange_rates()


async def convert_currency(
    amount: float,
    from_currency: str,
    to_currency: str
) -> Optional[float]:
    """Конвертирует сумму между валютами"""
    return await currency_service.convert_amount(amount, from_currency, to_currency)


def format_money(amount: float, currency: str) -> str:
    """Форматирует денежную сумму для отображения"""
    return currency_service.format_amount(amount, currency) 