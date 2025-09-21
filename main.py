#!/usr/bin/env python3
"""
Точка входа для запуска системы обработки файлов
Импортирует и запускает FileProcessor из пакета parser1
"""
import asyncio
import sys
from pathlib import Path

# Добавляем текущую папку в путь для импорта
sys.path.insert(0, str(Path(__file__).parent))

try:
    from parser1.main import FileProcessor
except ImportError as e:
    print(f"❌ Ошибка импорта: {e}")
    print("Убедитесь, что все зависимости установлены:")
    print("pip install -r parser1/requirements.txt")
    sys.exit(1)


async def main():
    """Главная функция"""
    print("🚀 Запуск системы обработки файлов")
    
    # Показываем доступные профили производительности
    print("\n📊 Доступные профили производительности:")
    print("   fast      - Максимальная скорость (overhead: 0.1-0.2 сек/файл)")
    print("   balanced  - Сбалансированный (overhead: 0.3-0.5 сек/файл) [РЕКОМЕНДУЕМЫЙ]")
    print("   accurate  - Максимальная точность (overhead: 0.5-1.0 сек/файл)")
    print("   debug     - Отладка (overhead: 0.5-1.0 сек/файл)")
    
    # Можно добавить выбор профиля через аргументы командной строки
    import sys
    profile = 'balanced'  # По умолчанию
    if len(sys.argv) > 1:
        profile = sys.argv[1]
    
    print(f"\n🎯 Используется профиль: {profile}")

    processor = FileProcessor()

    # Подключаемся к базе данных
    if not processor.db.connect():
        print("❌ Не удалось подключиться к базе данных")
        return

    try:
        # Обрабатываем файл со ссылками
        await processor.process_links_file()

    finally:
        # Отключаемся от базы данных
        processor.db.disconnect()

    print("🏁 Обработка завершена")


if __name__ == "__main__":
    asyncio.run(main())
