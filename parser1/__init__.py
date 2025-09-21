#!/usr/bin/env python3
"""
Parser1 - Система обработки файлов из step4_links.txt
Скачивает файлы через парсеры APKCombo и APKPure и обновляет базу данных
"""

__version__ = "1.0.0"
__author__ = "Evgenrzz"

# Экспортируем основные классы для удобного импорта
try:
    # Сначала пробуем импортировать config (не требует внешних зависимостей)
    from .config import DB_CONFIG, LINKS_FILE, BASE_DOWNLOAD_DIR
    
    # Затем пробуем импортировать остальные модули
    from .main import FileProcessor
    from .database import DatabaseManager
    from .version_extractor import VersionExtractor
    
    __all__ = [
        'FileProcessor',
        'DatabaseManager', 
        'VersionExtractor',
        'DB_CONFIG',
        'LINKS_FILE',
        'BASE_DOWNLOAD_DIR'
    ]
except ImportError as e:
    # Если есть проблемы с зависимостями, экспортируем только config
    try:
        from .config import DB_CONFIG, LINKS_FILE, BASE_DOWNLOAD_DIR
        __all__ = ['DB_CONFIG', 'LINKS_FILE', 'BASE_DOWNLOAD_DIR']
    except ImportError:
        __all__ = []
    
    print(f"⚠️ Предупреждение: Не удалось импортировать все модули parser1: {e}")
    print("💡 Установите зависимости: pip install -r parser1/requirements.txt")
