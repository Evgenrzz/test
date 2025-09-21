#!/usr/bin/env python3
"""
Модуль для скачивания файлов с apkcombo.com
"""
import asyncio
import os
import re
import hashlib
from pathlib import Path
from datetime import datetime
from playwright.async_api import async_playwright
from config import BROWSER_ARGS, USER_AGENT, BASE_DOWNLOAD_DIR, CLOUDFLARE_TIMEOUT, PAGE_LOAD_TIMEOUT, DOWNLOAD_TIMEOUT


class FileDownloader:
    def __init__(self):
        self.download_dir = self.get_current_download_dir()

    def get_current_download_dir(self):
        """Получаем папку для текущего месяца в формате год-месяц"""
        now = datetime.now()
        month_dir = f"{now.year}-{now.month:02d}"
        full_path = Path(BASE_DOWNLOAD_DIR) / month_dir
        full_path.mkdir(parents=True, exist_ok=True)
        return full_path

    def calculate_checksum(self, file_path):
        """Вычисляем MD5 чексумму файла"""
        hash_md5 = hashlib.md5()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()

    def normalize_filename(self, filename):
        """Нормализуем имя файла согласно требованиям"""
        print(f"📝 Исходное имя файла: {filename}")

        # Убираем "_apkcombo.com" из названия
        filename = filename.replace('_apkcombo.com', '')

        # Разделяем имя файла и расширение
        name_part, extension = os.path.splitext(filename)

        # Приводим к нижнему регистру
        name_part = name_part.lower()
        extension = extension.lower()

        # Переводим кириллицу в латиницу
        name_part = self._transliterate_cyrillic(name_part)

        # Заменяем +-+ на подчеркивания
        name_part = name_part.replace('+-+', '_')
        name_part = name_part.replace('+', '_')
        name_part = name_part.replace('-', '_')

        # Заменяем точки на подчеркивания в имени файла (но не в расширении)
        name_part = name_part.replace('.', '_')

        # Убираем множественные подчеркивания
        name_part = re.sub(r'_+', '_', name_part).strip('_')

        # Собираем обратно с одной точкой перед расширением
        normalized_filename = f"{name_part}{extension}"

        print(f"📝 Нормализованное имя: {normalized_filename}")
        return normalized_filename

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
            else:
                result += char
        
        return result

    def format_filename_for_attachment(self, filename):
        """Форматируем имя файла для поля apk-original"""
        print(f"📝 Форматируем для attachment: {filename}")

        # Разделяем имя файла и расширение
        name_part, extension = os.path.splitext(filename)

        # Убираем подчеркивания и заменяем на пробелы
        name_part = name_part.replace('_', ' ')

        # Убираем лишние символы +-+
        name_part = name_part.replace('+-+', ' ')
        name_part = name_part.replace('+', ' ')
        name_part = name_part.replace('-', ' ')

        # Убираем множественные пробелы
        name_part = re.sub(r'\s+', ' ', name_part).strip()

        # Восстанавливаем точки в версии (ищем паттерны типа "1 8 3" и заменяем на "1.8.3")
        # Ищем последовательности цифр разделенных пробелами в конце строки
        version_pattern = r'(\d+)\s+(\d+)\s+(\d+)(?:\s+(\d+))?(?:\s+(\d+))?$'
        match = re.search(version_pattern, name_part)
        if match:
            # Заменяем найденную версию на правильный формат с точками
            version_parts = [part for part in match.groups() if part is not None]
            version_str = '.'.join(version_parts)
            name_part = re.sub(version_pattern, version_str, name_part)

        # Собираем обратно
        formatted_filename = f"{name_part}{extension}"

        print(f"📝 Отформатированное имя: {formatted_filename}")
        return formatted_filename

    async def wait_for_cloudflare(self, page, max_wait=CLOUDFLARE_TIMEOUT):
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
            await page.goto(r2_url, wait_until="domcontentloaded", timeout=PAGE_LOAD_TIMEOUT)
        except Exception as e:
            if "Download is starting" in str(e):
                print("✅ Загрузка началась сразу при переходе")
                await asyncio.sleep(2)
            else:
                raise e

        # Если загрузка не началась сразу, ждем прохождения Cloudflare
        if not download_started:
            print("🔄 Загрузка не началась сразу, проверяем Cloudflare...")
            await self.wait_for_cloudflare(page, max_wait=CLOUDFLARE_TIMEOUT)
            # Ждем начала загрузки еще немного
            for i in range(DOWNLOAD_TIMEOUT):
                if download_started:
                    break
                await asyncio.sleep(1)
                if i % 5 == 0:
                    print(f"   Ждем загрузку... ({i+1}/{DOWNLOAD_TIMEOUT})")

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

    async def download_from_apkcombo(self, app_url):
        """Скачиваем файл с apkcombo.com"""
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True,
                args=BROWSER_ARGS
            )
            context = await browser.new_context(
                accept_downloads=True,
                user_agent=USER_AGENT
            )
            page = await context.new_page()

            try:
                print(f"📱 Открываем страницу приложения: {app_url}")
                await page.goto(app_url, wait_until="domcontentloaded", timeout=PAGE_LOAD_TIMEOUT)
                # Ждем прохождения Cloudflare если есть
                await self.wait_for_cloudflare(page, max_wait=CLOUDFLARE_TIMEOUT)
                await asyncio.sleep(3)

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
                await page.goto(download_page_url, wait_until="domcontentloaded", timeout=PAGE_LOAD_TIMEOUT)
                await self.wait_for_cloudflare(page, max_wait=CLOUDFLARE_TIMEOUT)
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
                return downloaded_file, version
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

