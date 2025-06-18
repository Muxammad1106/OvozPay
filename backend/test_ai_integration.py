#!/usr/bin/env python
"""
Комплексный тест AI интеграции OvozPay
Тестирует Tesseract OCR, Whisper Voice и Receipt-Voice Matching
"""

import os
import sys
import django
import tempfile
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

# Настройка Django
sys.path.append(os.path.dirname(__file__))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.core.files.uploadedfile import SimpleUploadedFile
from apps.users.models import User
from apps.ai.services.ocr.tesseract_service import TesseractOCRService
from apps.ai.services.voice.whisper_service import WhisperVoiceService
from apps.ai.services.nlp.receipt_matcher import ReceiptVoiceMatcher


def create_test_receipt_image():
    """Создает тестовое изображение чека"""
    # Создаем изображение чека
    width, height = 400, 600
    image = Image.new('RGB', (width, height), 'white')
    draw = ImageDraw.Draw(image)
    
    # Пытаемся использовать системный шрифт
    try:
        font = ImageFont.truetype("/System/Library/Fonts/Arial.ttf", 16)
        title_font = ImageFont.truetype("/System/Library/Fonts/Arial.ttf", 20)
    except:
        # Если не найден, используем стандартный
        font = ImageFont.load_default()
        title_font = ImageFont.load_default()
    
    # Заголовок магазина
    draw.text((20, 20), "МАКРО СУПЕРМАРКЕТ", fill='black', font=title_font)
    draw.text((20, 50), "ул. Амира Темура, 123", fill='black', font=font)
    draw.text((20, 70), "Ташкент, Узбекистан", fill='black', font=font)
    
    # Линия разделитель
    draw.line([(20, 100), (380, 100)], fill='black', width=2)
    
    # Товары
    y_pos = 120
    items = [
        ("ХЛЕБ БЕЛЫЙ", "1", "5000", "5000"),
        ("МОЛОКО 1Л", "2", "8000", "16000"),
        ("ЯЙЦА 10ШТ", "1", "12000", "12000"),
        ("МАСЛО ПОДСОЛН", "1", "15000", "15000"),
        ("САХАР 1КГ", "1", "10000", "10000"),
    ]
    
    draw.text((20, y_pos), "НАИМЕНОВАНИЕ", fill='black', font=font)
    draw.text((220, y_pos), "КОЛ", fill='black', font=font)
    draw.text((260, y_pos), "ЦЕНА", fill='black', font=font)
    draw.text((320, y_pos), "СУММА", fill='black', font=font)
    
    y_pos += 25
    draw.line([(20, y_pos), (380, y_pos)], fill='black', width=1)
    y_pos += 10
    
    total = 0
    for name, qty, price, amount in items:
        draw.text((20, y_pos), name, fill='black', font=font)
        draw.text((220, y_pos), qty, fill='black', font=font)
        draw.text((260, y_pos), price, fill='black', font=font)
        draw.text((320, y_pos), amount, fill='black', font=font)
        total += int(amount)
        y_pos += 20
    
    # Итого
    y_pos += 20
    draw.line([(20, y_pos), (380, y_pos)], fill='black', width=2)
    y_pos += 15
    draw.text((200, y_pos), f"ИТОГО: {total} СУМ", fill='black', font=title_font)
    
    # Дата и время
    y_pos += 40
    draw.text((20, y_pos), "Дата: 15.01.2024", fill='black', font=font)
    draw.text((20, y_pos + 20), "Время: 14:30:25", fill='black', font=font)
    draw.text((20, y_pos + 40), "Чек №: 123456789", fill='black', font=font)
    
    return image


def create_test_audio_file():
    """Создает тестовый аудио файл (заглушка)"""
    # В реальном тесте здесь был бы настоящий аудио файл
    # Для демо создаем пустой файл
    with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as f:
        # Записываем минимальный WAV заголовок
        f.write(b'RIFF')
        f.write((36).to_bytes(4, 'little'))  # Размер файла - 8
        f.write(b'WAVE')
        f.write(b'fmt ')
        f.write((16).to_bytes(4, 'little'))  # Размер fmt чанка
        f.write((1).to_bytes(2, 'little'))   # Аудио формат (PCM)
        f.write((1).to_bytes(2, 'little'))   # Количество каналов
        f.write((16000).to_bytes(4, 'little'))  # Частота дискретизации
        f.write((32000).to_bytes(4, 'little'))  # Байт в секунду
        f.write((2).to_bytes(2, 'little'))   # Блок выравнивания
        f.write((16).to_bytes(2, 'little'))  # Бит на семпл
        f.write(b'data')
        f.write((0).to_bytes(4, 'little'))   # Размер данных
        return f.name


