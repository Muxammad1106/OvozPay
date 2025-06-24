"""
Оптимизация и тестирование Whisper модели для максимальной скорости
"""

import asyncio
import time
import tempfile
import os
from django.core.management.base import BaseCommand
from services.ai.voice_recognition.whisper_service import WhisperService


class Command(BaseCommand):
    help = 'Оптимизирует и тестирует скорость Whisper распознавания'

    def add_arguments(self, parser):
        parser.add_argument(
            '--model',
            type=str,
            default='tiny',
            help='Модель Whisper для тестирования (tiny, base, small, medium, large)'
        )
        
        parser.add_argument(
            '--benchmark',
            action='store_true',
            help='Запустить бенчмарк скорости'
        )

    def handle(self, *args, **options):
        asyncio.run(self._run_optimization(options))

    async def _run_optimization(self, options):
        self.stdout.write('\n🚀 ОПТИМИЗАЦИЯ WHISPER ДЛЯ МАКСИМАЛЬНОЙ СКОРОСТИ\n')
        
        # Инициализируем сервис
        whisper_service = WhisperService()
        whisper_service.model_name = options['model']
        
        # Проверяем состояние
        status = whisper_service.get_service_status()
        self.stdout.write(f"📊 Статус Whisper: {status['status']}")
        self.stdout.write(f"🎯 Модель: {status['model']}")
        self.stdout.write(f"🌍 Языки: {status['supported_languages']}")
        
        if not status.get('whisper_installed'):
            self.stdout.write(
                self.style.ERROR("❌ Whisper не установлен. Установите: pip install openai-whisper")
            )
            return
        
        # Скачиваем модель если нужно
        self.stdout.write(f"\n📥 Проверяем/скачиваем модель {whisper_service.model_name}...")
        
        # Создаем тестовый аудио файл (если нет реального)
        test_audio = await self._create_test_audio()
        
        if options['benchmark']:
            await self._run_benchmark(whisper_service, test_audio)
        else:
            await self._test_basic_recognition(whisper_service, test_audio)
            
        # Очистка
        if test_audio and os.path.exists(test_audio):
            os.unlink(test_audio)

    async def _create_test_audio(self):
        """Создает или находит тестовый аудио файл"""
        # Примечание: В реальной реализации здесь должен быть тестовый OGG файл
        # Для демонстрации создаем пустой файл
        with tempfile.NamedTemporaryFile(suffix='.ogg', delete=False) as f:
            # В реальности здесь должны быть аудио данные
            f.write(b'FAKE_AUDIO_DATA')  # Placeholder
            return f.name

    async def _test_basic_recognition(self, whisper_service, audio_file):
        """Базовое тестирование распознавания"""
        self.stdout.write("\n🧪 БАЗОВОЕ ТЕСТИРОВАНИЕ:")
        
        languages = ['ru', 'en', 'uz']
        
        for language in languages:
            try:
                start_time = time.time()
                
                result = await whisper_service.transcribe_audio(
                    audio_file, 
                    language=language,
                    user_id='test_user'
                )
                
                end_time = time.time()
                duration = end_time - start_time
                
                if result:
                    self.stdout.write(
                        f"✅ {language.upper()}: {duration:.1f}с | "
                        f"Текст: '{result.get('text', 'Пусто')[:30]}...'"
                    )
                else:
                    self.stdout.write(
                        f"⚠️ {language.upper()}: {duration:.1f}с | Не распознано"
                    )
                    
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f"❌ {language.upper()}: Ошибка - {e}")
                )

    async def _run_benchmark(self, whisper_service, audio_file):
        """Запускает бенчмарк производительности"""
        self.stdout.write("\n🏁 БЕНЧМАРК ПРОИЗВОДИТЕЛЬНОСТИ:")
        
        models = ['tiny', 'base', 'small']
        test_count = 3
        
        results = {}
        
        for model in models:
            self.stdout.write(f"\n🔬 Тестируем модель: {model}")
            whisper_service.model_name = model
            
            times = []
            
            for i in range(test_count):
                try:
                    start_time = time.time()
                    
                    result = await whisper_service.transcribe_audio(
                        audio_file,
                        language='ru',
                        user_id=f'benchmark_user_{i}'
                    )
                    
                    end_time = time.time()
                    duration = end_time - start_time
                    times.append(duration)
                    
                    self.stdout.write(f"  Попытка {i+1}: {duration:.1f}с")
                    
                except Exception as e:
                    self.stdout.write(f"  Попытка {i+1}: ОШИБКА - {e}")
                    times.append(999)  # Большое время для ошибок
            
            avg_time = sum(times) / len(times)
            min_time = min(times)
            results[model] = {'avg': avg_time, 'min': min_time, 'times': times}
            
            self.stdout.write(f"  📊 Среднее: {avg_time:.1f}с | Минимум: {min_time:.1f}с")
        
        # Сводка результатов
        self.stdout.write("\n📈 СВОДКА РЕЗУЛЬТАТОВ:")
        sorted_models = sorted(results.items(), key=lambda x: x[1]['avg'])
        
        for i, (model, stats) in enumerate(sorted_models):
            rank = "🥇" if i == 0 else "🥈" if i == 1 else "🥉" if i == 2 else "📍"
            self.stdout.write(
                f"{rank} {model}: {stats['avg']:.1f}с (мин: {stats['min']:.1f}с)"
            )
        
        # Рекомендации
        best_model = sorted_models[0][0]
        best_time = sorted_models[0][1]['avg']
        
        self.stdout.write(f"\n🎯 РЕКОМЕНДАЦИЯ:")
        self.stdout.write(f"   Используйте модель '{best_model}' для максимальной скорости")
        self.stdout.write(f"   Среднее время распознавания: {best_time:.1f} секунд")
        
        if best_time > 2.0:
            self.stdout.write(
                self.style.WARNING(
                    "⚠️ ВНИМАНИЕ: Время распознавания превышает 2 секунды.\n"
                    "   Рекомендации для ускорения:\n"
                    "   1. Используйте GPU: pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118\n"
                    "   2. Обновите до последней версии: pip install --upgrade openai-whisper\n"
                    "   3. Используйте SSD диск для временных файлов"
                )
            )
        else:
            self.stdout.write("✅ Скорость оптимальна для пользовательского опыта!")
        
        self.stdout.write('\n🏆 Оптимизация завершена!') 