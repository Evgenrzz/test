#!/usr/bin/env python3
"""
Модуль для работы с базой данных
"""
import time
import re
import mysql.connector
from mysql.connector import Error
from .config import DB_CONFIG, CREATE_TRACKING_TABLE, ENABLE_FUZZY_MATCHING, ENABLE_DETAILED_LOGGING
from .lib.version_utils import VersionUtils


class DatabaseManager:
    def __init__(self, analyzer=None):
        self.connection = None
        self.analyzer = analyzer
        self._similar_apps_cache = {}  # Кэш для fuzzy matching

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

    def check_if_update_needed(self, news_id, app_name, current_version, sha256_hash=None, package_name=None):
        """Проверяем нужно ли обновлять файл с улучшенной проверкой дублей"""
        try:
            cursor = self.connection.cursor()
            
            # Сначала проверяем по SHA-256 (самый надежный способ)
            if sha256_hash:
                sha256_query = """
                SELECT id, version, file_size, checksum, file_path, source_priority
                FROM file_tracking
                WHERE sha256_hash = %s
                ORDER BY source_priority DESC, last_updated DESC LIMIT 1
                """
                cursor.execute(sha256_query, (sha256_hash,))
                sha256_result = cursor.fetchone()
                if sha256_result:
                    print(f"🔍 Найден точный дубль по SHA-256: {sha256_result[1]}")
                    if self.analyzer:
                        self.analyzer.log_duplicate_found('sha256', sha256_result[1], sha256_result[2], 
                                                        'Точное совпадение содержимого файла')
                    cursor.close()
                    return False, sha256_result
            
            # Проверяем по package_name если есть
            if package_name:
                package_query = """
                SELECT id, version, file_size, checksum, file_path, source_priority
                FROM file_tracking
                WHERE package_name = %s AND version = %s
                ORDER BY source_priority DESC, last_updated DESC LIMIT 1
                """
                cursor.execute(package_query, (package_name, current_version))
                package_result = cursor.fetchone()
                if package_result:
                    print(f"🔍 Найден дубль по package_name и версии: {package_result[1]}")
                    if self.analyzer:
                        self.analyzer.log_duplicate_found('package', package_result[1], package_result[2], 
                                                        f'Совпадение package name: {package_name}')
                    cursor.close()
                    return False, package_result
            
            # Проверяем по news_id + app_name + version (оригинальная логика)
            original_query = """
            SELECT id, version, file_size, checksum, file_path, source_priority
            FROM file_tracking
            WHERE news_id = %s AND app_name = %s AND version = %s
            ORDER BY source_priority DESC, last_updated DESC LIMIT 1
            """
            cursor.execute(original_query, (news_id, app_name, current_version))
            result = cursor.fetchone()
            
            if result:
                print(f"✅ Версия {current_version} уже актуальна")
                if self.analyzer:
                    self.analyzer.log_duplicate_found('name', app_name, current_version, 
                                                    'Точное совпадение названия и версии')
                cursor.close()
                return False, result
            
            # Если не найдено точного совпадения, проверяем похожие приложения
            if ENABLE_FUZZY_MATCHING:
                similar_apps = self.find_similar_apps(app_name, threshold=0.8)
                if similar_apps:
                    print(f"🔍 Найдены похожие приложения:")
                    for similar in similar_apps[:3]:  # Показываем топ-3
                        print(f"   - {similar['app_name']} (схожесть: {similar['similarity']:.2f})")
                    
                    if self.analyzer and ENABLE_DETAILED_LOGGING:
                        self.analyzer.log_similar_apps(app_name, similar_apps)
                    
                    # Проверяем, есть ли среди похожих приложений такая же версия
                    for similar in similar_apps:
                        similar_query = """
                        SELECT id, version, file_size, checksum, file_path, source_priority
                        FROM file_tracking
                        WHERE app_name = %s AND version = %s
                        ORDER BY source_priority DESC, last_updated DESC LIMIT 1
                        """
                        cursor.execute(similar_query, (similar['app_name'], current_version))
                        similar_result = cursor.fetchone()
                        if similar_result:
                            print(f"⚠️ Возможный дубль: {similar['app_name']} v{current_version} (схожесть: {similar['similarity']:.2f})")
                            if self.analyzer and ENABLE_DETAILED_LOGGING:
                                self.analyzer.log_duplicate_found('name', similar['app_name'], current_version, 
                                                                f'Похожее приложение (схожесть: {similar["similarity"]:.2f})', 
                                                                similar['similarity'])
                            cursor.close()
                            return False, similar_result
            
            cursor.close()
            print(f"📝 Новое приложение {app_name} версии {current_version} для новости {news_id}")
            return True, None

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

            # Для onserver используем переданное имя файла (уже очищенное)
            relative_path = f"{download_dir.name}/{downloaded_filename}"
            
            print(f"🗂️ Путь в onserver (без timestamp): {relative_path}")
            print(f"📁 Загруженный файл: {downloaded_filename}")

            insert_query = """
            INSERT INTO dle_files (news_id, name, onserver, author, date, dcount, size, checksum, driver, is_public)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """

            # Генерируем timestamp для поля date
            timestamp = str(int(time.time()))
            
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

    def add_to_tracking(self, news_id, app_name, version, file_size, file_path, checksum, source_url, sha256_hash=None, package_name=None, source_priority=0):
        """Добавляем запись в таблицу отслеживания с улучшенными полями"""
        try:
            cursor = self.connection.cursor()

            insert_query = """
            INSERT INTO file_tracking (news_id, app_name, version, file_size, file_path, checksum, sha256_hash, package_name, source_priority, source_url)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """

            # В version записываем ТОЛЬКО версию, без названия приложения
            values = (news_id, app_name, version, file_size, str(file_path), checksum, sha256_hash, package_name, source_priority, source_url)

            cursor.execute(insert_query, values)
            self.connection.commit()
            cursor.close()

            print(f"✅ Добавлена запись в таблицу отслеживания:")
            print(f"   app_name: {app_name}")
            print(f"   version: {version}")
            print(f"   sha256: {sha256_hash[:16] if sha256_hash else 'N/A'}...")
            print(f"   package_name: {package_name or 'N/A'}")
            print(f"   source_priority: {source_priority}")
            return True

        except Error as e:
            print(f"❌ Ошибка добавления в tracking: {e}")
            return False
    
    def find_similar_apps(self, app_name, threshold=0.8):
        """Находим похожие приложения с помощью fuzzy matching с кэшированием"""
        # Проверяем кэш
        cache_key = f"{app_name}_{threshold}"
        if cache_key in self._similar_apps_cache:
            return self._similar_apps_cache[cache_key]
        
        try:
            cursor = self.connection.cursor()
            
            # Получаем все уникальные названия приложений
            query = """
            SELECT DISTINCT app_name, COUNT(*) as count
            FROM file_tracking
            GROUP BY app_name
            ORDER BY count DESC
            """
            cursor.execute(query)
            all_apps = cursor.fetchall()
            cursor.close()
            
            similar_apps = []
            for stored_app_name, count in all_apps:
                if VersionUtils.fuzzy_match_app_names(app_name, stored_app_name, threshold):
                    similar_apps.append({
                        'app_name': stored_app_name,
                        'count': count,
                        'similarity': self._calculate_similarity(app_name, stored_app_name)
                    })
            
            # Сортируем по схожести
            similar_apps.sort(key=lambda x: x['similarity'], reverse=True)
            
            # Кэшируем результат
            self._similar_apps_cache[cache_key] = similar_apps
            
            return similar_apps
            
        except Error as e:
            print(f"❌ Ошибка поиска похожих приложений: {e}")
            return []
    
    def _calculate_similarity(self, name1, name2):
        """Вычисляем коэффициент схожести между названиями"""
        # Нормализуем названия
        name1_norm = re.sub(r'[^\w\s]', '', name1.lower()).strip()
        name2_norm = re.sub(r'[^\w\s]', '', name2.lower()).strip()
        
        # Простое сравнение по словам
        words1 = set(name1_norm.split())
        words2 = set(name2_norm.split())
        
        if not words1 or not words2:
            return 0
        
        # Вычисляем коэффициент схожести
        intersection = len(words1.intersection(words2))
        union = len(words1.union(words2))
        
        return intersection / union if union > 0 else 0
    
    def check_duplicate_by_content(self, sha256_hash):
        """Проверяем дубли по содержимому файла (SHA-256)"""
        try:
            cursor = self.connection.cursor()
            query = """
            SELECT id, app_name, version, file_size, file_path, source_priority
            FROM file_tracking
            WHERE sha256_hash = %s
            ORDER BY source_priority DESC, last_updated DESC
            LIMIT 1
            """
            cursor.execute(query, (sha256_hash,))
            result = cursor.fetchone()
            cursor.close()
            
            if result:
                print(f"🔍 Найден точный дубль по содержимому: {result[1]} v{result[2]}")
                return result
            
            return None
            
        except Error as e:
            print(f"❌ Ошибка проверки дубля по содержимому: {e}")
            return None
    
    def check_duplicate_by_size(self, file_size, tolerance_percent=5):
        """Проверяем дубли по размеру файла с допустимым отклонением"""
        try:
            cursor = self.connection.cursor()
            
            # Вычисляем допустимое отклонение
            tolerance = int(file_size * tolerance_percent / 100)
            min_size = file_size - tolerance
            max_size = file_size + tolerance
            
            query = """
            SELECT id, app_name, version, file_size, file_path, source_priority, sha256_hash
            FROM file_tracking
            WHERE file_size BETWEEN %s AND %s
            ORDER BY ABS(file_size - %s) ASC, source_priority DESC, last_updated DESC
            LIMIT 5
            """
            cursor.execute(query, (min_size, max_size, file_size))
            results = cursor.fetchall()
            cursor.close()
            
            if results:
                print(f"🔍 Найдены файлы похожего размера ({len(results)} шт.):")
                for result in results:
                    size_diff = abs(result[3] - file_size)
                    size_diff_percent = (size_diff / file_size) * 100
                    print(f"   - {result[1]} v{result[2]} ({result[3]} байт, отклонение: {size_diff_percent:.1f}%)")
                
                # Возвращаем самый близкий по размеру
                return results[0]
            
            return None
            
        except Error as e:
            print(f"❌ Ошибка проверки дубля по размеру: {e}")
            return None
    
    def should_replace_existing(self, existing_data, new_source_priority):
        """Определяем, нужно ли заменить существующий файл новым с более высоким приоритетом"""
        if not existing_data:
            return False
        
        existing_priority = existing_data[5] if len(existing_data) > 5 else 0
        return new_source_priority > existing_priority
    
    def replace_lower_priority_file(self, existing_id, new_data):
        """Заменяем файл с более низким приоритетом"""
        try:
            cursor = self.connection.cursor()
            
            # Обновляем существующую запись новыми данными
            update_query = """
            UPDATE file_tracking 
            SET app_name = %s, version = %s, file_size = %s, file_path = %s, 
                checksum = %s, sha256_hash = %s, package_name = %s, 
                source_priority = %s, source_url = %s, last_updated = CURRENT_TIMESTAMP
            WHERE id = %s
            """
            
            values = (
                new_data['app_name'], new_data['version'], new_data['file_size'],
                new_data['file_path'], new_data['checksum'], new_data['sha256_hash'],
                new_data['package_name'], new_data['source_priority'], new_data['source_url'],
                existing_id
            )
            
            cursor.execute(update_query, values)
            self.connection.commit()
            cursor.close()
            
            print(f"🔄 Заменен файл с более низким приоритетом (ID: {existing_id})")
            return True
            
        except Error as e:
            print(f"❌ Ошибка замены файла: {e}")
            return False
    
    def delete_old_file_from_apk_original(self, news_id):
        """Удаляем старый файл из поля apk-original"""
        try:
            cursor = self.connection.cursor()
            
            # Получаем текущее поле apk-original
            select_query = "SELECT xfields FROM dle_post WHERE id = %s"
            cursor.execute(select_query, (news_id,))
            result = cursor.fetchone()
            
            if not result:
                print(f"❌ Новость ID {news_id} не найдена")
                cursor.close()
                return False
                
            xfields = result[0]
            
            # Извлекаем старый attachment ID из поля apk-original
            import re
            old_attachment_match = re.search(r'apk-original\|\[attachment=(\d+):', xfields)
            
            if not old_attachment_match:
                print(f"ℹ️ Поле apk-original не содержит attachment для новости {news_id}")
                cursor.close()
                return False
                
            old_file_id = int(old_attachment_match.group(1))
            print(f"🔍 Найден старый файл ID {old_file_id} в поле apk-original")
            
            # Получаем информацию о старом файле
            file_query = "SELECT onserver, driver, name FROM dle_files WHERE id = %s"
            cursor.execute(file_query, (old_file_id,))
            file_result = cursor.fetchone()
            
            if not file_result:
                print(f"❌ Файл ID {old_file_id} не найден в dle_files")
                cursor.close()
                return False
                
            onserver, driver, filename = file_result
            print(f"📁 Старый файл: {filename} (путь: {onserver}, хранилище: {driver})")
            
            # Удаляем с диска
            if self.delete_file_from_storage(onserver, driver):
                # Удаляем из БД
                delete_query = "DELETE FROM dle_files WHERE id = %s"
                cursor.execute(delete_query, (old_file_id,))
                self.connection.commit()
                print(f"✅ Удален старый файл ID {old_file_id}: {filename}")
                cursor.close()
                return True
            else:
                print(f"❌ Не удалось удалить файл с диска: {onserver}")
                cursor.close()
                return False
                
        except Error as e:
            print(f"❌ Ошибка удаления старого файла: {e}")
            return False
    
    def delete_file_from_storage(self, onserver, driver):
        """Удаляем файл с хранилища"""
        try:
            # Получаем информацию о хранилище
            cursor = self.connection.cursor()
            storage_query = "SELECT * FROM dle_storage WHERE id = %s"
            cursor.execute(storage_query, (driver,))
            storage = cursor.fetchone()
            cursor.close()
            
            if not storage:
                print(f"❌ Хранилище ID {driver} не найдено")
                return False
            
            # Формируем полный путь
            storage_path = storage[8]  # path из таблицы dle_storage
            print(f"🔍 Отладка путей:")
            print(f"   storage_path: '{storage_path}'")
            print(f"   onserver: '{onserver}'")
            
            # Добавляем префикс /files если его нет
            if not onserver.startswith('/files'):
                onserver_with_prefix = f"/files/{onserver}"
                print(f"   Добавлен префикс /files")
            else:
                onserver_with_prefix = onserver
                print(f"   Префикс /files уже есть")
            
            print(f"   onserver_with_prefix: '{onserver_with_prefix}'")
            
            # Убираем двойные слеши
            full_path = f"{storage_path}{onserver_with_prefix}".replace('//', '/')
            
            print(f"🗂️ Полный путь к файлу: {full_path}")
            print(f"📂 Путь хранилища: {storage_path}")
            print(f"📁 Относительный путь: {onserver_with_prefix}")
            
            if storage[1] == 1:  # FTP хранилище
                print(f"🔌 Используем FTP хранилище: {storage[3]}:{storage[4]}")
                return self.delete_file_via_ftp(storage, full_path)
            else:
                # Локальное удаление
                import os
                print(f"💾 Используем локальное хранилище")
                if os.path.exists(full_path):
                    os.remove(full_path)
                    print(f"🗑️ Удален локальный файл: {full_path}")
                    return True
                else:
                    print(f"⚠️ Файл не найден: {full_path}")
                    return False
            
        except Exception as e:
            print(f"❌ Ошибка удаления файла с хранилища: {e}")
            return False
    
    def delete_file_via_ftp(self, storage, file_path):
        """Удаляем файл через FTP"""
        try:
            import ftplib
            
            print(f"🔌 Подключаемся к FTP: {storage[3]}:{storage[4]}")
            ftp = ftplib.FTP()
            ftp.connect(storage[3], storage[4])  # host, port
            ftp.login(storage[5], storage[6])    # username, password
            
            # Проверяем существование файла
            try:
                file_size = ftp.size(file_path)
                if file_size is not None:
                    print(f"✅ Файл найден на FTP, размер: {file_size} байт")
                else:
                    print(f"⚠️ Файл не найден на FTP: {file_path}")
                    ftp.quit()
                    return False
            except:
                print(f"⚠️ Не удалось проверить существование файла: {file_path}")
                ftp.quit()
                return False
            
            print(f"🗑️ Удаляем файл через FTP: {file_path}")
            ftp.delete(file_path)
            ftp.quit()
            
            print(f"✅ Файл успешно удален через FTP: {file_path}")
            return True
            
        except Exception as e:
            print(f"❌ Ошибка удаления через FTP: {e}")
            return False
