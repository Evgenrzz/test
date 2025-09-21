#!/usr/bin/env python3
"""
Модуль для скачивания файлов с APKCombo.com
Интегрирован в систему обработки файлов
"""
import asyncio
import os
import re
import hashlib
from pathlib import Path
from datetime import datetime
from playwright.async_api import async_playwright
from config import BROWSER_ARGS, USER_AGENT, BASE_DOWNLOAD_DIR, CLOUDFLARE_TIMEOUT, PAGE_LOAD_TIMEOUT, DOWNLOAD_TIMEOUT
from .file_normalizer import FileNormalizer


class FileDownloader:
    def __init__(self, download_dir):
        self.download_dir = download_dir

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

    def format_filename_for_attachment(self, filename):
        """Форматируем имя файла для поля apk-original"""
        return FileNormalizer.format_filename_for_attachment(filename)

    def extract_version_from_filename(self, filename):
        """Извлекаем версию из имени файла"""
        # Ищем паттерн версии в имени файла
        version_patterns = [
            r'_(\d+\.\d+\.\d+)',  # _5.0.0
            r'_(\d+\.\d+)',       # _5.0
            r'v(\d+\.\d+\.\d+)',  # v5.0.0
            r'(\d+\.\d+\.\d+)',   # 5.0.0
        ]

        for pattern in version_patterns:
            match = re.search(pattern, filename)
            if match:
                return match.group(1)

        return "1.0.0"  # Версия по умолчанию

    def extract_app_name_from_filename(self, filename):
        """Извлекаем название приложения из имени файла"""
        # Убираем расширение и версию
        name = filename.replace('.xapk', '').replace('.apk', '')
        # Убираем версию если есть
        name = re.sub(r'_\d+\.\d+.*$', '', name)
        return name

    async def wait_for_cloudflare(self, page, max_wait=120):
        """Ждем прохождения проверки Cloudflare"""
        print("🔄 Проверяем наличие Cloudflare...")
        for i in range(max_wait):
            await asyncio.sleep(1)
            try:
                current_url = page.url
                page_title = await page.title()
                # Проверяем индикаторы Cloudflare
                cf_indicators = [
                    "div.cf-browser-verification",
                    "div.cf-checking-browser",
                    "[data-ray]",
                    "h1:has-text('Checking your browser')",
                    "h1:has-text('Just a moment')"
                ]
                is_cf_active = False
                for indicator in cf_indicators:
                    try:
                        element = await page.query_selector(indicator)
                        if element:
                            is_cf_active = True
                            break
                    except:
                        continue
                # Проверяем по заголовку и URL
                if ("just a moment" in page_title.lower() or
                    "checking" in page_title.lower() or
                    "cloudflare" in current_url.lower()):
                    is_cf_active = True
                if not is_cf_active:
                    print("✅ Cloudflare проверка пройдена или отсутствует")
                    return True
                if i % 10 == 0:
                    print(f"⏳ Ждем Cloudflare... ({i+1}/{max_wait})")
            except Exception as e:
                print(f"   Ошибка при проверке Cloudflare: {e}")
                continue
        print("⚠️ Превышено время ожидания Cloudflare")
        return False

    async def download_file_from_r2_url(self, page, r2_url):
        """Скачиваем файл по r2 ссылке"""
        print(f"🔗 Переходим по r2 ссылке для скачивания...")
        # Устанавливаем обработчик загрузки ДО перехода на страницу
        download_started = False
        download_obj = None

        async def handle_download(download):
            nonlocal download_started, download_obj
            download_obj = download
            download_started = True
            print("🎯 Загрузка началась!")

        page.on("download", handle_download)

        # Пытаемся перейти на страницу, но ожидаем, что может начаться загрузка
        try:
            await page.goto(r2_url, wait_until="domcontentloaded", timeout=30000)
        except Exception as e:
            if "Download is starting" in str(e):
                print("✅ Загрузка началась сразу при переходе")
                await asyncio.sleep(2)
            else:
                raise e

        # Если загрузка не началась сразу, ждем прохождения Cloudflare
        if not download_started:
            print("🔄 Загрузка не началась сразу, проверяем Cloudflare...")
            await self.wait_for_cloudflare(page, max_wait=120)
            # Ждем начала загрузки еще немного
            for i in range(30):
                if download_started:
                    break
                await asyncio.sleep(1)
                if i % 5 == 0:
                    print(f"   Ждем загрузку... ({i+1}/30)")

        if not download_started:
            raise Exception("Загрузка так и не началась")

        print("📥 Ждем завершения загрузки...")

        # Определяем имя файла
        suggested_filename = download_obj.suggested_filename
        if not suggested_filename:
            # Пытаемся извлечь из URL
            if "filename" in r2_url:
                match = re.search(r'filename%253D%2522([^%]+)', r2_url)
                if match:
                    suggested_filename = match.group(1).replace('%2520', ' ')
                else:
                    suggested_filename = "downloaded_file.apk"
            else:
                suggested_filename = "downloaded_file.apk"

        print(f"📁 Исходное имя файла: {suggested_filename}")

        # Нормализуем имя файла
        normalized_filename = self.normalize_filename(suggested_filename)

        # Сохраняем файл с нормализованным именем
        final_file = self.download_dir / normalized_filename
        await download_obj.save_as(str(final_file))

        # Проверяем результат
        if final_file.exists():
            size_mb = final_file.stat().st_size / 1024 / 1024
            print(f"✅ Файл успешно скачан: {final_file}")
            print(f"📊 Размер файла: {size_mb:.2f} MB")
            return final_file
        else:
            print("❌ Файл не был сохранен")
            return None

    async def extract_version_from_page(self, app_url):
        """Извлекаем версию со страницы приложения"""
        try:
            print(f"🔍 Получаем версию со страницы: {app_url}")
            
            # Создаем браузер для получения версии
            async with async_playwright() as p:
                browser = await p.chromium.launch(
                    headless=True,
                    args=BROWSER_ARGS
                )
                context = await browser.new_context(
                    user_agent=USER_AGENT
                )
                page = await context.new_page()
                
                try:
                    await page.goto(app_url, wait_until="domcontentloaded", timeout=PAGE_LOAD_TIMEOUT)
                    await self.wait_for_cloudflare(page, max_wait=60)
                    await asyncio.sleep(3)

                    # Ищем версию в div.version
                    version_selectors = [
                        'div.version',
                        '.version',
                        '[class*="version"]',
                        '.app-version'
                    ]
                    
                    for selector in version_selectors:
                        try:
                            element = await page.query_selector(selector)
                            if element:
                                version_text = await element.inner_text()
                                # Извлекаем только номер версии
                                version_match = re.search(r'(\d+\.\d+\.\d+)', version_text)
                                if version_match:
                                    version = version_match.group(1)
                                    print(f"✅ Найдена версия на странице: {version}")
                                    return version
                        except:
                            continue
                    
                    print("⚠️ Версия не найдена на странице")
                    return None
                    
                finally:
                    await context.close()
                    await browser.close()
                    
        except Exception as e:
            print(f"❌ Ошибка получения версии со страницы: {e}")
            return None

    async def download_from_apkcombo(self, app_url):
        """Скачиваем файл с apkcombo.com"""
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True,
                args=[
                    "--no-sandbox",
                    "--disable-blink-features=AutomationControlled",
                    "--disable-dev-shm-usage"
                ]
            )
            context = await browser.new_context(
                accept_downloads=True,
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
            page = await context.new_page()

            try:
                print(f"📱 Открываем страницу приложения: {app_url}")
                await page.goto(app_url, wait_until="domcontentloaded", timeout=60000)
                # Ждем прохождения Cloudflare если есть
                await self.wait_for_cloudflare(page, max_wait=60)
                await asyncio.sleep(3)

                # Получаем версию со страницы
                page_version = await self.extract_version_from_page(app_url)

                # Шаг 1: Ищем ссылку "Скачать APK"
                print("🔍 Ищем ссылку 'Скачать APK'...")
                download_link = None
                selectors_to_try = [
                    "a.button.is-success.is-fullwidth",
                    "a.button.is-success",
                    "a[href*='/download/apk']",
                    "a[href*='/download/']",
                    "div.download a.button"
                ]
                for selector in selectors_to_try:
                    try:
                        print(f"   Пробуем селектор: {selector}")
                        elements = await page.query_selector_all(selector)
                        for element in elements:
                            href = await element.get_attribute("href")
                            text = await element.inner_text()
                            print(f"     Найден элемент: href={href}, text={text.strip()[:30]}")
                            if href and ('/download/' in href or 'apk' in href.lower()):
                                download_link = element
                                print(f"   ✅ Выбран элемент с href: {href}")
                                break
                        if download_link:
                            break
                    except Exception as e:
                        print(f"     Ошибка с селектором {selector}: {e}")
                        continue
                if not download_link:
                    raise Exception("Не удалось найти ссылку 'Скачать APK'")

                href = await download_link.get_attribute("href")
                if not href:
                    raise Exception("Не удалось получить href ссылки")
                # Приводим ссылку к полному виду
                if href.startswith('/'):
                    download_page_url = f"https://apkcombo.com{href}"
                else:
                    download_page_url = href
                print(f"➡️ Ссылка на страницу загрузки: {download_page_url}")

                # Шаг 2: Переходим на страницу загрузки
                await page.goto(download_page_url, wait_until="domcontentloaded", timeout=120000)
                await self.wait_for_cloudflare(page, max_wait=60)
                await asyncio.sleep(5)

                # Шаг 3: Ищем первый вариант файла в ul.file-list
                print("🔍 Ищем первый вариант файла в ul.file-list...")
                variant_selectors = [
                    "ul.file-list li a",
                    "ul.file-list a",
                    ".file-list li a",
                    ".file-list a"
                ]
                variant = None
                for selector in variant_selectors:
                    try:
                        print(f"   Ищем варианты с селектором: {selector}")
                        variant = await page.wait_for_selector(selector, timeout=15000)
                        if variant:
                            print(f"   ✅ Найден вариант с селектором: {selector}")
                            break
                    except:
                        continue
                if not variant:
                    raise Exception("Не удалось найти варианты загрузки в ul.file-list")

                # Получаем информацию о файле
                try:
                    file_type_element = await variant.query_selector("span.vtype span, .type-apk, .type-xapk")
                    file_type = await file_type_element.inner_text() if file_type_element else "APK"
                    version_element = await variant.query_selector("span.vername")
                    version = await version_element.inner_text() if version_element else "Unknown"
                    print(f"📦 Найден файл: {version} ({file_type})")
                except:
                    file_type = "APK"
                    version = "Unknown"

                # Получаем r2 ссылку
                r2_href = await variant.get_attribute("href")
                if not r2_href:
                    raise Exception("Не удалось найти r2 ссылку варианта загрузки")

                # Приводим r2 ссылку к полному виду
                if r2_href.startswith('/'):
                    r2_url = f"https://apkcombo.com{r2_href}"
                else:
                    r2_url = r2_href
                print(f"🔗 Найдена r2 ссылка: {r2_url}")

                # Шаг 4: Скачиваем файл по r2 ссылке
                downloaded_file = await self.download_file_from_r2_url(page, r2_url)
                
                # Возвращаем версию со страницы если есть, иначе версию из файла
                final_version = page_version if page_version else version
                return downloaded_file, final_version
                
            except Exception as e:
                print(f"❌ Ошибка: {e}")
                print(f"🔍 Текущий URL: {page.url}")
                # Сохраняем скриншот для отладки
                try:
                    await page.screenshot(path="debug_screenshot.png", full_page=True)
                    print("📸 Скриншот сохранен: debug_screenshot.png")
                except:
                    pass
                return None, None
            finally:
                await context.close()
                await browser.close()
                print("🔒 Браузер закрыт")
