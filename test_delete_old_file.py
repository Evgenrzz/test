#!/usr/bin/env python3
"""
Тестовый скрипт для проверки удаления старых файлов
"""
import sys
from pathlib import Path

# Добавляем текущую папку в путь для импорта
sys.path.insert(0, str(Path(__file__).parent))

from parser1.database import DatabaseManager

def test_delete_old_file():
    """Тестируем удаление старого файла"""
    print("🧪 Тестируем удаление старого файла...")
    
    db = DatabaseManager()
    
    # Подключаемся к базе данных
    if not db.connect():
        print("❌ Не удалось подключиться к базе данных")
        return
    
    try:
        # Тестируем на новости 293 (Stumble Guys)
        news_id = 293
        print(f"🔍 Проверяем новость ID: {news_id}")
        
        # Показываем текущее состояние
        cursor = db.connection.cursor()
        
        # Получаем поле apk-original
        select_query = "SELECT xfields FROM dle_post WHERE id = %s"
        cursor.execute(select_query, (news_id,))
        result = cursor.fetchone()
        
        if result:
            xfields = result[0]
            print(f"📄 Текущее поле apk-original: {xfields}")
            
            # Извлекаем attachment ID
            import re
            old_attachment_match = re.search(r'apk-original\|\[attachment=(\d+):', xfields)
            if old_attachment_match:
                old_file_id = int(old_attachment_match.group(1))
                print(f"🔍 Найден attachment ID: {old_file_id}")
                
                # Получаем информацию о файле
                file_query = "SELECT onserver, driver, name FROM dle_files WHERE id = %s"
                cursor.execute(file_query, (old_file_id,))
                file_result = cursor.fetchone()
                
                if file_result:
                    onserver, driver, filename = file_result
                    print(f"📁 Файл: {filename}")
                    print(f"🗂️ Путь в БД: {onserver}")
                    print(f"💾 Хранилище: {driver}")
                    
                    # Показываем полный путь
                    cursor2 = db.connection.cursor()
                    storage_query = "SELECT * FROM dle_storage WHERE id = %s"
                    cursor2.execute(storage_query, (driver,))
                    storage = cursor2.fetchone()
                    cursor2.close()
                    
                    if storage:
                        storage_path = storage[8]  # path из таблицы dle_storage
                        if not onserver.startswith('/files'):
                            onserver_with_prefix = f"/files/{onserver}"
                        else:
                            onserver_with_prefix = onserver
                        full_path = f"{storage_path}{onserver_with_prefix}".replace('//', '/')
                        print(f"🗂️ Полный путь: {full_path}")
                else:
                    print("❌ Файл не найден в dle_files")
            else:
                print("ℹ️ Attachment не найден в поле apk-original")
        else:
            print("❌ Новость не найдена")
        
        cursor.close()
        
        # Спрашиваем пользователя
        print("\n❓ Хотите удалить старый файл? (y/n): ", end="")
        choice = input().lower()
        
        if choice == 'y':
            print("\n🗑️ Удаляем старый файл...")
            success = db.delete_old_file_from_apk_original(news_id)
            if success:
                print("✅ Старый файл успешно удален!")
            else:
                print("❌ Не удалось удалить старый файл")
        else:
            print("⏭️ Удаление отменено")
    
    finally:
        db.disconnect()

if __name__ == "__main__":
    test_delete_old_file()