def test_ocr_service():
    """Тестирует OCR сервис"""
    print("🔍 ТЕСТИРОВАНИЕ OCR СЕРВИСА")
    print("=" * 50)
    
    try:
        # Создаем тестовое изображение
        test_image = create_test_receipt_image()
        
        # Сохраняем в временный файл
        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as temp_file:
            test_image.save(temp_file.name, 'PNG')
            temp_path = temp_file.name
        
        # Создаем Django файл
        with open(temp_path, 'rb') as f:
            image_file = SimpleUploadedFile(
                name='test_receipt.png',
                content=f.read(),
                content_type='image/png'
            )
        
        # Создаем тестового пользователя
        user, created = User.objects.get_or_create(
            username='test_user_ocr',
            defaults={
                'telegram_id': 12345,
                'first_name': 'Test',
                'last_name': 'User'
            }
        )
        
        # Инициализируем OCR сервис
        ocr_service = TesseractOCRService()
        
        # Проверяем статус сервиса
        status = ocr_service.get_processing_status()
        print(f"📊 Статус OCR сервиса:")
        print(f"   ✅ Tesseract доступен: {status.get('tesseract_available', False)}")
        print(f"   🗣️ Языки: {', '.join(status.get('supported_languages', []))}")
        print(f"   ⚙️ Конфигурация: {status.get('language_config', 'N/A')}")
        
        # Обрабатываем изображение
        print(f"\n🔄 Обрабатываем тестовое изображение чека...")
        
        ocr_result = ocr_service.process_receipt_image(
            user=user,
            image_file=image_file,
            recognition_type='receipt'
        )
        
        # Выводим результаты
        print(f"📋 РЕЗУЛЬТАТЫ OCR:")
        print(f"   🆔 ID результата: {ocr_result.id}")
        print(f"   📄 Статус: {ocr_result.status}")
        print(f"   🎯 Уверенность: {ocr_result.confidence_score:.2f}")
        print(f"   🏪 Магазин: {ocr_result.shop_name or 'Не определен'}")
        print(f"   💰 Общая сумма: {ocr_result.total_amount} сум")
        print(f"   📦 Количество товаров: {ocr_result.items_count}")
        print(f"   🗣️ Язык: {ocr_result.language_detected or 'Не определен'}")
        
        # Показываем товары
        if ocr_result.items.exists():
            print(f"\n🛍️ НАЙДЕННЫЕ ТОВАРЫ:")
            for item in ocr_result.items.all()[:5]:
                print(f"   • {item.name} - {item.total_price} сум (кол: {item.quantity})")
        
        # Показываем сырой текст (первые 200 символов)
        if ocr_result.raw_text:
            print(f"\n📄 Распознанный текст (первые 200 символов):")
            print(f"   {ocr_result.raw_text[:200]}...")
        
        # Очищаем временный файл
        os.unlink(temp_path)
        
        return ocr_result
        
    except Exception as e:
        print(f"❌ Ошибка тестирования OCR: {e}")
        import traceback
        traceback.print_exc()
        return None


