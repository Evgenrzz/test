#!/usr/bin/env python3
"""
Модуль для извлечения версий приложений
"""
import re
import asyncio
from playwright.async_api import async_playwright
from config import BROWSER_ARGS, USER_AGENT, CLOUDFLARE_TIMEOUT


class VersionExtractor:
    def __init__(self):
        pass

    def extract_version_from_filename(self, filename):
        """Извлекаем версию из имени файла"""
        print(f"🔍 Извлекаем версию из файла: {filename}")
        
        # Убираем расширение и _apkcombo.com
        clean_name = filename.replace('.xapk', '').replace('.apk', '').replace('_apkcombo.com', '')
        
        # Паттерны для поиска версии
        version_patterns = [
            r'_(\d+\.\d+\.\d+\.\d+)',  # _1.8.3.1
            r'_(\d+\.\d+\.\d+)',       # _1.8.3
            r'_(\d+\.\d+)',            # _1.8
            r'v(\d+\.\d+\.\d+\.\d+)',  # v1.8.3.1
            r'v(\d+\.\d+\.\d+)',       # v1.8.3
            r'v(\d+\.\d+)',            # v1.8
            r'(\d+\.\d+\.\d+\.\d+)',   # 1.8.3.1
            r'(\d+\.\d+\.\d+)',        # 1.8.3
            r'(\d+\.\d+)',             # 1.8
        ]

        for pattern in version_patterns:
            match = re.search(pattern, clean_name)
            if match:
                version = match.group(1)
                print(f"✅ Найдена версия в файле: {version}")
                return version

        print("⚠️ Версия в файле не найдена, используем 1.0.0")
        return "1.0.0"

    async def extract_version_from_page(self, page_url):
        """Извлекаем версию со страницы приложения"""
        print(f"🌐 Извлекаем версию со страницы: {page_url}")
        
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
                await page.goto(page_url, wait_until="domcontentloaded", timeout=30000)
                await self._wait_for_cloudflare(page)
                await asyncio.sleep(2)

                # Ищем версию в различных местах на странице
                version_selectors = [
                    "div.version",           # <div class="version">1.8.3</div>
                    ".version",              # любой элемент с классом version
                    "[class*='version']",    # элементы с классом содержащим version
                    ".app-version",          # альтернативный класс
                    ".current-version",      # еще один вариант
                ]

                for selector in version_selectors:
                    try:
                        element = await page.query_selector(selector)
                        if element:
                            version_text = await element.inner_text()
                            version_text = version_text.strip()
                            
                            # Извлекаем версию из текста
                            version_match = re.search(r'(\d+\.\d+\.\d+(?:\.\d+)?)', version_text)
                            if version_match:
                                version = version_match.group(1)
                                print(f"✅ Найдена версия на странице: {version}")
                                return version
                    except Exception as e:
                        print(f"   Ошибка с селектором {selector}: {e}")
                        continue

                # Если не нашли в специальных элементах, ищем в тексте страницы
                page_content = await page.content()
                version_patterns = [
                    r'<div[^>]*class="version"[^>]*>([^<]+)</div>',
                    r'Version[:\s]+(\d+\.\d+\.\d+(?:\.\d+)?)',
                    r'v(\d+\.\d+\.\d+(?:\.\d+)?)',
                    r'(\d+\.\d+\.\d+(?:\.\d+)?)',
                ]

                for pattern in version_patterns:
                    matches = re.findall(pattern, page_content, re.IGNORECASE)
                    if matches:
                        # Берем первое совпадение, которое выглядит как версия
                        for match in matches:
                            if re.match(r'\d+\.\d+', match):
                                print(f"✅ Найдена версия в контенте страницы: {match}")
                                return match

                print("⚠️ Версия на странице не найдена")
                return None

            except Exception as e:
                print(f"❌ Ошибка извлечения версии со страницы: {e}")
                return None
            finally:
                await context.close()
                await browser.close()

    async def _wait_for_cloudflare(self, page, max_wait=CLOUDFLARE_TIMEOUT):
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

    def extract_app_name_from_filename(self, filename):
        """Извлекаем название приложения из имени файла"""
        # Убираем расширение и _apkcombo.com
        name = filename.replace('.xapk', '').replace('.apk', '').replace('_apkcombo.com', '')
        
        # Убираем версию если есть
        name = re.sub(r'_\d+\.\d+.*$', '', name)
        
        # Заменяем + на пробелы и убираем лишние символы
        name = name.replace('+-+', ' ').replace('+', ' ').replace('-', ' ')
        name = re.sub(r'\s+', ' ', name).strip()
        
        return name

    def get_version(self, filename, page_version=None):
        """Получаем финальную версию для записи в БД"""
        # Приоритет: версия со страницы -> версия из файла -> 1.0.0
        if page_version:
            print(f"🎯 Используем версию со страницы: {page_version}")
            return page_version
        
        file_version = self.extract_version_from_filename(filename)
        print(f"🎯 Используем версию из файла: {file_version}")
        return file_version

