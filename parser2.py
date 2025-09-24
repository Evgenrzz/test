#!/usr/bin/env python3
"""
Parser2 - Система обработки модифицированных приложений
Основной файл для запуска parser2
"""
import asyncio
import sys
import argparse
from pathlib import Path

# Добавляем путь к модулю parser2
sys.path.insert(0, str(Path(__file__).parent / "parser2"))

# Принудительная перезагрузка модулей для обновления на сервере
import importlib

# Удаляем parser2 модули из кэша
modules_to_remove = [name for name in sys.modules.keys() if name.startswith('parser2')]
for module_name in modules_to_remove:
    del sys.modules[module_name]
    print(f"🗑️ Удален из кэша: {module_name}")

from parser2.main import Parser2


async def main():
    """Главная функция"""
    parser = argparse.ArgumentParser(description='Parser2 - Система обработки модифицированных приложений')
    parser.add_argument('mode', nargs='?', default='fast', choices=['fast', 'full'], 
                       help='Режим работы: fast (быстрый) или full (полный)')
    parser.add_argument('--links-file', '-f', help='Файл с ссылками для обработки')
    parser.add_argument('--version', '-v', action='version', version='Parser2 v2.0.0')
    
    args = parser.parse_args()
    
    print(f"🚀 Запуск Parser2 v2.0 в режиме: {args.mode}")
    
    # Создаем экземпляр парсера
    parser2 = Parser2()
    
    # Запускаем обработку
    await parser2.run(args.links_file)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n⏹️ Остановка по запросу пользователя")
    except Exception as e:
        print(f"\n❌ Критическая ошибка: {e}")
        sys.exit(1)