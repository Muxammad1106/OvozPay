"""
Django management команда для инициализации AI сервисов
"""

import asyncio
import logging
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone


class Command(BaseCommand):
    help = 'Инициализирует и проверяет все AI сервисы OvozPay'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--check-only',
            action='store_true',
            help='Только проверить статус сервисов, не инициализировать'
        )
        
        parser.add_argument(
            '--install-deps',
            action='store_true',
            help='Показать инструкции по установке зависимостей'
        )
    
    def handle(self, *args, **options):
        self.stdout.write(
            self.style.HTTP_INFO('🚀 Проверка AI сервисов OvozPay...')
        )
        
        if options.get('install_deps'):
            self._show_installation_instructions()
            return
        
        try:
            # Проверяем базовые зависимости
            missing_deps = self._check_dependencies()
            
            if missing_deps:
                self.stdout.write(
                    self.style.ERROR('❌ Отсутствуют зависимости:')
                )
                for dep in missing_deps:
                    self.stdout.write(f"  - {dep}")
                
                self.stdout.write('')
                self.stdout.write(
                    self.style.WARNING('💡 Для установки выполните:')
                )
                self.stdout.write('pip install -r requirements.txt')
                self.stdout.write('')
                self.stdout.write('Или запустите: python manage.py init_ai_services --install-deps')
                return
            
            self.stdout.write(
                self.style.SUCCESS('✅ Все зависимости установлены!')
            )
            
            # Проверяем статус сервисов  
            if options.get('check_only'):
                self._check_services_status()
            else:
                self.stdout.write(
                    self.style.HTTP_INFO('ℹ️ Для полной проверки используйте --check-only')
                )
                
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'💥 Ошибка: {e}')
            )
            raise CommandError(f'Не удалось проверить AI сервисы: {e}')
    
    def _check_dependencies(self):
        """Проверяет наличие необходимых зависимостей"""
        missing = []
        
        # Проверяем основные AI библиотеки
        deps_to_check = [
            ('whisper', 'openai-whisper'),
            ('easyocr', 'easyocr'),
            ('cv2', 'opencv-python'),
            ('httpx', 'httpx'),
            ('numpy', 'numpy')
        ]
        
        for import_name, package_name in deps_to_check:
            try:
                __import__(import_name)
                self.stdout.write(f'✅ {package_name}')
            except ImportError:
                missing.append(package_name)
                self.stdout.write(f'❌ {package_name}')
        
        return missing
    
    def _check_services_status(self):
        """Проверяет статус AI сервисов"""
        self.stdout.write(
            self.style.HTTP_INFO('🔍 Проверяем AI сервисы...')
        )
        
        # Проверяем импорт сервисов
        try:
            from services.ai.voice_recognition.whisper_service import whisper_service
            self.stdout.write('✅ WhisperService импортирован')
            
            status = whisper_service.get_service_status()
            if status.get('whisper_installed'):
                self.stdout.write('✅ Whisper CLI доступен')
            else:
                self.stdout.write('⚠️ Whisper CLI недоступен')
                
        except ImportError as e:
            self.stdout.write(f'❌ WhisperService: {e}')
        
        try:
            from services.ai.ocr.easyocr_service import easyocr_service
            self.stdout.write('✅ EasyOCRService импортирован')
            
            status = easyocr_service.get_service_status()
            if status.get('easyocr_available'):
                self.stdout.write('✅ EasyOCR доступен')
            else:
                self.stdout.write('⚠️ EasyOCR недоступен')
                
        except ImportError as e:
            self.stdout.write(f'❌ EasyOCRService: {e}')
        
        try:
            from services.ai.text_processing.nlp_service import nlp_service
            self.stdout.write('✅ NLPService импортирован')
            
            status = nlp_service.get_service_status()
            self.stdout.write(f'✅ NLP: {len(status.get("expense_categories", []))} категорий расходов')
            
        except ImportError as e:
            self.stdout.write(f'❌ NLPService: {e}')
        
        try:
            from services.currency_service import currency_service
            self.stdout.write('✅ CurrencyService импортирован')
            
        except ImportError as e:
            self.stdout.write(f'❌ CurrencyService: {e}')
        
        self.stdout.write('')
        self.stdout.write(
            self.style.SUCCESS('🎉 Проверка AI сервисов завершена!')
        )
    
    def _show_installation_instructions(self):
        """Показывает инструкции по установке"""
        self.stdout.write(
            self.style.HTTP_INFO('📦 УСТАНОВКА ЗАВИСИМОСТЕЙ ДЛЯ AI СЕРВИСОВ')
        )
        self.stdout.write('=' * 50)
        
        self.stdout.write('1. Обновите pip:')
        self.stdout.write('   pip install --upgrade pip')
        self.stdout.write('')
        
        self.stdout.write('2. Установите все зависимости:')
        self.stdout.write('   pip install -r requirements.txt')
        self.stdout.write('')
        
        self.stdout.write('3. Для работы с видео/аудио установите ffmpeg:')
        self.stdout.write('   # macOS:')
        self.stdout.write('   brew install ffmpeg')
        self.stdout.write('')
        self.stdout.write('   # Ubuntu/Debian:')
        self.stdout.write('   sudo apt update && sudo apt install ffmpeg')
        self.stdout.write('')
        
        self.stdout.write('4. Проверьте установку:')
        self.stdout.write('   python manage.py init_ai_services --check-only')
        self.stdout.write('')
        
        self.stdout.write(
            self.style.WARNING('⚠️ СИСТЕМНЫЕ ТРЕБОВАНИЯ:')
        )
        self.stdout.write('- Python 3.8+')
        self.stdout.write('- 4GB+ RAM')
        self.stdout.write('- 2GB+ свободного места')
        self.stdout.write('- ffmpeg для обработки аудио/видео')
        self.stdout.write('')