def test_voice_service():
    """Тестирует Voice сервис"""
    print("\n🎤 ТЕСТИРОВАНИЕ VOICE СЕРВИСА")
    print("=" * 50)
    
    try:
        # Инициализируем Voice сервис
        voice_service = WhisperVoiceService()
        
        # Проверяем статус сервиса
        status = voice_service.get_processing_status()
        print(f"📊 Статус Voice сервиса:")
        print(f"   ✅ Whisper доступен: {status.get('whisper_available', False)}")
        print(f"   🤖 Текущая модель: {status.get('current_model', 'N/A')}")
        print(f"   📂 Поддерживаемые форматы: {', '.join(status.get('supported_formats', []))}")
        print(f"   🎯 Модель загружена: {status.get('model_loaded', False)}")
        
        # Получаем поддерживаемые языки
        languages = voice_service.get_supported_languages()
        print(f"   🗣️ Поддерживаемые языки: {len(languages)} (ru, uz, en, ...)")
        
        # Получаем доступные модели
        models = voice_service.get_available_models()
        print(f"   📦 Доступные модели: {', '.join(models.keys())}")
        
        # Создаем тестовый аудио файл
        test_audio_path = create_test_audio_file()
        
        # Создаем Django файл
        with open(test_audio_path, 'rb') as f:
            audio_file = SimpleUploadedFile(
                name='test_voice.wav',
                content=f.read(),
                content_type='audio/wav'
            )
        
        # Создаем тестового пользователя
        user, created = User.objects.get_or_create(
            username='test_user_voice',
            defaults={
                'telegram_id': 12346,
                'first_name': 'Voice',
                'last_name': 'User'
            }
        )
        
        # Проверяем валидацию аудио
        is_valid, error = voice_service.validate_audio_file(audio_file)
        print(f"\n🔍 Валидация аудио файла:")
        print(f"   ✅ Файл валиден: {is_valid}")
        if not is_valid:
            print(f"   ❌ Ошибка: {error}")
        
        # В режиме демо (без реального аудио) тестируем demo режим
        print(f"\n🔄 Тестируем demo режим распознавания...")
        
        try:
            voice_result = voice_service.recognize_voice(
                user=user,
                audio_file=audio_file,
                language='ru',
                task='transcribe'
            )
            
            # Выводим результаты
            print(f"📋 РЕЗУЛЬТАТЫ VOICE:")
            print(f"   🆔 ID результата: {voice_result.id}")
            print(f"   📄 Статус: {voice_result.status}")
            print(f"   🎯 Уверенность: {voice_result.confidence_score:.2f}")
            print(f"   📝 Распознанный текст: {voice_result.recognized_text[:100]}...")
            print(f"   🗣️ Обнаруженный язык: {voice_result.detected_language}")
            print(f"   📊 Сегментов: {voice_result.segments_count}")
            print(f"   📁 Формат аудио: {voice_result.audio_format}")
            print(f"   💾 Размер аудио: {voice_result.audio_size} байт")
            
            # Показываем метаданные
            if voice_result.processing_metadata:
                metadata = voice_result.processing_metadata
                print(f"\n📊 Метаданные обработки:")
                for key, value in metadata.items():
                    print(f"   {key}: {value}")
            
            return voice_result
            
        except Exception as e:
            print(f"❌ Ошибка распознавания (ожидаемо для demo): {e}")
            return None
        
        finally:
            # Очищаем временный файл
            os.unlink(test_audio_path)
        
    except Exception as e:
        print(f"❌ Ошибка тестирования Voice: {e}")
        import traceback
        traceback.print_exc()
        return None


def test_receipt_matching(ocr_result, voice_result):
    """Тестирует сопоставление чека с голосом"""
    print("\n🎯 ТЕСТИРОВАНИЕ СОПОСТАВЛЕНИЯ")
    print("=" * 50)
    
    try:
        # Инициализируем сервис сопоставления
        matcher = ReceiptVoiceMatcher()
        
        # Проверяем статус сервиса
        status = matcher.get_processing_status()
        print(f"📊 Статус сервиса сопоставления:")
        print(f"   ⏰ Макс разница времени: {status.get('max_time_diff_minutes', 5)} мин")
        print(f"   🎯 Порог схожести: {status.get('similarity_threshold', 0.6)}")
        print(f"   📝 Ключевые слова товаров: {len(status.get('item_keywords', {}))} языков")
        print(f"   💰 Ключевые слова сумм: {len(status.get('amount_keywords', {}))} языков")
        
        if not ocr_result or not voice_result:
            print("⚠️ Отсутствуют данные OCR или Voice для сопоставления")
            return None
        
        print(f"\n🔄 Выполняем сопоставление...")
        
        # Выполняем сопоставление
        match_result = matcher.match_voice_with_receipt(voice_result, ocr_result)
        
        if match_result:
            print(f"📋 РЕЗУЛЬТАТЫ СОПОСТАВЛЕНИЯ:")
            print(f"   🆔 ID сопоставления: {match_result.id}")
            print(f"   📄 Статус: {match_result.status}")
            print(f"   🎯 Общая уверенность: {match_result.confidence_score:.2f}")
            print(f"   🛍️ Сопоставлено товаров: {match_result.matched_items_count}")
            print(f"   ⏰ Разница во времени: {match_result.time_difference_minutes} мин")
            print(f"   💰 Сумма из голоса: {match_result.total_amount_voice} сум")
            print(f"   🧾 Сумма из чека: {match_result.total_amount_receipt} сум")
            print(f"   💯 Совпадение сумм: {match_result.amount_match_percentage:.1f}%")
            print(f"   📊 Высокая уверенность: {'Да' if match_result.is_high_confidence else 'Нет'}")
            
            # Показываем сопоставленные товары
            if match_result.matched_items:
                print(f"\n🛍️ СОПОСТАВЛЕННЫЕ ТОВАРЫ:")
                for item in match_result.matched_items[:5]:
                    voice_item = item.get('voice_item', {})
                    receipt_item = item.get('receipt_item', {})
                    similarity = item.get('similarity', 0)
                    
                    print(f"   • Голос: '{voice_item.get('name', 'N/A')}' ↔ "
                          f"Чек: '{receipt_item.get('name', 'N/A')}' "
                          f"({similarity:.2f} схожесть)")
            
            # Показываем детали сопоставления
            if match_result.matching_details:
                details = match_result.matching_details
                print(f"\n📊 ДЕТАЛИ СОПОСТАВЛЕНИЯ:")
                for key, value in details.items():
                    if isinstance(value, (int, float)):
                        print(f"   {key}: {value:.3f}")
                    else:
                        print(f"   {key}: {value}")
            
            return match_result
        else:
            print("❌ Сопоставление не удалось")
            return None
        
    except Exception as e:
        print(f"❌ Ошибка тестирования сопоставления: {e}")
        import traceback
        traceback.print_exc()
        return None


