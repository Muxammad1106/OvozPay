"""
Celery задачи для обработки AI запросов через DeepSeek API
"""

from celery import shared_task
import logging
from django.utils import timezone
from services.deepseek_ai import process_voice_message, process_receipt_image, process_document_image

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def process_voice_message_task(self, audio_file_path: str, message_id: int = None):
    """
    Celery задача для обработки голосового сообщения
    
    Args:
        audio_file_path: Путь к аудио файлу
        message_id: ID сообщения в базе данных (опционально)
    
    Returns:
        dict: Результат обработки
    """
    try:
        logger.info(f"Начинаю обработку голосового сообщения: {audio_file_path}")
        
        # Обрабатываем голосовое сообщение через DeepSeek
        text = process_voice_message(audio_file_path)
        
        if text:
            logger.info(f"Голосовое сообщение успешно обработано: {len(text)} символов")
            return {
                'status': 'success',
                'text': text,
                'message_id': message_id,
                'processed_at': str(timezone.now())
            }
        else:
            logger.error("Не удалось обработать голосовое сообщение")
            return {
                'status': 'error',
                'message': 'Не удалось распознать речь',
                'message_id': message_id
            }
            
    except Exception as exc:
        logger.error(f"Ошибка при обработке голосового сообщения: {str(exc)}")
        
        # Повторяем задачу при ошибке
        if self.request.retries < self.max_retries:
            raise self.retry(countdown=60, exc=exc)
        
        return {
            'status': 'error',
            'message': str(exc),
            'message_id': message_id
        }


@shared_task(bind=True, max_retries=3)
def process_receipt_image_task(self, image_file_path: str, transaction_id: int = None):
    """
    Celery задача для обработки изображения чека
    
    Args:
        image_file_path: Путь к изображению
        transaction_id: ID транзакции в базе данных (опционально)
    
    Returns:
        dict: Результат обработки
    """
    try:
        logger.info(f"Начинаю обработку чека: {image_file_path}")
        
        # Обрабатываем изображение чека через DeepSeek
        text = process_receipt_image(image_file_path)
        
        if text:
            logger.info(f"Чек успешно обработан: {len(text)} символов")
            
            # Здесь можно добавить парсинг суммы, даты и других данных
            parsed_data = parse_receipt_data(text)
            
            return {
                'status': 'success',
                'raw_text': text,
                'parsed_data': parsed_data,
                'transaction_id': transaction_id,
                'processed_at': str(timezone.now())
            }
        else:
            logger.error("Не удалось обработать изображение чека")
            return {
                'status': 'error',
                'message': 'Не удалось извлечь текст из изображения',
                'transaction_id': transaction_id
            }
            
    except Exception as exc:
        logger.error(f"Ошибка при обработке чека: {str(exc)}")
        
        # Повторяем задачу при ошибке
        if self.request.retries < self.max_retries:
            raise self.retry(countdown=60, exc=exc)
        
        return {
            'status': 'error',
            'message': str(exc),
            'transaction_id': transaction_id
        }


def parse_receipt_data(text: str) -> dict:
    """
    Парсит данные из текста чека
    
    Args:
        text: Текст чека
        
    Returns:
        dict: Распарсенные данные
    """
    import re
    from datetime import datetime
    
    parsed = {
        'amount': None,
        'date': None,
        'store': None,
        'items': []
    }
    
    try:
        # Ищем сумму (различные форматы)
        amount_patterns = [
            r'итого:?\s*(\d+(?:[.,]\d{2})?)',
            r'всего:?\s*(\d+(?:[.,]\d{2})?)',
            r'к доплате:?\s*(\d+(?:[.,]\d{2})?)',
            r'(\d+(?:[.,]\d{2})?)\s*сум',
        ]
        
        for pattern in amount_patterns:
            match = re.search(pattern, text.lower())
            if match:
                parsed['amount'] = float(match.group(1).replace(',', '.'))
                break
        
        # Ищем дату
        date_patterns = [
            r'(\d{1,2}[./]\d{1,2}[./]\d{2,4})',
            r'(\d{1,2}-\d{1,2}-\d{2,4})',
        ]
        
        for pattern in date_patterns:
            match = re.search(pattern, text)
            if match:
                try:
                    # Пытаемся распарсить дату
                    date_str = match.group(1)
                    for date_format in ['%d.%m.%Y', '%d/%m/%Y', '%d-%m-%Y', '%d.%m.%y']:
                        try:
                            parsed['date'] = datetime.strptime(date_str, date_format).date().isoformat()
                            break
                        except ValueError:
                            continue
                    break
                except:
                    continue
        
        # Ищем название магазина (первые несколько строк)
        lines = text.split('\n')[:5]
        for line in lines:
            line = line.strip()
            if len(line) > 3 and not re.match(r'^\d', line):
                parsed['store'] = line
                break
                
    except Exception as e:
        logger.error(f"Ошибка парсинга чека: {str(e)}")
    
    return parsed 