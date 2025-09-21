#!/usr/bin/env python3
"""
Модуль для работы с базой данных
"""
import time
import re
import mysql.connector
from mysql.connector import Error
from config import DB_CONFIG, CREATE_TRACKING_TABLE


class DatabaseManager:
    def __init__(self):
        self.connection = None

    def connect(self):
        """Подключение к базе данных"""
        try:
            self.connection = mysql.connector.connect(**DB_CONFIG)
            if self.connection.is_connected():
                print("✅ Подключение к базе данных установлено")

                # Создаем таблицу отслеживания если не существует
                cursor = self.connection.cursor()
                cursor.execute(CREATE_TRACKING_TABLE)
                self.connection.commit()
                cursor.close()

                return True
        except Error as e:
            print(f"❌ Ошибка подключения к базе данных: {e}")
            return False

    def disconnect(self):
        """Отключение от базы данных"""
        if self.connection and self.connection.is_connected():
            self.connection.close()
            print("🔒 Соединение с базой данных закрыто")

    def check_if_update_needed(self, news_id, app_name, current_version):
        """Проверяем нужно ли обновлять файл"""
        try:
            cursor = self.connection.cursor()
            query = """
            SELECT version, file_size, checksum, file_path
            FROM file_tracking
            WHERE news_id = %s AND app_name = %s
            ORDER BY last_updated DESC LIMIT 1
            """
            cursor.execute(query, (news_id, app_name))
            result = cursor.fetchone()
            cursor.close()

            if not result:
                print(f"📝 Новое приложение {app_name} для новости {news_id}")
                return True, None

            stored_version = result[0]
            if stored_version != current_version:
                print(f"🔄 Обновление нужно: {stored_version} -> {current_version}")
                return True, result
            else:
                print(f"✅ Версия {current_version} уже актуальна")
                return False, result

        except Error as e:
            print(f"❌ Ошибка проверки версии: {e}")
            return True, None

    def add_to_dle_files(self, news_id, app_name, version, file_extension, downloaded_filename, file_size, checksum, download_dir):
        """Добавляем запись в таблицу dle_files"""
        try:
            cursor = self.connection.cursor()

            # Формируем читаемое имя файла для поля name
            # Переводим кириллицу в латиницу
            readable_name = self._transliterate_cyrillic(app_name)
            readable_filename = f"{readable_name} {version}{file_extension}"
            
            print(f"📝 Формируем читаемое имя для dle_files.name: {readable_filename}")

            # Для onserver используем точно такое же имя как у загруженного файла
            # Убираем расширение из downloaded_filename и добавляем timestamp
            downloaded_name_without_ext = downloaded_filename.replace(file_extension, '')
            
            # Генерируем уникальное имя файла на сервере
            timestamp = str(int(time.time()))
            server_filename = f"{timestamp[:8]}_{downloaded_filename}"

            # Относительный путь для базы данных
            relative_path = f"{download_dir.name}/{server_filename}"
            
            print(f"🗂️ Имя файла на сервере (onserver): {server_filename}")

            insert_query = """
            INSERT INTO dle_files (news_id, name, onserver, author, date, dcount, size, checksum, driver, is_public)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """

            values = (
                news_id,
                readable_filename,  # Читаемое имя в поле name
                relative_path,      # Путь с именем загруженного файла в поле onserver
                'app4ok',
                timestamp,
                0,
                file_size,
                checksum,
                2,
                0
            )

            cursor.execute(insert_query, values)
            file_id = cursor.lastrowid
            self.connection.commit()
            cursor.close()

            print(f"✅ Файл добавлен в dle_files с ID: {file_id}")
            print(f"📁 name: {readable_filename}")
            print(f"🗂️ onserver: {relative_path}")
            return file_id

        except Error as e:
            print(f"❌ Ошибка добавления в dle_files: {e}")
            return None

    def update_dle_post(self, news_id, file_id, app_name, version, file_extension):
        """Обновляем поле apk-original в таблице dle_post"""
        try:
            cursor = self.connection.cursor()

            # Получаем текущие xfields
            select_query = "SELECT xfields FROM dle_post WHERE id = %s"
            cursor.execute(select_query, (news_id,))
            result = cursor.fetchone()

            if not result:
                print(f"❌ Новость с ID {news_id} не найдена")
                return False

            xfields = result[0]

            # Формируем читаемое имя файла для attachment (такое же как в dle_files.name)
            # Переводим кириллицу в латиницу
            readable_name = self._transliterate_cyrillic(app_name)
            
            # Формируем финальное имя: "app_name version.extension"
            readable_filename = f"{readable_name} {version}{file_extension}"
            
            print(f"📝 Формируем читаемое имя для attachment: {readable_filename}")

            # Обновляем поле apk-original
            new_attachment = f"[attachment={file_id}:{readable_filename}]"

            # Ищем и заменяем существующее поле apk-original
            pattern = r'apk-original\|[^|]*\|\|'
            replacement = f'apk-original|{new_attachment}||'

            if re.search(pattern, xfields):
                new_xfields = re.sub(pattern, replacement, xfields)
            else:
                # Если поля нет, добавляем в конец
                new_xfields = xfields + f'||apk-original|{new_attachment}||'

            # Обновляем запись
            update_query = "UPDATE dle_post SET xfields = %s WHERE id = %s"
            cursor.execute(update_query, (new_xfields, news_id))
            self.connection.commit()
            cursor.close()

            print(f"✅ Обновлено поле apk-original для новости {news_id}: {new_attachment}")
            return True

        except Error as e:
            print(f"❌ Ошибка обновления dle_post: {e}")
            return False

    def _transliterate_cyrillic(self, text):
        """Переводим кириллицу в латиницу"""
        cyrillic_to_latin = {
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
        
        result = ""
        for char in text:
            if char in cyrillic_to_latin:
                result += cyrillic_to_latin[char]
            elif char == '+':
                result += ' '  # Заменяем + на пробелы
            else:
                result += char
        
        # Убираем множественные пробелы
        result = re.sub(r'\s+', ' ', result).strip()
        
        return result

    def add_to_tracking(self, news_id, app_name, version, file_size, file_path, checksum, source_url):
        """Добавляем запись в таблицу отслеживания"""
        try:
            cursor = self.connection.cursor()

            insert_query = """
            INSERT INTO file_tracking (news_id, app_name, version, file_size, file_path, checksum, source_url)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            """

            # В version записываем ТОЛЬКО версию, без названия приложения
            values = (news_id, app_name, version, file_size, str(file_path), checksum, source_url)

            cursor.execute(insert_query, values)
            self.connection.commit()
            cursor.close()

            print(f"✅ Добавлена запись в таблицу отслеживания:")
            print(f"   app_name: {app_name}")
            print(f"   version: {version}")
            return True

        except Error as e:
            print(f"❌ Ошибка добавления в tracking: {e}")
            return False

