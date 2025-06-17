from django.conf import settings

def translated_fields(lang, instance, translation_options):
    """
    Возвращает переведенные поля для указанного языка
    
    Args:
        lang (str): Код языка (например, 'uz', 'ru', 'en')
        instance: Экземпляр модели
        translation_options: Класс с настройками перевода (TranslationOptions)
    
    Returns:
        dict: Словарь с переведенными полями
    """
    result = {}
    if not hasattr(translation_options, 'fields'):
        return result
        
    # Если указанного языка нет в настройках, используем язык по умолчанию
    if lang not in [code for code, name in settings.LANGUAGES]:
        lang = settings.LANGUAGE_CODE.split('-')[0]
    
    for field in translation_options.fields:
        field_name = f"{field}_{lang}"
        if hasattr(instance, field_name):
            result[field] = getattr(instance, field_name) or getattr(instance, field)
        else:
            result[field] = getattr(instance, field)
            
    return result
