#!/usr/bin/env python3
"""
Загрузчик для liteapks.com для parser2
Специализирован для работы с модифицированными приложениями
Версия: 2.0 - с поддержкой accordion блоков
"""
import re
import time
from playwright.async_api import async_playwright
from .version_utils import VersionUtils


class LiteAPKsDownloader:
    """Загрузчик для liteapks.com"""
    
    def __init__(self, config):
        self.config = config
        self.version_utils = VersionUtils()
        
    async def extract_version_from_page(self, url):
        """Извлекаем версию со страницы liteapks.com"""
        print(f"🌐 Получаем версию со страницы: {url}")
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True,
                args=self.config['browser_args']
            )
            
            try:
                page = await browser.new_page()
                await page.set_extra_http_headers({
                    'User-Agent': self.config['user_agent']
                })
                
                # Проверяем Cloudflare
                print("🔄 Проверяем наличие Cloudflare...")
                await page.goto(url, wait_until='networkidle', timeout=self.config['page_load_timeout'])
                
                # Ждем загрузки Cloudflare если есть
                try:
                    await page.wait_for_selector('body', timeout=10000)
                    body_text = await page.inner_text('body')
                    if 'cloudflare' in body_text.lower():
                        print("⏳ Обнаружен Cloudflare, ожидаем...")
                        await page.wait_for_timeout(5000)
                        await page.reload(wait_until='networkidle')
                        print("✅ Cloudflare проверка пройдена или отсутствует")
                    else:
                        print("✅ Cloudflare проверка пройдена или отсутствует")
                except:
                    print("✅ Cloudflare проверка пройдена или отсутствует")
                
                # Ищем версию на странице
                version = await self._find_version_on_page(page)
                
                return version
                
            except Exception as e:
                print(f"❌ Ошибка при загрузке страницы: {e}")
                return None
            finally:
                await browser.close()
    
    async def _find_version_on_page(self, page):
        """Ищем версию на странице используя различные селекторы"""
        selectors = self.config['liteapks']['version_selectors']
        
        for selector in selectors:
            try:
                elements = await page.query_selector_all(selector)
                for element in elements:
                    text = await element.inner_text()
                    version = self.version_utils.extract_clean_version(text)
                    if version:
                        print(f"✅ Найдена версия через селектор '{selector}': {version}")
                        return version
            except Exception as e:
                print(f"⚠️ Ошибка с селектором '{selector}': {e}")
                continue
        
        # Если версия не найдена через селекторы, ищем в тексте страницы
        print("🔍 Ищем версию в тексте страницы...")
        try:
            page_text = await page.inner_text('body')
            print(f"📄 Получен текст страницы ({len(page_text)} символов)")
            
            version_patterns = [
                r'Version\s*:?\s*(\d+\.\d+\.\d+)',
                r'Версия\s*:?\s*(\d+\.\d+\.\d+)',
                r'v(\d+\.\d+\.\d+)',
                r'(\d+\.\d+\.\d+)',
                r'(\d+\.\d+)'
            ]
            
            for pattern in version_patterns:
                matches = re.findall(pattern, page_text, re.IGNORECASE)
                if matches:
                    version = matches[0]
                    print(f"✅ Найдена версия в тексте страницы: {version}")
                    return version
            
            print("❌ Версия не найдена в тексте страницы")
            
        except Exception as e:
            print(f"❌ Ошибка поиска в тексте страницы: {e}")
        
        print("⚠️ Версия не найдена на странице")
        return None
    
    async def extract_download_links(self, url):
        """Извлекаем ссылки для скачивания"""
        print(f"🔗 Извлекаем ссылки для скачивания: {url}")
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True,
                args=self.config['browser_args']
            )
            
            try:
                page = await browser.new_page()
                await page.set_extra_http_headers({
                    'User-Agent': self.config['user_agent']
                })
                
                # Загружаем страницу
                await page.goto(url, wait_until='networkidle', timeout=self.config['page_load_timeout'])
                
                # Ждем загрузки Cloudflare если есть
                try:
                    await page.wait_for_selector('body', timeout=10000)
                    body_text = await page.inner_text('body')
                    if 'cloudflare' in body_text.lower():
                        print("⏳ Обнаружен Cloudflare, ожидаем...")
                        await page.wait_for_timeout(5000)
                        await page.reload(wait_until='networkidle')
                except:
                    pass
                
                # Ищем ссылки для скачивания
                download_links = await self._find_download_links(page, url)
                
                return download_links
                
            except Exception as e:
                print(f"❌ Ошибка при извлечении ссылок: {e}")
                return []
            finally:
                await browser.close()
    
    async def _find_download_links(self, page, original_url):
        """Ищем ссылки для скачивания на странице liteapks.com"""
        print("🔧 LiteAPKs Downloader v2.0 - с поддержкой accordion блоков")
        links = []
        
        try:
            # Ищем блоки с версиями в accordion
            print("🔍 Ищем блоки с версиями в accordion...")
            
            # Проверяем, есть ли accordion на странице
            accordion_element = await page.query_selector('#accordion-versions')
            if accordion_element:
                print("✅ Найден элемент #accordion-versions")
            else:
                print("❌ Элемент #accordion-versions не найден")
                
                # Ищем альтернативные селекторы для блоков с версиями
                alternative_selectors = [
                    '.accordion',
                    '.version-item',
                    '.download-section',
                    '.app-versions',
                    '[class*="version"]',
                    '[class*="accordion"]'
                ]
                
                for selector in alternative_selectors:
                    elements = await page.query_selector_all(selector)
                    if elements:
                        print(f"🔍 Найдено {len(elements)} элементов с селектором: {selector}")
                        
                        # Проверяем, есть ли в них ссылки на скачивание
                        for i, element in enumerate(elements[:3]):  # Проверяем только первые 3
                            links = await element.query_selector_all('a[href*="download"]')
                            if links:
                                print(f"   ✅ В элементе {i+1} найдено {len(links)} ссылок на скачивание")
                                for link in links:
                                    href = await link.get_attribute('href')
                                    text = await link.inner_text()
                                    print(f"      🔗 {text.strip()[:50]} -> {href}")
                            else:
                                print(f"   ❌ В элементе {i+1} нет ссылок на скачивание")
            
            # Ищем все блоки с версиями
            version_blocks = await page.query_selector_all('#accordion-versions .border.rounded.mb-2')
            
            # Если не нашли стандартные блоки, ищем альтернативные
            if not version_blocks:
                print("🔍 Ищем альтернативные блоки с версиями...")
                
                # Пробуем найти блоки с версиями по другим селекторам
                alternative_block_selectors = [
                    '.accordion .border.rounded.mb-2',
                    '.version-item',
                    '.download-section',
                    '.app-versions .border',
                    '[class*="version"] .border',
                    '.card-body .border'
                ]
                
                for selector in alternative_block_selectors:
                    version_blocks = await page.query_selector_all(selector)
                    if version_blocks:
                        print(f"✅ Найдено {len(version_blocks)} блоков с селектором: {selector}")
                        break
                
                if not version_blocks:
                    print("❌ Не найдены блоки с версиями")
            
            if version_blocks:
                print(f"📦 Найдено {len(version_blocks)} блоков с версиями")
                
                # Выбираем первый блок (самую новую версию)
                for i, block in enumerate(version_blocks):
                    try:
                        # Ищем ссылку на скачивание в блоке с различными селекторами
                        download_link_selectors = [
                            'a.btn.btn-light.btn-sm.btn-block',
                            'a.btn.btn-light.btn-sm',
                            'a.btn.btn-light',
                            'a.btn.btn-primary',
                            'a[href*="download"]',
                            'a[href*="liteapks.com/download"]'
                        ]
                        
                        download_link = None
                        for selector in download_link_selectors:
                            download_link = await block.query_selector(selector)
                            if download_link:
                                print(f"🔍 Найдена ссылка с селектором: {selector}")
                                break
                        
                        if download_link:
                            href = await download_link.get_attribute('href')
                            if href and ('liteapks.com/download/' in href or href.startswith('https://')):
                                print(f"🔗 Найдена ссылка в блоке {i+1}: {href}")
                                
                                # Переходим по ссылке и ищем финальную ссылку на файл
                                final_url = await self._get_final_download_url(page, href)
                                if final_url:
                                    # Получаем информацию о версии из блока
                                    version_text = await block.query_selector('a.h6')
                                    if not version_text:
                                        version_text = await block.query_selector('.h6')
                                    if not version_text:
                                        version_text = await block.query_selector('h6')
                                    if not version_text:
                                        version_text = await block.query_selector('[class*="version"]')
                                    
                                    version_info = await version_text.inner_text() if version_text else f"Version {i+1}"
                                    
                                    links.append({
                                        'url': final_url,
                                        'text': version_info.strip(),
                                        'type': 'accordion',
                                        'original_url': href
                                    })
                                    print(f"✅ Финальная ссылка: {final_url}")
                                    break  # Берем только первую (самую новую) версию
                    except Exception as e:
                        print(f"⚠️ Ошибка обработки блока {i+1}: {e}")
                        continue
            
            # Если не нашли в accordion, ищем обычные ссылки
            if not links:
                print("🔍 Accordion не найден или пуст, ищем обычные ссылки для скачивания...")
                
                # Ищем все ссылки с href
                all_links = await page.query_selector_all('a[href]')
                print(f"🔍 Найдено {len(all_links)} ссылок на странице")
                
                for link in all_links:
                    href = await link.get_attribute('href')
                    if href and self._is_download_link(href):
                        # Проверяем текст ссылки
                        text = await link.inner_text()
                        if text and any(keyword in text.lower() for keyword in ['download', 'скачать', 'download apk', 'download mod']):
                            print(f"🔗 Найдена ссылка: {text.strip()} -> {href}")
                            links.append({
                                'url': href,
                                'text': text.strip(),
                                'type': 'direct'
                            })
                
                # Ищем кнопки скачивания
                selectors = self.config['liteapks']['download_selectors']
                for selector in selectors:
                    try:
                        buttons = await page.query_selector_all(selector)
                        for button in buttons:
                            # Проверяем onclick или href
                            onclick = await button.get_attribute('onclick')
                            href = await button.get_attribute('href')
                            
                            if onclick and 'download' in onclick.lower():
                                # Извлекаем URL из onclick
                                url_match = re.search(r'["\']([^"\']*download[^"\']*)["\']', onclick)
                                if url_match:
                                    links.append({
                                        'url': url_match.group(1),
                                        'text': await button.inner_text(),
                                        'type': 'onclick'
                                    })
                            elif href and self._is_download_link(href):
                                links.append({
                                    'url': href,
                                    'text': await button.inner_text(),
                                    'type': 'button'
                                })
                    except Exception as e:
                        print(f"⚠️ Ошибка с селектором '{selector}': {e}")
                        continue
        
        except Exception as e:
            print(f"⚠️ Ошибка при поиске ссылок: {e}")
        
        # Если не нашли ссылок, пробуем упрощенную логику
        if not links:
            print("🔍 Пробуем упрощенную логику: ищем основные ссылки для скачивания...")
            
            # Ищем ссылки с ключевыми словами
            download_selectors = [
                'a[href*="download"]',
                'a[href*="Download"]',
                'a.btn.btn-primary',
                'a.btn.btn-success'
            ]
            
            for selector in download_selectors:
                try:
                    download_links = await page.query_selector_all(selector)
                    for link in download_links:
                        href = await link.get_attribute('href')
                        if href and 'liteapks.com/download/' in href:
                            print(f"🔗 Найдена ссылка: {href}")
                            
                            # Применяем упрощенную логику: добавляем "/1" к URL
                            modified_url = href + "/1"
                            print(f"🔄 Модифицированный URL: {modified_url}")
                            
                            # Переходим по модифицированному URL и ищем spiderdown.com ссылку
                            spiderdown_url = await self._get_spiderdown_link(page, modified_url)
                            if spiderdown_url:
                                links.append({
                                    'url': spiderdown_url,
                                    'text': 'Download APK',
                                    'type': 'spiderdown'
                                })
                                break
                except Exception as e:
                    print(f"⚠️ Ошибка с селектором '{selector}': {e}")
                    continue
        
        # Убираем дубли
        unique_links = []
        seen_urls = set()
        for link in links:
            if link['url'] not in seen_urls:
                unique_links.append(link)
                seen_urls.add(link['url'])
        
        print(f"🔗 Найдено {len(unique_links)} уникальных ссылок для скачивания")
        for i, link in enumerate(unique_links, 1):
            print(f"   {i}. {link['text']} -> {link['url']}")
        
        return unique_links
    
    async def _get_final_download_url(self, page, download_url):
        """Получаем финальную ссылку на файл, переходя по промежуточной ссылке"""
        try:
            print(f"🔗 Переходим по промежуточной ссылке: {download_url}")
            
            # Переходим на страницу скачивания
            await page.goto(download_url, wait_until='networkidle', timeout=30000)
            
            # Ждем загрузки страницы
            await page.wait_for_timeout(2000)
            
            # Ищем финальную ссылку на скачивание
            final_link_selectors = [
                'a.btn.btn-primary.px-5.download',
                'a[href*=".apk"]',
                'a[download]',
                'a.btn-primary[href*="http"]'
            ]
            
            for selector in final_link_selectors:
                try:
                    final_link = await page.query_selector(selector)
                    if final_link:
                        final_url = await final_link.get_attribute('href')
                        if final_url and (final_url.endswith('.apk') or 'spiderdown.com' in final_url):
                            print(f"✅ Найдена финальная ссылка: {final_url}")
                            return final_url
                except Exception as e:
                    print(f"⚠️ Ошибка с селектором '{selector}': {e}")
                    continue
            
            # Если не нашли через селекторы, ищем в тексте страницы
            page_content = await page.content()
            apk_urls = re.findall(r'https?://[^\s<>"]+\.apk', page_content)
            if apk_urls:
                final_url = apk_urls[0]
                print(f"✅ Найдена ссылка в тексте: {final_url}")
                return final_url
            
            print("❌ Финальная ссылка не найдена")
            return None
            
        except Exception as e:
            print(f"❌ Ошибка получения финальной ссылки: {e}")
            return None
    
    async def _get_spiderdown_link(self, page, download_url):
        """Получаем ссылку на spiderdown.com, переходя по модифицированному URL"""
        try:
            print(f"🔗 Переходим по модифицированной ссылке: {download_url}")
            
            # Переходим на страницу скачивания с добавлением "/1"
            await page.goto(download_url, wait_until='networkidle', timeout=30000)
            
            # Ждем загрузки страницы
            await page.wait_for_timeout(2000)
            
            # Ищем ссылку на spiderdown.com
            page_content = await page.content()
            spiderdown_urls = re.findall(r'https?://[^\s<>"]*spiderdown\.com[^\s<>"]*', page_content)
            if spiderdown_urls:
                spiderdown_url = spiderdown_urls[0]
                print(f"✅ Найдена ссылка на spiderdown.com: {spiderdown_url}")
                return spiderdown_url
            
            print("❌ Ссылка на spiderdown.com не найдена")
            return None
            
        except Exception as e:
            print(f"❌ Ошибка получения ссылки на spiderdown.com: {e}")
            return None
    
    def _is_download_link(self, url):
        """Проверяем, является ли ссылка ссылкой для скачивания"""
        if not url:
            return False
        
        url_lower = url.lower()
        
        # Проверяем расширения файлов
        download_extensions = ['.apk', '.xapk', '.zip']
        if any(url_lower.endswith(ext) for ext in download_extensions):
            return True
        
        # Проверяем ключевые слова в URL
        download_keywords = ['download', 'dl', 'file', 'get', 'fetch']
        if any(keyword in url_lower for keyword in download_keywords):
            return True
        
        # Проверяем домены для скачивания
        download_domains = ['mediafire', 'drive.google', 'mega.nz', 'dropbox', 'spiderdown.com']
        if any(domain in url_lower for domain in download_domains):
            return True
        
        # Проверяем ссылки liteapks.com
        if 'liteapks.com/download/' in url_lower:
            return True
        
        return False
    
    def extract_app_info(self, url):
        """Извлекаем информацию о приложении из URL"""
        info = {
            'package_name': self.version_utils.extract_package_name_from_url(url),
            'source_priority': self.version_utils.get_source_priority(url),
            'mod_type': 'unknown'
        }
        
        # Определяем тип модификации по URL
        if 'liteapks.com' in url:
            info['mod_type'] = 'liteapks'
        
        return info