#!/usr/bin/env python3
"""
Модуль для извлечения версий из файлов и веб-страниц
"""
import re
from playwright.async_api import async_playwright
from .config import BROWSER_ARGS, USER_AGENT, CLOUDFLARE_TIMEOUT, PAGE_LOAD_TIMEOUT
from .lib.version_utils import VersionUtils


class VersionExtractor:
    def extract_version_from_filename(self, filename):
        """Извлекаем версию из имени файла с улучшенной обработкой"""
        version = VersionUtils.extract_version_from_text(filename)
        return VersionUtils.normalize_version(version) if version else "1.0.0"

    def extract_app_name_from_filename(self, filename):
        """Извлекаем название приложения из имени файла с улучшенной обработкой"""
        return VersionUtils.extract_app_name_from_filename(filename)

    async def extract_version_from_page(self, url):
        """Извлекаем версию со страницы приложения"""
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
                print(f"🌐 Получаем версию со страницы: {url}")
                await page.goto(url, wait_until="domcontentloaded", timeout=PAGE_LOAD_TIMEOUT)
                
                # Ждем прохождения Cloudflare если есть
                await self._wait_for_cloudflare(page)
                
                # Ищем версию в div.version
                version_selectors = [
                    "div.version",
                    ".version",
                    "[class*='version']",
                    ".app-version"
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
                
            except Exception as e:
                print(f"❌ Ошибка получения версии со страницы: {e}")
                return None
            finally:
                await context.close()
                await browser.close()

    async def _wait_for_cloudflare(self, page, max_wait=CLOUDFLARE_TIMEOUT):
        """Ждем прохождения проверки Cloudflare"""
        import asyncio
        
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

    def extract_clean_version(self, version_text):
        """Извлекаем только номер версии из любого текста с улучшенной обработкой"""
        version = VersionUtils.extract_version_from_text(version_text)
        clean_version = VersionUtils.normalize_version(version) if version else "1.0.0"
        print(f"🧹 Извлечена чистая версия: {clean_version} из '{version_text}'")
        return clean_version

    def get_version(self, filename, page_version=None):
        """Определяем финальную версию для использования"""
        # Приоритет: версия со страницы > версия из файла
        if page_version:
            clean_page_version = self.extract_clean_version(page_version)
            print(f"🎯 Используем версию со страницы: {clean_page_version}")
            return clean_page_version
        
        file_version = self.extract_version_from_filename(filename)
        clean_file_version = self.extract_clean_version(file_version)
        print(f"📁 Используем версию из файла: {clean_file_version}")
        return clean_file_version
    
    def extract_package_name_from_url(self, url):
        """Извлекаем package name из URL"""
        return VersionUtils.extract_package_name_from_url(url)
    
    def get_source_priority(self, source_url):
        """Получаем приоритет источника"""
        return VersionUtils.get_source_priority(source_url)
