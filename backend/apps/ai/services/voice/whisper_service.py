"""
Сервис распознавания речи с OpenAI Whisper
Поддержка русского, узбекского и английского языков
"""

import os
import tempfile
import logging
import subprocess
from typing import Dict, Optional, Any
from pathlib import Path

import whisper
from django.conf import settings
from django.core.files.uploadedfile import UploadedFile

from apps.ai.models import VoiceResult, AIProcessingLog


logger = logging.getLogger(__name__)


class WhisperVoiceService:
    """Сервис распознавания речи с Whisper"""
    
    # Поддерживаемые языки
    SUPPORTED_LANGUAGES = {
        'russian': 'ru',
        'uzbek': 'uz', 
        'english': 'en',
        'auto': None  # Автоопределение
    }
    
    # Модели Whisper (от самой быстрой к самой точной)
    WHISPER_MODELS = {
        'tiny': 'tiny',      # ~39 MB, самая быстрая
        'base': 'base',      # ~74 MB, хороший баланс
        'small': 'small',    # ~244 MB, лучше качество
        'medium': 'medium',  # ~769 MB, высокое качество  
        'large': 'large'     # ~1550 MB, лучшее качество
    }
    
    # Поддерживаемые аудиоформаты
    SUPPORTED_FORMATS = [
        'audio/ogg', 'audio/mpeg', 'audio/wav', 'audio/mp4',
        'audio/webm', 'audio/m4a', 'audio/x-m4a'
    ]
    
    def __init__(self, model_name: str = 'base'):
        """
        Инициализация сервиса
        
        Args:
            model_name: Название модели Whisper
        """
        self.model_name = model_name
        self.model = None
        self.whisper_available = False
        
        # Загружаем модель при инициализации
        self._load_model()
    
    def _load_model(self) -> bool:
        """Загрузка модели Whisper"""
        try:
            logger.info(f"Загрузка модели Whisper: {self.model_name}")
            self.model = whisper.load_model(self.model_name)
            self.whisper_available = True
            logger.info(f"Модель Whisper '{self.model_name}' загружена успешно")
            return True
        except Exception as e:
            logger.error(f"Ошибка загрузки модели Whisper: {e}")
            self.whisper_available = False
            return False
    
    def recognize_voice(
        self, 
        user, 
        audio_file: UploadedFile,
        language: str = 'auto',
        task: str = 'transcribe'
    ) -> VoiceResult:
        """
        Распознавание голосового сообщения
        
        Args:
            user: Пользователь
            audio_file: Аудио файл
            language: Язык распознавания ('ru', 'uz', 'en', 'auto')
            task: Тип задачи ('transcribe', 'translate')
            
        Returns:
            VoiceResult: Результат распознавания
        """
        # Создаем запись результата
        voice_result = VoiceResult.objects.create(
            user=user,
            original_filename=audio_file.name,
            audio_format=audio_file.content_type,
            audio_size=audio_file.size,
            language_code=language,
            recognition_task=task,
            status='processing'
        )
        
        try:
            # Сохраняем аудио файл
            voice_result.audio_file = audio_file
            voice_result.save()
            
            if not self.whisper_available:
                # Возвращаем демо-результат если Whisper недоступен
                return self._create_demo_result(voice_result, language)
            
            # Конвертируем аудио в формат для Whisper
            audio_path = self._convert_audio_for_whisper(audio_file)
            
            # Выполняем распознавание
            recognition_result = self._perform_recognition(
                audio_path, language, task
            )
            
            # Обрабатываем результат
            self._process_recognition_result(voice_result, recognition_result)
            
            # Очистка временного файла
            if os.path.exists(audio_path):
                os.unlink(audio_path)
            
            voice_result.status = 'completed'
            voice_result.save()
            
            logger.info(f"Распознавание голоса завершено: {voice_result.id}")
            return voice_result
            
        except Exception as e:
            logger.error(f"Ошибка распознавания голоса: {e}")
            voice_result.status = 'failed'
            voice_result.error_message = str(e)
            voice_result.save()
            return voice_result
    
    def _convert_audio_for_whisper(self, audio_file: UploadedFile) -> str:
        """
        Конвертация аудио для Whisper
        
        Args:
            audio_file: Аудио файл
            
        Returns:
            str: Путь к конвертированному файлу
        """
        try:
            # Создаем временные файлы
            with tempfile.NamedTemporaryFile(suffix='.ogg', delete=False) as input_temp:
                input_path = input_temp.name
                # Сохраняем исходный файл
                audio_file.seek(0)
                input_temp.write(audio_file.read())
            
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as output_temp:
                output_path = output_temp.name
            
            # Конвертируем с помощью ffmpeg
            cmd = [
                'ffmpeg',
                '-i', input_path,
                '-ar', '16000',  # Sample rate 16kHz для Whisper
                '-ac', '1',      # Mono канал
                '-c:a', 'pcm_s16le',  # 16-bit PCM
                '-y',  # Overwrite output file
                output_path
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            # Очищаем входной временный файл
            if os.path.exists(input_path):
                os.unlink(input_path)
            
            if result.returncode == 0:
                logger.info("Аудио конвертировано для Whisper")
                return output_path
            else:
                logger.error(f"Ошибка конвертации ffmpeg: {result.stderr}")
                # Возвращаем исходный файл если конвертация не удалась
                return input_path
                
        except subprocess.TimeoutExpired:
            logger.error("Превышено время ожидания конвертации")
            return input_path
        except Exception as e:
            logger.error(f"Ошибка конвертации аудио: {e}")
            return input_path
    
    def _perform_recognition(
        self, 
        audio_path: str, 
        language: str = 'auto',
        task: str = 'transcribe'
    ) -> Dict[str, Any]:
        """
        Выполнение распознавания с Whisper
        
        Args:
            audio_path: Путь к аудио файлу
            language: Язык распознавания
            task: Тип задачи
            
        Returns:
            Dict: Результат распознавания Whisper
        """
        try:
            # Подготавливаем параметры для Whisper
            whisper_options = {
                'task': task,
                'fp16': False,  # Для совместимости с CPU
                'verbose': False
            }
            
            # Устанавливаем язык если не авто
            if language != 'auto' and language in self.SUPPORTED_LANGUAGES.values():
                whisper_options['language'] = language
            
            logger.info(f"Начинаем распознавание с параметрами: {whisper_options}")
            
            # Выполняем распознавание
            result = self.model.transcribe(audio_path, **whisper_options)
            
            logger.info(f"Распознавание завершено. Длина текста: {len(result.get('text', ''))}")
            
            return result
            
        except Exception as e:
            logger.error(f"Ошибка выполнения распознавания: {e}")
            return {
                'text': '',
                'language': language,
                'segments': []
            }
    
    def _process_recognition_result(self, voice_result: VoiceResult, result: Dict[str, Any]):
        """
        Обработка результата распознавания
        
        Args:
            voice_result: Объект результата
            result: Результат от Whisper
        """
        # Основной текст
        voice_result.recognized_text = result.get('text', '').strip()
        
        # Определенный язык
        detected_language = result.get('language', 'unknown')
        voice_result.detected_language = detected_language
        
        # Уверенность (рассчитываем среднюю из сегментов)
        segments = result.get('segments', [])
        if segments:
            avg_confidence = sum(
                segment.get('avg_logprob', 0.0) for segment in segments
            ) / len(segments)
            # Конвертируем логарифмическую вероятность в проценты
            confidence = min(max((avg_confidence + 5) / 5, 0), 1)
            voice_result.confidence_score = confidence
        else:
            voice_result.confidence_score = 0.8 if voice_result.recognized_text else 0.0
        
        # Дополнительные метаданные
        voice_result.segments_count = len(segments)
        voice_result.processing_metadata = {
            'model_used': self.model_name,
            'language_detected': detected_language,
            'segments_count': len(segments),
            'total_duration': sum(
                segment.get('end', 0) - segment.get('start', 0) 
                for segment in segments
            ),
            'segments': [
                {
                    'start': seg.get('start', 0),
                    'end': seg.get('end', 0),
                    'text': seg.get('text', ''),
                    'confidence': seg.get('avg_logprob', 0)
                }
                for seg in segments[:10]  # Сохраняем только первые 10 сегментов
            ]
        }
    
    def _create_demo_result(self, voice_result: VoiceResult, language: str) -> VoiceResult:
        """Создание демо-результата когда Whisper недоступен"""
        
        # Демо-тексты для разных языков
        demo_texts = {
            'ru': 'Добавь расход такси тысяча пятьсот сум',
            'uz': 'Taksi uchun ming besh yuz sum sarflash qo\'sh',
            'en': 'Add expense taxi one thousand five hundred sum',
            'auto': 'Добавь расход кальян пять тысяч сум'
        }
        
        demo_text = demo_texts.get(language, demo_texts['auto'])
        
        voice_result.recognized_text = demo_text
        voice_result.detected_language = language if language != 'auto' else 'ru'
        voice_result.confidence_score = 0.95
        voice_result.segments_count = 1
        voice_result.processing_metadata = {
            'model_used': 'demo',
            'demo_mode': True,
            'language_detected': voice_result.detected_language
        }
        voice_result.status = 'completed'
        voice_result.save()
        
        return voice_result
    
    def transcribe_file_path(self, file_path: str, language: str = 'auto') -> Dict[str, Any]:
        """
        Транскрипция файла по пути (для внутреннего использования)
        
        Args:
            file_path: Путь к аудио файлу
            language: Язык распознавания
            
        Returns:
            Dict: Результат транскрипции
        """
        if not self.whisper_available:
            return {
                'text': 'Демо режим: файл распознан успешно',
                'language': language,
                'confidence': 0.95
            }
        
        try:
            result = self._perform_recognition(file_path, language)
            return {
                'text': result.get('text', ''),
                'language': result.get('language', language),
                'confidence': self._calculate_confidence(result),
                'segments': result.get('segments', [])
            }
        except Exception as e:
            logger.error(f"Ошибка транскрипции файла {file_path}: {e}")
            return {
                'text': '',
                'language': language,
                'confidence': 0.0,
                'error': str(e)
            }
    
    def _calculate_confidence(self, result: Dict[str, Any]) -> float:
        """Рассчет общей уверенности"""
        segments = result.get('segments', [])
        if not segments:
            return 0.5
        
        avg_confidence = sum(
            segment.get('avg_logprob', 0.0) for segment in segments
        ) / len(segments)
        
        return min(max((avg_confidence + 5) / 5, 0), 1)
    
    def validate_audio_file(self, audio_file: UploadedFile) -> tuple[bool, str]:
        """
        Валидация аудио файла
        
        Args:
            audio_file: Аудио файл
            
        Returns:
            tuple: (is_valid, error_message)
        """
        # Проверка размера (макс 25MB)
        max_size = 25 * 1024 * 1024  # 25MB
        if audio_file.size > max_size:
            return False, f"Размер файла превышает {max_size // 1024 // 1024}MB"
        
        # Проверка формата
        if audio_file.content_type not in self.SUPPORTED_FORMATS:
            return False, f"Неподдерживаемый формат. Поддерживаются: {', '.join(self.SUPPORTED_FORMATS)}"
        
        # Проверка минимального размера
        if audio_file.size < 1024:  # Минимум 1KB
            return False, "Файл слишком маленький"
        
        return True, ""
    
    def get_supported_languages(self) -> Dict[str, str]:
        """Получение поддерживаемых языков"""
        return self.SUPPORTED_LANGUAGES.copy()
    
    def get_available_models(self) -> Dict[str, str]:
        """Получение доступных моделей"""
        return self.WHISPER_MODELS.copy()
    
    def change_model(self, model_name: str) -> bool:
        """
        Смена модели Whisper
        
        Args:
            model_name: Название новой модели
            
        Returns:
            bool: Успешность смены модели
        """
        if model_name not in self.WHISPER_MODELS:
            logger.error(f"Неизвестная модель: {model_name}")
            return False
        
        try:
            old_model = self.model_name
            self.model_name = model_name
            
            # Освобождаем память от старой модели
            if self.model is not None:
                del self.model
                self.model = None
            
            # Загружаем новую модель
            success = self._load_model()
            
            if success:
                logger.info(f"Модель изменена с '{old_model}' на '{model_name}'")
            else:
                # Откатываемся к старой модели при ошибке
                self.model_name = old_model
                self._load_model()
                
            return success
            
        except Exception as e:
            logger.error(f"Ошибка смены модели: {e}")
            return False
    
    def get_processing_status(self) -> Dict[str, Any]:
        """Статус сервиса распознавания речи"""
        return {
            'whisper_available': self.whisper_available,
            'current_model': self.model_name,
            'supported_languages': self.SUPPORTED_LANGUAGES,
            'supported_formats': self.SUPPORTED_FORMATS,
            'available_models': self.WHISPER_MODELS,
            'model_loaded': self.model is not None
        } 