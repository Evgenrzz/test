#!/usr/bin/env python3
"""
Основной модуль системы обработки файлов из step4_links.txt
Скачивает файлы через парсеры APKCombo и APKPure и обновляет базу данных
"""
import asyncio
import os
import re
from pathlib import Path
from datetime import datetime
from .config import LINKS_FILE, BASE_DOWNLOAD_DIR, ENABLE_SHA256_CHECK, ENABLE_FUZZY_MATCHING, ENABLE_SIZE_CHECK, ENABLE_DETAILED_LOGGING
from .database import DatabaseManager
from .version_extractor import VersionExtractor
from .lib.file_downloader import FileDownloader
from .lib.apkpure_downloader import APKPureDownloader
from .lib.duplicate_analyzer import DuplicateAnalyzer


class FileProcessor:
    def __init__(self):
        self.analyzer = DuplicateAnalyzer()
        self.db = DatabaseManager(analyzer=self.analyzer)
        self.version_extractor = VersionExtractor()
        
        # Создаем папку для текущего месяца
        self.download_dir = self.get_current_download_dir()
        self.downloader = FileDownloader(self.download_dir)
    
    def get_current_download_dir(self):
        """Получаем папку для текущего месяца в формате год-месяц"""
        now = datetime.now()
        month_dir = f"{now.year}-{now.month:02d}"
        full_path = Path(BASE_DOWNLOAD_DIR) / month_dir
        full_path.mkdir(parents=True, exist_ok=True)
        return full_path

    def parse_link_line(self, line):
        """Парсим строку из файла step4_links.txt"""
        # Формат: 1,[attachment=861:Apple Music_5.0.0.xapk],https://apkcombo.com/ru/apple-music/com.apple.android.music/
        line = line.strip()
        if not line:
            return None

        parts = line.split(',', 2)
        if len(parts) != 3:
            return None

        news_id = parts[0].strip()
        attachment_info = parts[1].strip()
        url = parts[2].strip()

        # Извлекаем информацию из attachment
        match = re.search(r'\[attachment=(\d+):([^\]]+)\]', attachment_info)
        if not match:
            return None

        old_file_id = match.group(1)
        filename = match.group(2)

        return {
            'news_id': int(news_id),
            'old_file_id': int(old_file_id),
            'filename': filename,
            'url': url
        }

    async def process_single_link(self, link_data):
        """Обрабатываем одну ссылку"""
        print(f"\n🔄 Обрабатываем: {link_data['filename']} (ID: {link_data['news_id']})")

        # Извлекаем информацию о приложении
        app_name = self.version_extractor.extract_app_name_from_filename(link_data['filename'])
        file_version = self.version_extractor.extract_version_from_filename(link_data['filename'])

        print(f"📱 Приложение: {app_name}")
        print(f"🔢 Версия из файла: {file_version}")

        # Пытаемся получить версию со страницы (только для APKCombo)
        page_version = None
        if 'apkcombo.com' in link_data['url']:
            try:
                page_version = await self.version_extractor.extract_version_from_page(link_data['url'])
            except Exception as e:
                print(f"⚠️ Ошибка получения версии со страницы APKCombo: {e}")
                page_version = None
        else:
            print("ℹ️ Версия со страницы будет получена парсером APKPure")

        # Определяем финальную версию (ТОЛЬКО номер версии)
        final_version = self.version_extractor.get_version(link_data['filename'], page_version)
        
        # Убеждаемся что это чистая версия
        clean_version_for_check = self.version_extractor.extract_clean_version(final_version)

        print(f"🏷️ Финальная версия (только номер): {clean_version_for_check}")

        # Извлекаем дополнительную информацию
        package_name = self.version_extractor.extract_package_name_from_url(link_data['url'])
        source_priority = self.version_extractor.get_source_priority(link_data['url'])
        
        print(f"📦 Package name: {package_name or 'N/A'}")
        print(f"⭐ Приоритет источника: {source_priority}")

        # Проверяем нужно ли обновление с улучшенной проверкой дублей
        need_update, existing_data = self.db.check_if_update_needed(
            link_data['news_id'], app_name, clean_version_for_check, 
            package_name=package_name
        )

        if not need_update:
            print("⏭️ Пропускаем, версия актуальна")
            self.analyzer.log_file_processed(app_name, clean_version_for_check, 0, 
                                           link_data['url'], is_new=False)
            return True

        # Определяем тип парсера и скачиваем файл
        try:
            if 'apkcombo.com' in link_data['url']:
                print("🔧 Используем парсер APKCombo")
                downloaded_file, download_version = await self.downloader.download_from_apkcombo(link_data['url'])
            elif 'apkpure.com' in link_data['url']:
                print("🔧 Используем парсер APKPure")
                # Создаем APKPure downloader с той же папкой загрузки
                apkpure_downloader = APKPureDownloader(self.download_dir)
                downloaded_file, download_version = await apkpure_downloader.download_from_apkpure(link_data['url'])
            else:
                print(f"❌ Неподдерживаемый сайт: {link_data['url']}")
                return False

            if not downloaded_file:
                print("❌ Не удалось скачать файл")
                return False

            # Если при скачивании получили версию, используем её
            if download_version and download_version != "Unknown":
                # Извлекаем только номер версии из download_version
                clean_download_version = self.version_extractor.extract_clean_version(download_version)
                clean_version_for_check = clean_download_version
                print(f"🎯 Обновляем версию из процесса скачивания: {clean_version_for_check}")

            # Получаем информацию о файле
            file_size = downloaded_file.stat().st_size
            
            # Вычисляем чексуммы
            if ENABLE_SHA256_CHECK:
                print("🔐 Вычисляем чексуммы...")
                checksum, sha256_hash = self.downloader.calculate_checksums_parallel(downloaded_file)
            else:
                print("🔐 Вычисляем MD5...")
                checksum = self.downloader.calculate_checksum(downloaded_file)
                sha256_hash = None

            print(f"📊 Размер файла: {file_size} байт")
            print(f"🔐 MD5: {checksum}")
            if sha256_hash:
                print(f"🔐 SHA-256: {sha256_hash[:16]}...")
            print(f"🏷️ Финальная версия для БД: {clean_version_for_check}")
            print(f"📁 Загруженный файл: {downloaded_file.name}")
            
            # Дополнительная проверка дублей по размеру файла
            if ENABLE_SIZE_CHECK:
                size_duplicate = self.db.check_duplicate_by_size(file_size, tolerance_percent=5)
                if size_duplicate:
                    print(f"⚠️ Найден файл похожего размера: {size_duplicate[1]} v{size_duplicate[2]}")
                    # Если это тот же файл по SHA-256, пропускаем
                    if sha256_hash and size_duplicate[6] == sha256_hash:
                        print("🔍 Это тот же файл по содержимому, пропускаем")
                        if ENABLE_DETAILED_LOGGING:
                            self.analyzer.log_duplicate_found('size', size_duplicate[1], size_duplicate[2], 
                                                            'Совпадение по размеру и содержимому')
                        return True
                    else:
                        if ENABLE_DETAILED_LOGGING:
                            self.analyzer.log_duplicate_found('size', size_duplicate[1], size_duplicate[2], 
                                                            f'Совпадение по размеру (отклонение: {abs(size_duplicate[3] - file_size)/file_size*100:.1f}%)')

            # Получаем расширение файла
            file_extension = os.path.splitext(downloaded_file.name)[1]
            
            # Очищаем имя файла от суффиксов источников
            from .lib.file_normalizer import FileNormalizer
            clean_filename = FileNormalizer.clean_source_suffixes(downloaded_file.name)
            
            # Переименовываем файл на диске
            if clean_filename != downloaded_file.name:
                new_file_path = self.download_dir / clean_filename
                downloaded_file.rename(new_file_path)
                downloaded_file = new_file_path
                print(f"📁 Файл переименован: {downloaded_file.name}")
            
            print(f"🏷️ Чистая версия для БД: {clean_version_for_check}")
            
            # Удаляем старый файл из поля apk-original перед добавлением нового
            print("🗑️ Проверяем наличие старого файла в поле apk-original...")
            self.db.delete_old_file_from_apk_original(link_data['news_id'])
            
            # Добавляем в dle_files с правильными именами
            file_id = self.db.add_to_dle_files(
                link_data['news_id'],
                app_name,
                clean_version_for_check,
                file_extension,
                clean_filename,  # Передаем очищенное имя файла
                file_size,
                checksum,
                self.download_dir
            )

            if not file_id:
                print("❌ Не удалось добавить файл в dle_files")
                return False

            # Обновляем dle_post с читаемым именем
            success = self.db.update_dle_post(
                link_data['news_id'],
                file_id,
                app_name,
                clean_version_for_check,
                file_extension
            )

            if not success:
                print("❌ Не удалось обновить dle_post")
                return False

            # Добавляем в таблицу отслеживания с улучшенными полями
            self.db.add_to_tracking(
                link_data['news_id'],
                app_name,
                clean_version_for_check,  # ТОЛЬКО версия, например "1.8.3"
                file_size,
                downloaded_file,
                checksum,
                link_data['url'],
                sha256_hash=sha256_hash,
                package_name=package_name,
                source_priority=source_priority
            )

            print(f"✅ Файл {clean_filename} успешно обработан с версией {clean_version_for_check}!")
            self.analyzer.log_file_processed(app_name, clean_version_for_check, file_size, 
                                           link_data['url'], is_new=True)
            return True

        except Exception as e:
            print(f"❌ Ошибка обработки файла: {e}")
            self.analyzer.log_processing_error(str(e), f"для {app_name}")
            return False

    async def process_links_file(self):
        """Обрабатываем файл со ссылками"""
        if not os.path.exists(LINKS_FILE):
            print(f"❌ Файл {LINKS_FILE} не найден")
            return

        print(f"📄 Читаем файл: {LINKS_FILE}")

        with open(LINKS_FILE, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        print(f"📊 Найдено {len(lines)} строк")

        # Начинаем анализ дублей
        self.analyzer.start_processing()

        processed = 0
        errors = 0

        for i, line in enumerate(lines, 1):
            print(f"\n{'='*50}")
            print(f"📝 Строка {i}/{len(lines)}")

            link_data = self.parse_link_line(line)
            if not link_data:
                print(f"⚠️ Не удалось распарсить строку: {line.strip()}")
                continue

            # Проверяем что это поддерживаемая ссылка
            if 'apkcombo.com' not in link_data['url'] and 'apkpure.com' not in link_data['url']:
                print(f"⏭️ Пропускаем неподдерживаемую ссылку: {link_data['url']}")
                continue

            try:
                success = await self.process_single_link(link_data)
                if success:
                    processed += 1
                else:
                    errors += 1

            except Exception as e:
                print(f"❌ Критическая ошибка обработки строки {i}: {e}")
                errors += 1
                continue

        # Завершаем анализ дублей
        self.analyzer.end_processing()

        print(f"\n{'='*50}")
        print(f"📊 ИТОГИ:")
        print(f"✅ Успешно обработано: {processed}")
        print(f"❌ Ошибок: {errors}")
        print(f"📄 Всего строк: {len(lines)}")


