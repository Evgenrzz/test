#!/usr/bin/env python3
"""
Основной модуль parser2 для обработки модифицированных приложений
"""
import asyncio
import logging
import re
from pathlib import Path
from .config import *
from .database_api import DatabaseManagerAPI
from .lib.liteapks_downloader import LiteAPKsDownloader
from .lib.file_downloader import FileDownloader
from .lib.duplicate_analyzer import DuplicateAnalyzer
from .lib.version_utils import VersionUtils


class Parser2:
    """Основной класс parser2 для обработки модифицированных приложений"""
    
    def __init__(self):
        self.setup_logging()
        print("🔧 Parser2 v2.0 - с обновленной логикой liteapks.com")
        self.version_utils = VersionUtils()
        self.analyzer = DuplicateAnalyzer()
        self.db_manager = DatabaseManagerAPI(self.analyzer)
        # Создаем полную конфигурацию для liteapks_downloader
        liteapks_full_config = {
            'liteapks': LITEAPKS_CONFIG,
            'browser_args': BROWSER_ARGS,
            'user_agent': USER_AGENT,
            'page_load_timeout': PAGE_LOAD_TIMEOUT
        }
        self.liteapks_downloader = LiteAPKsDownloader(liteapks_full_config)
        self.file_downloader = FileDownloader({
            'download_timeout': DOWNLOAD_TIMEOUT,
            'mod': MOD_CONFIG
        })
        
        # Статистика
        self.stats = {
            'total_processed': 0,
            'successful_downloads': 0,
            'failed_downloads': 0,
            'skipped_duplicates': 0,
            'errors': 0
        }
    
    def setup_logging(self):
        """Настраиваем логирование в файл logs/parser2_log.txt"""
        # Создаем папку logs если её нет
        logs_dir = Path("logs")
        logs_dir.mkdir(exist_ok=True)
        
        # Создаем имя файла лога
        log_filename = "parser2_log.txt"
        log_filepath = logs_dir / log_filename
        
        # Настраиваем логирование
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_filepath, mode='w', encoding='utf-8'),  # mode='w' переписывает файл
                logging.StreamHandler()  # Также выводим в консоль
            ]
        )
        
        self.logger = logging.getLogger(__name__)
        self.logger.info(f"🚀 Запуск parser2 - лог файл: {log_filepath}")
    
    def parse_link_line(self, line):
        """Парсим строку с ссылками"""
        line = line.strip()
        if not line or line.startswith('#'):
            return None
        
        # Формат: ID,[attachment=123:filename.apk],url1;url2;url3
        parts = line.split(',', 2)
        if len(parts) < 3:
            self.logger.warning(f"⚠️ Неверный формат строки: {line}")
            return None
        
        try:
            news_id = int(parts[0])
            attachment = parts[1]
            urls_string = parts[2]
            
            # Извлекаем attachment ID и имя файла
            attachment_match = re.search(r'\[attachment=(\d+):([^\]]+)\]', attachment)
            if not attachment_match:
                self.logger.warning(f"⚠️ Неверный формат attachment: {attachment}")
                return None
            
            attachment_id = int(attachment_match.group(1))
            attachment_name = attachment_match.group(2)
            
            # Разделяем URLs по точке с запятой
            urls = [url.strip() for url in urls_string.split(';') if url.strip()]
            
            return {
                'news_id': news_id,
                'attachment_id': attachment_id,
                'attachment_name': attachment_name,
                'urls': urls
            }
            
        except ValueError as e:
            self.logger.warning(f"⚠️ Ошибка парсинга строки: {e}")
            return None
    
    async def process_links_file(self, links_file):
        """Обрабатываем файл с ссылками"""
        self.logger.info(f"📄 Обрабатываем файл: {links_file}")
        
        try:
            with open(links_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            self.logger.info(f"📊 Найдено {len(lines)} строк в файле")
            
            for i, line in enumerate(lines, 1):
                self.logger.info(f"📝 Строка {i}/{len(lines)}")
                
                link_data = self.parse_link_line(line)
                if not link_data:
                    continue
                
                await self.process_link_data(link_data)
                
        except FileNotFoundError:
            self.logger.error(f"❌ Файл не найден: {links_file}")
        except Exception as e:
            self.logger.error(f"❌ Ошибка обработки файла: {e}")
    
    async def process_link_data(self, link_data):
        """Обрабатываем данные ссылки"""
        news_id = link_data['news_id']
        attachment_name = link_data['attachment_name']
        urls = link_data['urls']
        
        self.logger.info(f"🔄 Обрабатываем: {attachment_name} (ID: {news_id})")
        
        # Извлекаем название приложения и версию из имени файла
        app_name = self.version_utils.extract_app_name_from_filename(attachment_name)
        file_version = self.version_utils.extract_version_from_filename(attachment_name)
        
        self.logger.info(f"📱 Приложение: {app_name}")
        self.logger.info(f"🔢 Версия из файла: {file_version}")
        
        # Обрабатываем каждую ссылку
        url_versions = []
        for i, url in enumerate(urls, 1):
            self.logger.info(f"📱 Ссылка {i}: {url}")
            
            # Проверяем поддерживаемые сайты
            if 'liteapks.com' not in url:
                self.logger.info(f"⏭️ Пропускаем неподдерживаемую ссылку: {url}")
                continue
            
            # Получаем версию со страницы
            version = await self.liteapks_downloader.extract_version_from_page(url)
            if version:
                url_versions.append((url, version))
                self.logger.info(f"    ✅ Версия: {version}")
            else:
                self.logger.warning(f"    ❌ Не удалось получить версию с {url}")
        
        # Выбираем лучшую ссылку
        if not url_versions:
            self.logger.warning(f"⚠️ Не удалось получить версии ни с одной ссылки, используем первую")
            if urls:
                version = await self.liteapks_downloader.extract_version_from_page(urls[0])
                if version:
                    url_versions.append((urls[0], version))
        
        if not url_versions:
            self.logger.error(f"❌ Не удалось получить версию ни с одной ссылки")
            self.stats['errors'] += 1
            return
        
        # Выбираем ссылку с лучшей версией
        best_url, best_version = max(url_versions, key=lambda x: self.version_utils.compare_versions(x[1], file_version))
        
        self.logger.info(f"🏆 Выбрана лучшая ссылка: {best_url}")
        self.logger.info(f"🏆 Лучшая версия: {best_version}")
        
        # Извлекаем информацию о приложении
        app_info = self.liteapks_downloader.extract_app_info(best_url)
        
        # Обрабатываем файл
        await self.process_file(
            news_id=news_id,
            app_name=app_name,
            version=best_version,
            url=best_url,
            attachment_name=attachment_name,
            app_info=app_info
        )
    
    async def process_file(self, news_id, app_name, version, url, attachment_name, app_info):
        """Обрабатываем файл"""
        self.stats['total_processed'] += 1
        
        # Извлекаем чистую версию
        clean_version = self.version_utils.extract_clean_version(version)
        if clean_version:
            version = clean_version
        
        self.logger.info(f"🏷️ Финальная версия (только номер): {version}")
        
        # Извлекаем package name
        package_name = app_info.get('package_name')
        if package_name:
            self.logger.info(f"📦 Package name: {package_name}")
        
        # Определяем приоритет источника
        source_priority = app_info.get('source_priority', MOD_CONFIG['default_priority'])
        self.logger.info(f"⭐ Приоритет источника: {source_priority}")
        
        # Проверяем версию в поле mod-at
        self.logger.info(f"🔍 Проверяем версию в поле {MOD_CONFIG['field_name']}...")
        
        need_update = self.db_manager.check_version_in_mod_at(news_id, version)
        
        if not need_update:
            self.logger.info(f"⏭️ Пропускаем, версия в {MOD_CONFIG['field_name']} актуальна")
            self.stats['skipped_duplicates'] += 1
            return
        
        # Проверяем дубли
        need_download, existing_duplicate = self.db_manager.check_if_update_needed(
            news_id, app_name, version, package_name=package_name
        )
        
        if not need_download:
            self.logger.info(f"⏭️ Пропускаем, дубль найден")
            self.stats['skipped_duplicates'] += 1
            return
        
        # Скачиваем файл
        success = await self.download_and_process_file(
            news_id=news_id,
            app_name=app_name,
            version=version,
            url=url,
            attachment_name=attachment_name,
            package_name=package_name,
            source_priority=source_priority,
            mod_type=app_info.get('mod_type'),
            existing_duplicate=existing_duplicate
        )
        
        if success:
            self.stats['successful_downloads'] += 1
        else:
            self.stats['failed_downloads'] += 1
    
    async def download_and_process_file(self, news_id, app_name, version, url, attachment_name, package_name, source_priority, mod_type, existing_duplicate):
        """Скачиваем и обрабатываем файл"""
        try:
            # Создаем директорию для скачивания
            download_dir = self.file_downloader.create_download_directory(BASE_DOWNLOAD_DIR)
            
            # Получаем ссылки для скачивания
            download_links = await self.liteapks_downloader.extract_download_links(url)
            
            if not download_links:
                self.logger.error(f"❌ Не найдены ссылки для скачивания")
                return False
            
            # Выбираем первую доступную ссылку
            download_url = download_links[0]['url']
            self.logger.info(f"📥 Скачиваем с: {download_url}")
            
            # Определяем имя файла
            file_extension = Path(attachment_name).suffix
            clean_app_name = re.sub(r'[^\w\s-]', '', app_name).strip()
            clean_version = re.sub(r'[^\w.-]', '', str(version))
            filename = f"{MOD_CONFIG['file_prefix']}_{clean_app_name}_{clean_version}{file_extension}"
            
            # Скачиваем файл
            file_path, file_size = await self.file_downloader.download_file(download_url, download_dir, filename)
            
            if not file_path:
                self.logger.error(f"❌ Ошибка скачивания файла")
                return False
            
            # Вычисляем чексуммы
            checksum = self.file_downloader.calculate_checksum(file_path)
            sha256_hash = None
            if ENABLE_SHA256_CHECK:
                sha256_hash = self.file_downloader.calculate_sha256(file_path)
            
            # Анализируем дубли
            if ENABLE_DETAILED_LOGGING:
                self.analyzer.analyze_duplicates(app_name, version, file_size, sha256_hash)
            
            # Обновляем базу данных
            success = await self.update_database(
                news_id=news_id,
                app_name=app_name,
                version=version,
                file_path=file_path,
                file_size=file_size,
                checksum=checksum,
                sha256_hash=sha256_hash,
                package_name=package_name,
                source_priority=source_priority,
                mod_type=mod_type,
                existing_duplicate=existing_duplicate
            )
            
            return success
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка обработки файла: {e}")
            return False
    
    async def update_database(self, news_id, app_name, version, file_path, file_size, checksum, sha256_hash, package_name, source_priority, mod_type, existing_duplicate):
        """Обновляем базу данных"""
        try:
            # Определяем расширение файла
            file_extension = file_path.suffix
            
            # Проверяем нужно ли заменить существующий файл
            if existing_duplicate and self.db_manager.should_replace_existing(existing_duplicate, source_priority):
                self.logger.info(f"🔄 Заменяем файл с более низким приоритетом")
                success = self.db_manager.replace_lower_priority_file(existing_duplicate['id'], {
                    'app_name': app_name,
                    'file_path': str(file_path),
                    'file_size': file_size,
                    'checksum': checksum
                })
                if not success:
                    return False
                
                file_id = existing_duplicate['id']
            else:
                # Добавляем новый файл в dle_files
                file_id = self.db_manager.add_to_dle_files(
                    news_id, app_name, version, file_extension, file_path.name, file_size, checksum, file_path.parent
                )
                
                if not file_id:
                    return False
            
            # Обновляем поле mod-at в dle_post
            success = self.db_manager.update_dle_post(news_id, file_id, app_name, version, file_extension)
            if not success:
                return False
            
            # Добавляем в таблицу отслеживания
            self.db_manager.add_to_tracking(
                news_id=news_id,
                app_name=app_name,
                version=version,
                file_size=file_size,
                file_path=file_path,
                checksum=checksum,
                source_url=url,
                sha256_hash=sha256_hash,
                package_name=package_name,
                source_priority=source_priority,
                mod_type=mod_type
            )
            
            self.logger.info(f"✅ Файл успешно обработан и добавлен в базу данных")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка обновления базы данных: {e}")
            return False
    
    def print_statistics(self):
        """Выводим статистику обработки"""
        self.logger.info("\n📊 Статистика обработки:")
        self.logger.info(f"   Всего обработано: {self.stats['total_processed']}")
        self.logger.info(f"   Успешно скачано: {self.stats['successful_downloads']}")
        self.logger.info(f"   Ошибок скачивания: {self.stats['failed_downloads']}")
        self.logger.info(f"   Пропущено дублей: {self.stats['skipped_duplicates']}")
        self.logger.info(f"   Ошибок: {self.stats['errors']}")
        
        # Выводим статистику анализа дублей
        if ENABLE_DETAILED_LOGGING:
            self.analyzer.print_summary()
    
    async def run(self, links_file=None):
        """Запускаем обработку"""
        try:
            self.logger.info("🚀 Запуск parser2")
            
            # Подключаемся к базе данных
            self.db_manager.connect()
            
            # Обрабатываем файл с ссылками
            if links_file is None:
                links_file = LINKS_FILE
            
            await self.process_links_file(links_file)
            
            # Выводим статистику
            self.print_statistics()
            
        except Exception as e:
            self.logger.error(f"❌ Критическая ошибка: {e}")
        finally:
            # Отключаемся от базы данных
            self.db_manager.disconnect()


async def main():
    """Главная функция"""
    parser = Parser2()
    await parser.run()


if __name__ == "__main__":
    asyncio.run(main())
