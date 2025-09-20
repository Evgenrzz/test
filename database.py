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

    def add_to_dle_files(self, news_id, filename, file_path, file_size, checksum, download_dir):
        """Добавляем запись в таблицу dle_files"""
        try:
            cursor = self.connection.cursor()

            # Генерируем уникальное имя файла на сервере
            timestamp = str(int(time.time()))
            server_filename = f"{timestamp[:8]}_{filename}"

            # Относительный путь для базы данных
            relative_path = f"{download_dir.name}/{server_filename}"

            insert_query = """
            INSERT INTO dle_files (news_id, name, onserver, author, date, dcount, size, checksum, driver, is_public)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """

            values = (
                news_id,
                filename,
                relative_path,
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
            return file_id

        except Error as e:
            print(f"❌ Ошибка добавления в dle_files: {e}")
            return None

    def update_dle_post(self, news_id, file_id, filename):
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

            # Обновляем поле apk-original
            new_attachment = f"[attachment={file_id}:{filename}]"

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

            print(f"✅ Обновлено поле apk-original для новости {news_id}")
            return True

        except Error as e:
            print(f"❌ Ошибка обновления dle_post: {e}")
            return False

    def add_to_tracking(self, news_id, app_name, version, file_size, file_path, checksum, source_url):
        """Добавляем запись в таблицу отслеживания"""
        try:
            cursor = self.connection.cursor()

            insert_query = """
            INSERT INTO file_tracking (news_id, app_name, version, file_size, file_path, checksum, source_url)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            """

            values = (news_id, app_name, version, file_size, str(file_path), checksum, source_url)

            cursor.execute(insert_query, values)
            self.connection.commit()
            cursor.close()

            print(f"✅ Добавлена запись в таблицу отслеживания с версией: {version}")
            return True

        except Error as e:
            print(f"❌ Ошибка добавления в tracking: {e}")
            return False

