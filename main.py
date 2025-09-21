#!/usr/bin/env python3
"""
Основной модуль системы обработки файлов из step4_links.txt
Скачивает файлы через парсеры APKCombo и APKPure и обновляет базу данных
"""
import asyncio
import os
import re
from config import LINKS_FILE
from database import DatabaseManager
from version_extractor import VersionExtractor
from lib.file_downloader import FileDownloader
from lib.apkpure_downloader import APKPureDownloader


class FileProcessor:
    def __init__(self):
        self.db = DatabaseManager()
        self.version_extractor = VersionExtractor()
        self.downloader = FileDownloader()

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

        # Проверяем нужно ли обновление
        need_update, existing_data = self.db.check_if_update_needed(
            link_data['news_id'], app_name, clean_version_for_check
        )

        if not need_update:
            print("⏭️ Пропускаем, версия актуальна")
            return True

        # Определяем тип парсера и скачиваем файл
        try:
            if 'apkcombo.com' in link_data['url']:
                print("🔧 Используем парсер APKCombo")
                downloaded_file, download_version = await self.downloader.download_from_apkcombo(link_data['url'])
            elif 'apkpure.com' in link_data['url']:
                print("🔧 Используем парсер APKPure")
                # Создаем APKPure downloader с той же папкой загрузки
                apkpure_downloader = APKPureDownloader(self.downloader.download_dir)
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
            checksum = self.downloader.calculate_checksum(downloaded_file)

            print(f"📊 Размер файла: {file_size} байт")
            print(f"🔐 Чексумма: {checksum}")
            print(f"🏷️ Финальная версия для БД: {clean_version_for_check}")
            print(f"📁 Загруженный файл: {downloaded_file.name}")

            # Получаем расширение файла
            file_extension = os.path.splitext(downloaded_file.name)[1]
            
            print(f"🏷️ Чистая версия для БД: {clean_version_for_check}")
            
            # Добавляем в dle_files с правильными именами
            file_id = self.db.add_to_dle_files(
                link_data['news_id'],
                app_name,
                clean_version_for_check,
                file_extension,
                downloaded_file.name,  # Передаем имя загруженного файла
                file_size,
                checksum,
                self.downloader.download_dir
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

            # Добавляем в таблицу отслеживания с ТОЛЬКО версией
            self.db.add_to_tracking(
                link_data['news_id'],
                app_name,
                clean_version_for_check,  # ТОЛЬКО версия, например "1.8.3"
                file_size,
                downloaded_file,
                checksum,
                link_data['url']
            )

            print(f"✅ Файл {downloaded_file.name} успешно обработан с версией {clean_version_for_check}!")
            return True

        except Exception as e:
            print(f"❌ Ошибка обработки файла: {e}")
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

        print(f"\n{'='*50}")
        print(f"📊 ИТОГИ:")
        print(f"✅ Успешно обработано: {processed}")
        print(f"❌ Ошибок: {errors}")
        print(f"📄 Всего строк: {len(lines)}")


async def main():
    """Главная функция"""
    print("🚀 Запуск системы обработки файлов")
    print("🌐 Поддерживаемые сайты:")
    print("   📱 APKCombo.com - полная поддержка с извлечением версии")
    print("   📱 APKPure.com - умный загрузчик APK/XAPK")
    print("📋 Исправлены все проблемы с записью данных в БД:")
    print("   ✅ file_tracking.version - только номер версии")
    print("   ✅ dle_files.onserver - имя как у загруженного файла")
    print("   ✅ dle_files.name - читаемое имя без дублирования")
    print("   ✅ dle_post.apk-original - такое же как dle_files.name")

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
