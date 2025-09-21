#!/usr/bin/env python3
"""
Модуль для скачивания файлов с APKPure.com
Интегрирован в систему обработки файлов
"""
import asyncio
import os
import re
import hashlib
from pathlib import Path
from datetime import datetime
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError
from ..config import BROWSER_ARGS, USER_AGENT, CLOUDFLARE_TIMEOUT, PAGE_LOAD_TIMEOUT, DOWNLOAD_TIMEOUT
from .file_normalizer import FileNormalizer


class APKPureDownloader:
    def __init__(self, download_dir):
        self.download_dir = download_dir

    def extract_package_name(self, url):
        """Извлекает package name из URL APKPure"""
        # Пример: https://apkpure.com/ru/brawl-stars-android/com.supercell.brawlstars/download
        # Извлекаем com.supercell.brawlstars
        match = re.search(r'/([a-zA-Z0-9._-]+)/download', url)
        if match:
            return match.group(1)

        # Альтернативный способ
        match = re.search(r'/([a-zA-Z0-9._-]+)/?$', url.rstrip('/'))
        if match:
            return match.group(1)

        return "unknown.app"

    def calculate_checksum(self, file_path):
        """Вычисляем MD5 чексумму файла"""
        hash_md5 = hashlib.md5()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()

    def normalize_filename(self, filename):
        """Нормализуем имя файла согласно требованиям"""
        return FileNormalizer.normalize_filename(filename)

    async def setup_browser(self):
        """Настройка браузера с настройками для скачивания"""
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(
            headless=True,
            args=BROWSER_ARGS + [
                '--disable-extensions',
                '--no-first-run',
                '--disable-default-apps',
                '--disable-features=TranslateUI',
                '--disable-ipc-flooding-protection',
                '--disable-web-security',
                '--allow-running-insecure-content',
                '--disable-features=VizDisplayCompositor'
            ]
        )

        # Создаем контекст с настройками для скачивания
        self.context = await self.browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent=USER_AGENT,
            locale='ru-RU',
            timezone_id='Europe/Moscow',
            accept_downloads=True,
            extra_http_headers={
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
                'Accept-Language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7',
                'Accept-Encoding': 'gzip, deflate, br',
                'Cache-Control': 'max-age=0',
                'Sec-Fetch-Dest': 'document',
                'Sec-Fetch-Mode': 'navigate',
                'Sec-Fetch-Site': 'none',
                'Sec-Fetch-User': '?1',
                'Upgrade-Insecure-Requests': '1'
            }
        )

        self.page = await self.context.new_page()

        # Скрываем автоматизацию
        await self.page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined,
            });

            window.chrome = {
                runtime: {},
            };

            Object.defineProperty(navigator, 'plugins', {
                get: () => [1, 2, 3, 4, 5],
            });

            Object.defineProperty(navigator, 'languages', {
                get: () => ['ru-RU', 'ru', 'en-US', 'en'],
            });
        """)

    async def check_available_formats(self, app_url):
        """Проверяет доступные форматы на странице скачивания"""
        try:
            # Переходим на страницу скачивания
            download_url = app_url
            if not download_url.endswith('/download'):
                download_url = download_url.rstrip('/') + '/download'

            print(f"🔍 Проверяем доступные форматы: {download_url}")
            await self.page.goto(download_url, wait_until='domcontentloaded', timeout=PAGE_LOAD_TIMEOUT)

            # Ждем загрузки страницы
            await self.page.wait_for_timeout(3000)

            available_formats = set()

            # Ищем в блоке version-list
            try:
                version_list = await self.page.locator('#version-list').first
                if await version_list.is_visible():
                    tags = await version_list.locator('span.tag[data-tag]').all()
                    for tag in tags:
                        tag_value = await tag.get_attribute('data-tag')
                        if tag_value:
                            available_formats.add(tag_value.upper())
                            print(f"📦 Найден формат в version-list: {tag_value}")
            except:
                pass

            # Ищем в блоке show-more
            try:
                show_more = await self.page.locator('.show-more').first
                if await show_more.is_visible():
                    tags = await show_more.locator('span.tag[data-tag]').all()
                    for tag in tags:
                        tag_value = await tag.get_attribute('data-tag')
                        if tag_value:
                            available_formats.add(tag_value.upper())
                            print(f"📦 Найден формат в show-more: {tag_value}")
            except:
                pass

            # Ищем в любых других местах
            try:
                all_tags = await self.page.locator('span.tag[data-tag]').all()
                for tag in all_tags:
                    tag_value = await tag.get_attribute('data-tag')
                    if tag_value and tag_value.upper() in ['APK', 'XAPK', 'APKS']:
                        available_formats.add(tag_value.upper())
                        print(f"📦 Найден формат: {tag_value}")
            except:
                pass

            print(f"🎯 Доступные форматы: {', '.join(sorted(available_formats))}")
            return available_formats

        except Exception as e:
            print(f"⚠️ Ошибка при проверке форматов: {e}")
            return set()

    def determine_download_priority(self, available_formats):
        """Определяет приоритет скачивания на основе доступных форматов"""
        formats = {f.upper() for f in available_formats}

        print(f"🧠 Analyzing formats: {formats}")

        # Priority logic:
        # 1. If APK available - download only APK
        # 2. If XAPK available but no APK - download XAPK
        # 3. If XAPK + APKs - download XAPK
        # 4. If XAPK + APK + APKs - download only APK

        if 'APK' in formats:
            print("✅ Priority: APK (found clean APK)")
            return 'APK'
        elif 'XAPK' in formats and 'APK' not in formats:
            print("✅ Priority: XAPK (APK not available)")
            return 'XAPK'
        elif 'XAPK' in formats:
            print("✅ Priority: XAPK (default)")
            return 'XAPK'
        else:
            print("⚠️ Priority: APK (fallback)")
            return 'APK'

    async def extract_version_from_page(self, app_url):
        """Extract version from APKPure app page"""
        try:
            # Remove /download from URL if present
            page_url = app_url.replace('/download', '')
            
            print(f"🔍 Getting version from page: {page_url}")
            await self.page.goto(page_url, wait_until='domcontentloaded', timeout=PAGE_LOAD_TIMEOUT)
            
            # Wait for page load
            await self.page.wait_for_timeout(2000)
            
            # Search for version in various places
            version_selectors = [
                '.version-number',
                '.version',
                '[data-dt-version]',
                '.apk-version',
                '.app-version'
            ]
            
            for selector in version_selectors:
                try:
                    element = await self.page.query_selector(selector)
                    if element:
                        version_text = await element.inner_text()
                        # Extract only version number
                        version_match = re.search(r'(\d+\.\d+\.\d+)', version_text)
                        if version_match:
                            version = version_match.group(1)
                            print(f"✅ Found version on APKPure page: {version}")
                            return version
                except:
                    continue
            
            print("⚠️ Version not found on APKPure page")
            return None
            
        except Exception as e:
            print(f"❌ Error getting version from APKPure page: {e}")
            return None

    async def download_file(self, file_type, package_name):
        """Скачивание файла указанного типа"""
        try:
            print(f"🚀 Начинаем скачивание {file_type} с APKPure...")

            # Настраиваем обработчик скачивания
            download_info = {'downloads': [], 'completed_files': []}

            async def handle_download(download):
                try:
                    filename = download.suggested_filename
                    print(f"📥 Начато скачивание: {filename}")
                    download_info['downloads'].append(download)

                    # Определяем путь для сохранения
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

                    if filename:
                        suggested_name = filename
                    else:
                        ext = '.xapk' if file_type == 'XAPK' else '.apk'
                        suggested_name = f"App_{timestamp}{ext}"

                    # Убеждаемся, что расширение правильное
                    if not suggested_name.lower().endswith(('.apk', '.xapk')):
                        if file_type == 'XAPK':
                            suggested_name += '.xapk'
                        else:
                            suggested_name += '.apk'

                    # Нормализуем имя файла
                    normalized_name = self.normalize_filename(suggested_name)
                    filepath = self.download_dir / normalized_name
                    
                    print(f"💾 Сохраняем как: {filepath}")

                    # Сохраняем файл
                    try:
                        await download.save_as(filepath)
                        download_info['completed_files'].append(str(filepath))

                        print(f"✅ Файл сохранен: {filepath}")

                        # Проверяем размер
                        if filepath.exists():
                            size_mb = filepath.stat().st_size / (1024 * 1024)
                            print(f"📊 Размер файла: {size_mb:.2f} MB")

                            # Проверяем на подозрительно маленький размер
                            if file_type == 'APK' and size_mb < 80 and size_mb > 30:
                                print(f"⚠️ Подозрительно маленький APK файл ({size_mb:.2f} MB)")
                                print("💡 Возможно, это не полный APK, а заглушка")
                            elif size_mb > 100:
                                print("🎉 Отличный размер файла!")
                            elif size_mb > 10:
                                print("✅ Файл скачан")
                            else:
                                print("⚠️ Файл может быть неполным")

                    except Exception as save_error:
                        print(f"⚠️ Ошибка при сохранении: {save_error}")

                except Exception as e:
                    print(f"⚠️ Ошибка в обработчике скачивания: {e}")

            # Подключаем обработчик скачивания
            self.page.on("download", handle_download)

            # Формируем URL для скачивания
            download_url = f"https://d.apkpure.com/b/{file_type}/{package_name}?version=latest"

            print(f"🔗 Скачиваем {file_type}: {download_url}")

            # Переходим по ссылке скачивания
            try:
                await self.page.goto(download_url, wait_until='commit', timeout=10000)
            except Exception as goto_error:
                if "Download is starting" in str(goto_error):
                    print(f"✅ {file_type} скачивание началось автоматически")
                else:
                    print(f"⚠️ Ошибка перехода: {goto_error}")
                    return None, None

            # Ждем начала скачивания
            wait_time = 0
            while wait_time < 15 and not download_info['downloads']:
                await self.page.wait_for_timeout(1000)
                wait_time += 1

            if download_info['downloads']:
                print(f"📥 {file_type} скачивание обнаружено, ожидаем завершения...")

                # Ждем завершения скачивания
                wait_time = 0
                while wait_time < 300 and not download_info['completed_files']:
                    await self.page.wait_for_timeout(1000)
                    wait_time += 1

                    if wait_time % 30 == 0:
                        print(f"⏳ Ожидание: {wait_time}с")

                if download_info['completed_files']:
                    await self.page.wait_for_timeout(3000)  # Дополнительное ожидание
                    downloaded_path = download_info['completed_files'][0]
                    return Path(downloaded_path), "Unknown"  # Возвращаем Path и версию

            print(f"❌ {file_type} скачивание не удалось")
            return None, None

        except Exception as e:
            print(f"❌ Ошибка при скачивании {file_type}: {e}")
            return None, None

    async def cleanup(self):
        """Безопасная очистка ресурсов"""
        try:
            await asyncio.sleep(2)

            if hasattr(self, 'page'):
                try:
                    await self.page.close()
                except:
                    pass

            if hasattr(self, 'context'):
                try:
                    await self.context.close()
                except:
                    pass

            if hasattr(self, 'browser'):
                try:
                    await self.browser.close()
                except:
                    pass

            if hasattr(self, 'playwright'):
                try:
                    await self.playwright.stop()
                except:
                    pass
        except Exception as e:
            print(f"⚠️ Ошибка при очистке APKPure: {e}")

    async def download_from_apkpure(self, app_url):
        """Основной метод скачивания с APKPure"""
        try:
            print("🎭 Запуск APKPure загрузчика")
            print(f"📱 Приложение: {app_url}")

            # Извлекаем package name
            package_name = self.extract_package_name(app_url)
            print(f"📦 Package: {package_name}")

            # Настройка браузера
            await self.setup_browser()

            # Получаем версию со страницы
            try:
                page_version = await self.extract_version_from_page(app_url)
            except Exception as e:
                print(f"⚠️ Ошибка получения версии: {e}")
                page_version = None

            # Проверяем доступные форматы
            available_formats = await self.check_available_formats(app_url)

            if not available_formats:
                print("⚠️ Не удалось определить доступные форматы, пробуем APK")
                file_type = 'APK'
            else:
                # Определяем приоритет
                file_type = self.determine_download_priority(available_formats)

            # Скачиваем выбранный формат
            downloaded_file, download_version = await self.download_file(file_type, package_name)

            if downloaded_file and downloaded_file.exists():
                print("=" * 60)
                print("🎉 СКАЧИВАНИЕ APKPure ЗАВЕРШЕНО!")

                size_mb = downloaded_file.stat().st_size / (1024 * 1024)
                actual_type = "XAPK" if str(downloaded_file).lower().endswith('.xapk') else "APK"

                print(f"📱 Файл: {downloaded_file.name}")
                print(f"📦 Тип: {actual_type}")
                print(f"📊 Размер: {size_mb:.2f} MB")
                print(f"📂 Путь: {downloaded_file.absolute()}")

                # Возвращаем версию со страницы если есть, иначе "Unknown"
                final_version = page_version if page_version else "Unknown"
                return downloaded_file, final_version
            else:
                print("❌ Не удалось скачать файл с APKPure")
                return None, None

        except Exception as e:
            print(f"❌ Критическая ошибка APKPure: {e}")
            return None, None
        finally:
            await self.cleanup()
