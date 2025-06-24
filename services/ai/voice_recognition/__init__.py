"""
Voice Recognition Module
Модуль для распознавания речи через OpenAI Whisper
"""

from .whisper_service import WhisperService, whisper_service, transcribe_voice_message

__all__ = [
    'WhisperService',
    'whisper_service',
    'transcribe_voice_message'
] 