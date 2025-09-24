#!/usr/bin/env python3
"""
Утилиты для работы с версиями для parser2
Специализирован для работы с модифицированными приложениями
"""
import re
from packaging import version


class VersionUtils:
    """Утилиты для работы с версиями"""
    
    @staticmethod
    def extract_version_from_filename(filename):
        """Извлекаем версию из имени файла"""
        # Убираем расширение
        name_without_ext = filename.rsplit('.', 1)[0]
        
        # Паттерны для поиска версии
        patterns = [
            r'(\d+\.\d+\.\d+\.\d+)',  # 1.2.3.4
            r'(\d+\.\d+\.\d+)',       # 1.2.3
            r'(\d+\.\d+)',            # 1.2
            r'(\d+)',                 # 1
            r'v(\d+\.\d+\.\d+)',      # v1.2.3
            r'v(\d+\.\d+)',           # v1.2
            r'v(\d+)',                # v1
        ]
        
        for pattern in patterns:
            match = re.search(pattern, name_without_ext, re.IGNORECASE)
            if match:
                return match.group(1)
        
        return None
    
    @staticmethod
    def extract_app_name_from_filename(filename):
        """Извлекаем название приложения из имени файла"""
        # Убираем расширение
        name_without_ext = filename.rsplit('.', 1)[0]
        
        # Убираем версию
        version_patterns = [
            r'(\d+\.\d+\.\d+\.\d+)',  # 1.2.3.4
            r'(\d+\.\d+\.\d+)',       # 1.2.3
            r'(\d+\.\d+)',            # 1.2
            r'(\d+)',                 # 1
            r'v(\d+\.\d+\.\d+)',      # v1.2.3
            r'v(\d+\.\d+)',           # v1.2
            r'v(\d+)',                # v1
        ]
        
        app_name = name_without_ext
        for pattern in version_patterns:
            app_name = re.sub(pattern, '', app_name, flags=re.IGNORECASE)
        
        # Убираем префиксы модов
        mod_prefixes = ['MOD', 'mod', 'Mod', 'MODDED', 'modded', 'Modded']
        for prefix in mod_prefixes:
            app_name = app_name.replace(prefix, '').strip()
        
        # Убираем суффиксы модов
        mod_suffixes = ['-mod', '-modded', '-hack', '-premium', '-unlocked', '-pro']
        for suffix in mod_suffixes:
            app_name = app_name.replace(suffix, '').strip()
        
        # Убираем лишние символы
        app_name = re.sub(r'[_\-\.]+', ' ', app_name).strip()
        app_name = re.sub(r'\s+', ' ', app_name)
        
        return app_name if app_name else "Unknown App"
    
    @staticmethod
    def extract_package_name_from_url(url):
        """Извлекаем package name из URL"""
        if 'liteapks.com' in url:
            # Извлекаем из URL вида https://liteapks.com/app-name/
            match = re.search(r'liteapks\.com/([^/]+)/?', url)
            if match:
                return match.group(1)
        
        return None
    
    @staticmethod
    def get_source_priority(url):
        """Определяем приоритет источника"""
        if 'liteapks.com' in url:
            return 60  # Высокий приоритет для модифицированных приложений
        
        return 10  # Низкий приоритет по умолчанию
    
    @staticmethod
    def compare_versions(version1, version2):
        """Сравнивает две версии"""
        if not version1 or not version2:
            return 0
        
        try:
            v1 = version.parse(version1)
            v2 = version.parse(version2)
            
            if v1 > v2:
                return 1
            elif v1 < v2:
                return -1
            else:
                return 0
        except:
            # Если не удалось распарсить, сравниваем как строки
            if version1 > version2:
                return 1
            elif version1 < version2:
                return -1
            else:
                return 0
    
    @staticmethod
    def extract_clean_version(version_string):
        """Извлекаем чистую версию из строки"""
        if not version_string:
            return None
        
        # Паттерны для поиска версии
        patterns = [
            r'(\d+\.\d+\.\d+\.\d+)',  # 1.2.3.4
            r'(\d+\.\d+\.\d+)',       # 1.2.3
            r'(\d+\.\d+)',            # 1.2
            r'(\d+)',                 # 1
        ]
        
        for pattern in patterns:
            match = re.search(pattern, str(version_string))
            if match:
                return match.group(1)
        
        return None
    
    @staticmethod
    def fuzzy_match_app_names(name1, name2, threshold=0.8):
        """Fuzzy matching названий приложений"""
        if not name1 or not name2:
            return False
        
        # Нормализуем названия
        name1_norm = re.sub(r'[^\w\s]', '', name1.lower()).strip()
        name2_norm = re.sub(r'[^\w\s]', '', name2.lower()).strip()
        
        # Разбиваем на слова
        words1 = set(name1_norm.split())
        words2 = set(name2_norm.split())
        
        if not words1 or not words2:
            return False
        
        # Вычисляем коэффициент схожести
        intersection = len(words1.intersection(words2))
        union = len(words1.union(words2))
        
        similarity = intersection / union if union > 0 else 0
        
        return similarity >= threshold
    
    @staticmethod
    def detect_mod_type(filename, app_name):
        """Определяем тип модификации по имени файла и приложению"""
        text = f"{filename} {app_name}".lower()
        
        mod_types = {
            'premium': ['premium', 'pro', 'paid', 'unlocked'],
            'unlocked': ['unlocked', 'unlock', 'crack', 'cracked'],
            'hack': ['hack', 'hacked', 'cheat', 'cheats'],
            'mod': ['mod', 'modded', 'modified', 'modded apk']
        }
        
        detected_types = []
        for mod_type, keywords in mod_types.items():
            for keyword in keywords:
                if keyword in text:
                    detected_types.append(mod_type)
                    break
        
        return detected_types[0] if detected_types else 'mod'
    
    @staticmethod
    def extract_mod_features(text):
        """Извлекаем особенности модификации из текста"""
        features = []
        text_lower = text.lower()
        
        feature_keywords = {
            'no_ads': ['no ads', 'ad free', 'no advertisement'],
            'premium': ['premium', 'pro features', 'paid features'],
            'unlimited': ['unlimited', 'infinite', 'unlimited coins'],
            'speed_hack': ['speed hack', 'faster', 'speed mod'],
            'god_mode': ['god mode', 'invincible', 'immortal'],
            'unlock_all': ['unlock all', 'all unlocked', 'everything unlocked']
        }
        
        for feature, keywords in feature_keywords.items():
            for keyword in keywords:
                if keyword in text_lower:
                    features.append(feature)
                    break
        
        return features