def test_auto_matching():
    """Тестирует автоматическое сопоставление"""
    print("\n🤖 ТЕСТИРОВАНИЕ АВТОМАТИЧЕСКОГО СОПОСТАВЛЕНИЯ")
    print("=" * 50)
    
    try:
        # Создаем тестового пользователя
        user, created = User.objects.get_or_create(
            username='test_user_auto',
            defaults={
                'telegram_id': 12347,
                'first_name': 'Auto',
                'last_name': 'User'
            }
        )
        
        # Инициализируем сервис сопоставления
        matcher = ReceiptVoiceMatcher()
        
        # Ищем недавние голосовые результаты пользователя
        from apps.ai.models import VoiceResult
        recent_voice = VoiceResult.objects.filter(user=user).first()
        
        if recent_voice:
            print(f"🔍 Найдено голосовое сообщение для автосопоставления...")
            
            # Выполняем автосопоставление
            matches = matcher.auto_match_recent_receipts(recent_voice)
            
            print(f"📊 Результаты автосопоставления:")
            print(f"   📈 Найдено совпадений: {len(matches)}")
            
            for i, match in enumerate(matches[:3], 1):
                print(f"   {i}. Уверенность: {match.confidence_score:.2f}, "
                      f"Товаров: {match.matched_items_count}, "
                      f"Время: {match.time_difference_minutes} мин")
        else:
            print("ℹ️ Нет данных для автосопоставления")
        
    except Exception as e:
        print(f"❌ Ошибка автосопоставления: {e}")
        import traceback
        traceback.print_exc()


def main():
    """Главная функция тестирования"""
    print("🚀 КОМПЛЕКСНОЕ ТЕСТИРОВАНИЕ AI ИНТЕГРАЦИИ OVOZPAY")
    print("=" * 60)
    print("Тестируем: Tesseract OCR + Whisper Voice + Receipt Matching")
    print("=" * 60)
    
    # Тестируем OCR
    ocr_result = test_ocr_service()
    
    # Тестируем Voice
    voice_result = test_voice_service()
    
    # Тестируем сопоставление
    if ocr_result and voice_result:
        match_result = test_receipt_matching(ocr_result, voice_result)
    else:
        print("\n⚠️ Пропускаем тест сопоставления из-за отсутствия данных")
        match_result = None
    
    # Тестируем автосопоставление
    test_auto_matching()
    
    # Финальный отчет
    print("\n" + "=" * 60)
    print("📊 ФИНАЛЬНЫЙ ОТЧЕТ ТЕСТИРОВАНИЯ")
    print("=" * 60)
    
    print(f"✅ OCR сервис: {'Работает' if ocr_result else 'Ошибка'}")
    print(f"✅ Voice сервис: {'Работает' if voice_result else 'Ошибка'}")
    print(f"✅ Сопоставление: {'Работает' if match_result else 'Не протестировано'}")
    
    if ocr_result:
        print(f"📄 OCR: {ocr_result.items_count} товаров, {ocr_result.total_amount} сум")
    
    if voice_result:
        print(f"🎤 Voice: {len(voice_result.recognized_text)} символов, {voice_result.detected_language}")
    
    if match_result:
        print(f"🎯 Match: {match_result.confidence_score:.2f} уверенность, {match_result.matched_items_count} товаров")
    
    print("\n🎉 Тестирование завершено!")
    print("💡 Для производственного использования:")
    print("   • Загрузите реальные аудио файлы для тестирования Whisper")
    print("   • Проверьте качество изображений чеков")
    print("   • Настройте пороги уверенности для продакшена")


if __name__ == '__main__':
    main() 