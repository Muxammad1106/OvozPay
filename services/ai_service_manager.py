"""
AI Service Manager - Центральный менеджер для управления всеми AI сервисами
Координирует работу WhisperService, EasyOCRService, NLPService и CurrencyService
"""

import asyncio
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime

from .ai.voice_recognition.whisper_service import whisper_service
from .ai.ocr.easyocr_service import easyocr_service
from .ai.text_processing.nlp_service import nlp_service
from .currency_service import currency_service

logger = logging.getLogger(__name__)


class AIServiceManager:
    """Центральный менеджер для всех AI сервисов"""
    
    def __init__(self):
        self.whisper = whisper_service
        self.ocr = easyocr_service
        self.nlp = nlp_service
        self.currency = currency_service
        
        self.is_initialized = False
        self._initialization_lock = asyncio.Lock()
    
    async def initialize_services(self) -> bool:
        """
        Инициализирует все AI сервисы
        
        Returns:
            True если все сервисы успешно инициализированы
        """
        async with self._initialization_lock:
            if self.is_initialized:
                return True
            
            try:
                logger.info("Начинаем инициализацию AI сервисов...")
                
                initialization_results = []
                
                # Проверяем статус всех сервисов
                services_status = await self.get_all_services_status()
                
                for service_name, status in services_status.items():
                    if status.get('status') == 'active':
                        logger.info(f"✅ {service_name} готов к работе")
                        initialization_results.append(True)
                    elif status.get('status') == 'error':
                        logger.warning(f"⚠️ {service_name} имеет ошибки: {status.get('error', 'Неизвестная ошибка')}")
                        initialization_results.append(False)
                    else:
                        logger.warning(f"❓ {service_name} в неопределённом состоянии")
                        initialization_results.append(False)
                
                # Считаем успешными если хотя бы 75% сервисов работают
                success_rate = sum(initialization_results) / len(initialization_results)
                
                if success_rate >= 0.75:
                    self.is_initialized = True
                    logger.info(f"🚀 AI сервисы инициализированы! Успешность: {success_rate:.1%}")
                    return True
                else:
                    logger.error(f"❌ Инициализация AI сервисов провалена. Успешность: {success_rate:.1%}")
                    return False
                    
            except Exception as e:
                logger.error(f"Критическая ошибка при инициализации AI сервисов: {e}")
                return False
    
    async def process_voice_message(
        self,
        audio_file_path: str,
        user_id: str,
        language: str = 'ru'
    ) -> Optional[Dict[str, Any]]:
        """
        Полный пайплайн обработки голосового сообщения
        
        Args:
            audio_file_path: Путь к аудио файлу
            user_id: ID пользователя
            language: Язык распознавания
            
        Returns:
            Результат обработки с извлечёнными финансовыми данными
        """
        try:
            logger.info(f"Начинаем обработку голосового сообщения пользователя {user_id}")
            
            # 1. Распознавание речи через Whisper
            transcription_result = await self.whisper.transcribe_audio(
                audio_file_path, language, user_id
            )
            
            if not transcription_result or not transcription_result.get('text'):
                logger.warning("Не удалось распознать речь")
                return {
                    'status': 'failed',
                    'error': 'speech_recognition_failed',
                    'message': 'Не удалось распознать голосовое сообщение'
                }
            
            recognized_text = transcription_result['text']
            logger.info(f"Распознанный текст: '{recognized_text}'")
            
            # 2. Анализ текста через NLP
            nlp_result = await self.nlp.parse_transaction_text(recognized_text, language)
            
            if not nlp_result or nlp_result.get('confidence', 0) < 0.3:
                logger.warning("Низкая уверенность в парсинге NLP")
                return {
                    'status': 'failed',
                    'error': 'nlp_parsing_failed',
                    'message': 'Не удалось извлечь финансовые данные из текста',
                    'recognized_text': recognized_text
                }
            
            # 3. Конвертация валют (если нужно)
            final_amount = nlp_result.get('amount')
            final_currency = nlp_result.get('currency', 'UZS')
            
            # Если валюта не UZS, конвертируем в UZS для единообразия
            if final_currency != 'UZS' and final_amount:
                converted_amount = await self.currency.convert_amount(
                    final_amount, final_currency, 'UZS'
                )
                if converted_amount:
                    nlp_result['amount_uzs'] = converted_amount
            
            # 4. Формируем финальный результат
            result = {
                'status': 'success',
                'processing_data': {
                    'audio_duration': transcription_result.get('audio_duration', 0),
                    'speech_confidence': transcription_result.get('confidence', 0),
                    'nlp_confidence': nlp_result.get('confidence', 0),
                    'processing_time': transcription_result.get('processing_time', 0)
                },
                'transaction_data': {
                    'original_text': recognized_text,
                    'transaction_type': nlp_result.get('transaction_type'),
                    'amount': nlp_result.get('amount'),
                    'currency': nlp_result.get('currency'),
                    'amount_uzs': nlp_result.get('amount_uzs'),
                    'category': nlp_result.get('category'),
                    'description': nlp_result.get('description', recognized_text),
                    'date': nlp_result.get('date'),
                    'extracted_entities': nlp_result.get('extracted_entities', {})
                }
            }
            
            logger.info(
                f"Голосовое сообщение успешно обработано: "
                f"{nlp_result.get('transaction_type')} {nlp_result.get('amount')} {nlp_result.get('currency')}"
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Ошибка обработки голосового сообщения: {e}")
            return {
                'status': 'failed',
                'error': 'processing_error',
                'message': f'Ошибка обработки: {str(e)}'
            }
    
    async def process_receipt_image(
        self,
        image_file_path: str,
        user_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Полный пайплайн обработки изображения чека
        
        Args:
            image_file_path: Путь к изображению
            user_id: ID пользователя
            
        Returns:
            Результат обработки с извлечёнными данными чека
        """
        try:
            logger.info(f"Начинаем обработку изображения чека пользователя {user_id}")
            
            # 1. OCR обработка изображения
            ocr_result = await self.ocr.extract_text_from_image(
                image_file_path, enhance_image=True, user_id=user_id
            )
            
            if not ocr_result or not ocr_result.get('structured_data'):
                logger.warning("Не удалось извлечь текст с изображения")
                return {
                    'status': 'failed',
                    'error': 'ocr_failed',
                    'message': 'Не удалось распознать текст на изображении'
                }
            
            structured_data = ocr_result['structured_data']
            raw_text = ocr_result.get('raw_text', '')
            
            logger.info(f"OCR обработка завершена, найдена сумма: {structured_data.get('total_amount')}")
            
            # 2. Дополнительный NLP анализ (если нужно)
            nlp_result = None
            if raw_text and len(raw_text) > 10:
                nlp_result = await self.nlp.parse_transaction_text(raw_text, 'ru')
            
            # 3. Конвертация валют для итоговой суммы
            total_amount = structured_data.get('total_amount')
            if total_amount and total_amount > 0:
                # Предполагаем, что чеки в Узбекистане в сумах
                structured_data['amount_uzs'] = total_amount
                structured_data['currency'] = 'UZS'
            
            # 4. Формируем результат
            result = {
                'status': 'success',
                'processing_data': {
                    'ocr_confidence': ocr_result.get('confidence', 0),
                    'processing_time': ocr_result.get('processing_time', 0),
                    'detected_regions': ocr_result.get('detected_regions', 0),
                    'nlp_confidence': nlp_result.get('confidence', 0) if nlp_result else 0
                },
                'receipt_data': {
                    'raw_text': raw_text,
                    'total_amount': structured_data.get('total_amount'),
                    'currency': structured_data.get('currency', 'UZS'),
                    'shop_name': structured_data.get('shop_name'),
                    'items': structured_data.get('items', []),
                    'dates': structured_data.get('dates', []),
                    'all_amounts': structured_data.get('amounts', [])
                },
                'transaction_suggestions': []
            }
            
            # 5. Генерируем предложения транзакций
            if total_amount and total_amount > 0:
                # Основная транзакция
                main_transaction = {
                    'transaction_type': 'expense',
                    'amount': total_amount,
                    'currency': 'UZS',
                    'category': 'продукты',  # По умолчанию
                    'description': f"Покупка в {structured_data.get('shop_name', 'магазине')}",
                    'date': structured_data.get('dates', [None])[0]
                }
                result['transaction_suggestions'].append(main_transaction)
            
            logger.info(f"Изображение чека успешно обработано, найдено {len(result['transaction_suggestions'])} транзакций")
            
            return result
            
        except Exception as e:
            logger.error(f"Ошибка обработки изображения чека: {e}")
            return {
                'status': 'failed',
                'error': 'processing_error',
                'message': f'Ошибка обработки: {str(e)}'
            }
    
    async def get_all_services_status(self) -> Dict[str, Dict[str, Any]]:
        """Возвращает статус всех AI сервисов"""
        try:
            return {
                'whisper_service': self.whisper.get_service_status(),
                'easyocr_service': self.ocr.get_service_status(),
                'nlp_service': self.nlp.get_service_status(),
                'currency_service': self.currency.get_service_status()
            }
        except Exception as e:
            logger.error(f"Ошибка получения статуса сервисов: {e}")
            return {}
    
    async def cleanup_temp_files(self) -> None:
        """Очищает временные файлы всех сервисов"""
        try:
            logger.info("Очищаем временные файлы AI сервисов...")
            
            # Очистка Whisper
            if hasattr(self.whisper, 'cleanup_temp_files'):
                self.whisper.cleanup_temp_files()
            
            # Очистка OCR
            if hasattr(self.ocr, 'cleanup_temp_files'):
                self.ocr.cleanup_temp_files()
            
            logger.info("Временные файлы очищены")
            
        except Exception as e:
            logger.error(f"Ошибка очистки временных файлов: {e}")
    
    async def initialize_all_services(self) -> bool:
        """
        Инициализирует все AI сервисы
        
        Returns:
            bool: True если все сервисы инициализированы успешно
        """
        try:
            logger.info("Инициализируем все AI сервисы...")
            
            # Инициализация всех сервисов
            whisper_init = await self.whisper.initialize()
            ocr_init = await self.ocr.initialize()
            
            # NLP и Currency сервисы не требуют асинхронной инициализации
            nlp_init = True
            currency_init = True
            
            success = whisper_init and ocr_init and nlp_init and currency_init
            
            if success:
                logger.info("Все AI сервисы успешно инициализированы")
            else:
                logger.warning(f"Ошибки инициализации: Whisper={whisper_init}, OCR={ocr_init}")
            
            return success
            
        except Exception as e:
            logger.error(f"Ошибка инициализации AI сервисов: {e}")
            return False

    async def get_services_status(self) -> Dict[str, Any]:
        """
        Получает статус всех сервисов
        
        Returns:
            Словарь со статусом каждого сервиса
        """
        return await self.get_all_services_status()

    async def health_check_all(self) -> Dict[str, bool]:
        """
        Выполняет health check всех сервисов
        
        Returns:
            Словарь с результатами health check
        """
        try:
            logger.info("Выполняем health check всех AI сервисов...")
            
            # Health check всех сервисов
            whisper_health = await self.whisper.health_check()
            ocr_health = await self.ocr.health_check()
            
            # NLP и Currency не имеют health_check
            nlp_health = True
            currency_health = True
            
            health_results = {
                'whisper': whisper_health,
                'ocr': ocr_health,
                'nlp': nlp_health,
                'currency': currency_health,
                'overall': whisper_health and ocr_health and nlp_health and currency_health
            }
            
            logger.info(f"Health check завершён: {health_results}")
            return health_results
            
        except Exception as e:
            logger.error(f"Ошибка health check: {e}")
            return {
                'whisper': False,
                'ocr': False,
                'nlp': False,
                'currency': False,
                'overall': False
            }

    def get_manager_status(self) -> Dict[str, Any]:
        """Возвращает общий статус менеджера"""
        return {
            'manager': 'AIServiceManager',
            'status': 'active' if self.is_initialized else 'not_initialized',
            'initialized': self.is_initialized,
            'services_count': 4,
            'last_check': datetime.now().isoformat()
        }


# Глобальный экземпляр менеджера
ai_manager = AIServiceManager()


# Функции-обёртки для удобства использования
async def process_voice_command(
    audio_file_path: str,
    user_id: str,
    language: str = 'ru'
) -> Optional[Dict[str, Any]]:
    """Обрабатывает голосовую команду"""
    return await ai_manager.process_voice_message(audio_file_path, user_id, language)


async def process_receipt_photo(
    image_file_path: str,
    user_id: str
) -> Optional[Dict[str, Any]]:
    """Обрабатывает фото чека"""
    return await ai_manager.process_receipt_image(image_file_path, user_id)


async def initialize_ai_services() -> bool:
    """Инициализирует все AI сервисы"""
    return await ai_manager.initialize_services()


async def get_ai_services_health() -> Dict[str, Any]:
    """Возвращает статус здоровья всех AI сервисов"""
    services_status = await ai_manager.get_all_services_status()
    manager_status = ai_manager.get_manager_status()
    
    return {
        'manager': manager_status,
        'services': services_status
    } 