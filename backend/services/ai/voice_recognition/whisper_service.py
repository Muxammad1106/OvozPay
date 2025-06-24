"""
WhisperService - Локальное распознавание речи через OpenAI Whisper
Поддерживает русский, узбекский и английский языки
"""

import os
import asyncio
import logging
from typing import Optional, Dict, Any
from pathlib import Path
import subprocess
import tempfile
from django.conf import settings

logger = logging.getLogger(__name__)


class WhisperService:
    """Сервис для распознавания речи через OpenAI Whisper (локально)"""
    
    def __init__(self):
        self.model_name = getattr(settings, 'WHISPER_MODEL', 'base')  # tiny, base, small, medium, large
        self.supported_languages = ['ru', 'uz', 'en']
        self.temp_dir = Path(tempfile.gettempdir()) / 'ovozpay_audio'
        self.temp_dir.mkdir(exist_ok=True)
        
        # Проверяем установлен ли Whisper
        self._check_whisper_installation()
    
    def _check_whisper_installation(self) -> None:
        """Проверяет установлен ли OpenAI Whisper"""
        try:
            result = subprocess.run(
                ['whisper', '--help'], 
                capture_output=True, 
                text=True, 
                timeout=10
            )
            if result.returncode != 0:
                raise Exception("Whisper не найден")
            logger.info("Whisper успешно найден в системе")
        except Exception as e:
            logger.error(f"Ошибка проверки Whisper: {e}")
            logger.warning("Для работы голосовых команд установите: pip install openai-whisper")
    
    async def transcribe_audio(
        self,
        audio_file_path: str,
        language: str = 'ru',
        user_id: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Преобразует аудио в текст
        
        Args:
            audio_file_path: Путь к аудио файлу
            language: Язык распознавания (ru, uz, en)
            user_id: ID пользователя для логирования
            
        Returns:
            Словарь с результатом распознавания или None при ошибке
        """
        start_time = asyncio.get_event_loop().time()
        
        try:
            # Валидация входных данных
            if not os.path.exists(audio_file_path):
                raise FileNotFoundError(f"Аудио файл не найден: {audio_file_path}")
            
            if language not in self.supported_languages:
                logger.warning(f"Неподдерживаемый язык {language}, используем 'ru'")
                language = 'ru'
            
            logger.info(f"Начинаем распознавание аудио для пользователя {user_id}")
            
            # Запускаем Whisper в отдельном процессе
            result = await self._run_whisper_transcription(audio_file_path, language)
            
            # Обрабатываем результат
            if result and result.get('text'):
                processing_time = asyncio.get_event_loop().time() - start_time
                
                transcription_result = {
                    'text': result['text'].strip(),
                    'language': result.get('language', language),
                    'confidence': self._calculate_confidence(result),
                    'processing_time': processing_time,
                    'audio_duration': result.get('duration', 0),
                    'segments': result.get('segments', [])
                }
                
                logger.info(
                    f"Распознавание завершено за {processing_time:.2f}с: "
                    f"'{transcription_result['text'][:50]}...'"
                )
                
                return transcription_result
            else:
                logger.warning("Whisper не смог распознать текст")
                return None
                
        except Exception as e:
            processing_time = asyncio.get_event_loop().time() - start_time
            logger.error(f"Ошибка распознавания аудио за {processing_time:.2f}с: {e}")
            return None
    
    async def _run_whisper_transcription(
        self, 
        audio_file_path: str, 
        language: str
    ) -> Optional[Dict[str, Any]]:
        """Запускает процесс распознавания Whisper"""
        try:
            # Команда для Whisper с JSON выводом
            command = [
                'whisper',
                audio_file_path,
                '--model', self.model_name,
                '--language', language,
                '--output_format', 'json',
                '--output_dir', str(self.temp_dir),
                '--verbose', 'False'
            ]
            
            # Запускаем в отдельном процессе асинхронно
            process = await asyncio.create_subprocess_exec(
                *command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode != 0:
                logger.error(f"Ошибка Whisper: {stderr.decode()}")
                return None
            
            # Читаем JSON результат
            audio_filename = Path(audio_file_path).stem
            json_file = self.temp_dir / f"{audio_filename}.json"
            
            if json_file.exists():
                import json
                with open(json_file, 'r', encoding='utf-8') as f:
                    result = json.load(f)
                
                # Очищаем временный файл
                json_file.unlink()
                
                return result
            else:
                logger.error("JSON файл результата не найден")
                return None
                
        except Exception as e:
            logger.error(f"Ошибка выполнения Whisper: {e}")
            return None
    
    def _calculate_confidence(self, whisper_result: Dict[str, Any]) -> float:
        """Рассчитывает уверенность распознавания на основе сегментов"""
        try:
            segments = whisper_result.get('segments', [])
            if not segments:
                return 0.5  # Средняя уверенность по умолчанию
            
            # Средняя уверенность по всем сегментам
            confidences = [
                segment.get('avg_logprob', 0) for segment in segments
                if 'avg_logprob' in segment
            ]
            
            if confidences:
                # Преобразуем логарифмическую вероятность в процент
                avg_confidence = sum(confidences) / len(confidences)
                # Нормализуем от -1 до 0 в диапазон 0-1
                confidence = max(0, min(1, (avg_confidence + 1)))
                return confidence
            
            return 0.5
            
        except Exception:
            return 0.5
    
    def cleanup_temp_files(self, older_than_hours: int = 24) -> None:
        """Очищает временные файлы старше указанного времени"""
        try:
            import time
            current_time = time.time()
            cutoff_time = current_time - (older_than_hours * 3600)
            
            for file_path in self.temp_dir.glob('*'):
                if file_path.is_file() and file_path.stat().st_mtime < cutoff_time:
                    file_path.unlink()
                    logger.debug(f"Удален временный файл: {file_path}")
                    
        except Exception as e:
            logger.error(f"Ошибка очистки временных файлов: {e}")
    
    async def initialize(self) -> bool:
        """
        Инициализирует Whisper сервис
        
        Returns:
            bool: True если инициализация успешна
        """
        try:
            # Проверяем доступность Whisper
            result = subprocess.run(
                ['whisper', '--help'], 
                capture_output=True, 
                timeout=10
            )
            
            if result.returncode == 0:
                logger.info("Whisper сервис успешно инициализирован")
                return True
            else:
                logger.error("Whisper не найден в системе")
                return False
                
        except Exception as e:
            logger.error(f"Ошибка инициализации Whisper: {e}")
            return False

    async def health_check(self) -> bool:
        """
        Проверяет готовность сервиса к работе
        
        Returns:
            bool: True если сервис готов
        """
        try:
            # Проверяем доступность Whisper
            result = subprocess.run(
                ['whisper', '--help'], 
                capture_output=True, 
                timeout=5
            )
            
            if result.returncode == 0:
                logger.info("Whisper сервис готов к работе")
                return True
            else:
                logger.warning("Whisper не доступен")
                return False
                
        except Exception as e:
            logger.error(f"Ошибка проверки здоровья Whisper: {e}")
            return False

    def get_supported_formats(self) -> list:
        """
        Возвращает список поддерживаемых аудио форматов
        
        Returns:
            list: Список поддерживаемых форматов
        """
        return [
            'mp3', 'wav', 'flac', 'm4a', 'ogg', 
            'wma', 'aac', 'mp4', 'avi', 'mov'
        ]

    def get_service_status(self) -> Dict[str, Any]:
        """Возвращает статус сервиса"""
        try:
            # Проверяем доступность Whisper
            result = subprocess.run(
                ['whisper', '--help'], 
                capture_output=True, 
                timeout=5
            )
            
            whisper_available = result.returncode == 0
            
            return {
                'service': 'WhisperService',
                'status': 'active' if whisper_available else 'error',
                'model': self.model_name,
                'supported_languages': self.supported_languages,
                'temp_dir': str(self.temp_dir),
                'whisper_installed': whisper_available
            }
            
        except Exception as e:
            return {
                'service': 'WhisperService',
                'status': 'error',
                'error': str(e),
                'whisper_installed': False
            }


# Глобальный экземпляр сервиса
whisper_service = WhisperService()


# Функции-обёртки для удобства использования
async def transcribe_voice_message(
    audio_file_path: str,
    language: str = 'ru',
    user_id: Optional[str] = None
) -> Optional[str]:
    """
    Упрощённая функция для распознавания голосового сообщения
    
    Args:
        audio_file_path: Путь к аудио файлу
        language: Язык распознавания
        user_id: ID пользователя
        
    Returns:
        Распознанный текст или None
    """
    result = await whisper_service.transcribe_audio(audio_file_path, language, user_id)
    return result['text'] if result else None


def sync_transcribe_voice_message(
    audio_file_path: str,
    language: str = 'ru',
    user_id: Optional[str] = None
) -> Optional[str]:
    """Синхронная версия распознавания голоса"""
    return asyncio.run(transcribe_voice_message(audio_file_path, language, user_id)) 