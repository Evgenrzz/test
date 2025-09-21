#!/usr/bin/env python3
"""
Модуль для нормализации имен файлов
Используется всеми парсерами для единообразной обработки имен файлов
"""
import os
import re


class FileNormalizer:
    """Класс для нормализации имен файлов"""
    
    @staticmethod
    def get_cyrillic_to_latin_map():
        """Возвращает словарь для транслитерации кириллицы в латиницу"""
        return {
            'а': 'a', 'б': 'b', 'в': 'v', 'г': 'g', 'д': 'd', 'е': 'e', 'ё': 'yo',
            'ж': 'zh', 'з': 'z', 'и': 'i', 'й': 'y', 'к': 'k', 'л': 'l', 'м': 'm',
            'н': 'n', 'о': 'o', 'п': 'p', 'р': 'r', 'с': 's', 'т': 't', 'у': 'u',
            'ф': 'f', 'х': 'h', 'ц': 'ts', 'ч': 'ch', 'ш': 'sh', 'щ': 'sch',
            'ъ': '', 'ы': 'y', 'ь': '', 'э': 'e', 'ю': 'yu', 'я': 'ya',
            'А': 'A', 'Б': 'B', 'В': 'V', 'Г': 'G', 'Д': 'D', 'Е': 'E', 'Ё': 'Yo',
            'Ж': 'Zh', 'З': 'Z', 'И': 'I', 'Й': 'Y', 'К': 'K', 'Л': 'L', 'М': 'M',
            'Н': 'N', 'О': 'O', 'П': 'P', 'Р': 'R', 'С': 'S', 'Т': 'T', 'У': 'U',
            'Ф': 'F', 'Х': 'H', 'Ц': 'Ts', 'Ч': 'Ch', 'Ш': 'Sh', 'Щ': 'Sch',
            'Ъ': '', 'Ы': 'Y', 'Ь': '', 'Э': 'E', 'Ю': 'Yu', 'Я': 'Ya'
        }
    
    @staticmethod
    def transliterate_cyrillic(text):
        """Переводим кириллицу в латиницу"""
        cyrillic_to_latin = FileNormalizer.get_cyrillic_to_latin_map()
        
        result = ""
        for char in text:
            if char in cyrillic_to_latin:
                result += cyrillic_to_latin[char]
            else:
                result += char
        
        return result
    
    @staticmethod
    def normalize_filename(filename):
        """Нормализуем имя файла согласно требованиям"""
        print(f"📝 Исходное имя файла: {filename}")

        # Убираем суффиксы источников
        filename = FileNormalizer.clean_source_suffixes(filename)

        # Разделяем имя файла и расширение
        name_part, extension = os.path.splitext(filename)

        # Приводим к нижнему регистру
        name_part = name_part.lower()
        extension = extension.lower()

        # Переводим кириллицу в латиницу
        name_part = FileNormalizer.transliterate_cyrillic(name_part)

        # Заменяем +-+ на подчеркивания
        name_part = name_part.replace('+-+', '_')
        name_part = name_part.replace('+', '_')
        name_part = name_part.replace('-', '_')

        # Заменяем пробелы на подчеркивания
        name_part = name_part.replace(' ', '_')

        # Заменяем точки на подчеркивания в имени файла (но не в расширении)
        name_part = name_part.replace('.', '_')

        # Убираем множественные подчеркивания
        name_part = re.sub(r'_+', '_', name_part).strip('_')

        # Собираем обратно с одной точкой перед расширением
        normalized_filename = f"{name_part}{extension}"

        print(f"📝 Нормализованное имя: {normalized_filename}")
        return normalized_filename
    
    @staticmethod
    def clean_source_suffixes(filename):
        """Убираем суффиксы источников из имени файла"""
        # Убираем суффиксы источников
        filename = filename.replace('_apkpure', '')
        filename = filename.replace('_apkcombo', '')
        filename = filename.replace('_apkcombo.com', '')
        
        return filename
    
    @staticmethod
    def format_filename_for_attachment(filename):
        """Форматируем имя файла для поля apk-original"""
        print(f"📝 Форматируем для attachment: {filename}")

        # Убираем суффиксы источников
        filename = FileNormalizer.clean_source_suffixes(filename)
        
        # Разделяем имя файла и расширение
        name_part, extension = os.path.splitext(filename)

        # Убираем подчеркивания и заменяем на пробелы
        name_part = name_part.replace('_', ' ')

        # Убираем лишние символы +-+
        name_part = name_part.replace('+-+', ' ')
        name_part = name_part.replace('+', ' ')
        name_part = name_part.replace('-', ' ')

        # Убираем множественные пробелы
        name_part = re.sub(r'\s+', ' ', name_part).strip()

        # Восстанавливаем точки в версии (ищем паттерны типа "1 8 3" и заменяем на "1.8.3")
        # Ищем последовательности цифр разделенных пробелами в конце строки
        version_pattern = r'(\d+)\s+(\d+)\s+(\d+)(?:\s+(\d+))?(?:\s+(\d+))?$'
        match = re.search(version_pattern, name_part)
        if match:
            # Заменяем найденную версию на правильный формат с точками
            version_parts = [part for part in match.groups() if part is not None]
            version_str = '.'.join(version_parts)
            name_part = re.sub(version_pattern, version_str, name_part)

        # Собираем обратно
        formatted_filename = f"{name_part}{extension}"

        print(f"📝 Отформатированное имя: {formatted_filename}")
        return formatted_filename
