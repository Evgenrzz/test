#!/usr/bin/env python3
"""
Cloudflare Downloader (Headless) - для серверов без GUI
Обходит JS-челлендж и скачивает файлы в headless режиме
"""
import asyncio
import sys
import traceback
from pathlib import Path
from playwright.async_api import async_playwright
import time
from urllib.parse import urlparse
class CloudflareDownloaderHeadless:
    def __init__(self, download_dir="/www/wwwroot/tools.bromod.ru/5PLAYpy/downloads"):
        self.download_dir = Path(download_dir)
        self.download_dir.mkdir(parents=True, exist_ok=True)

    async def setup_browser(self):
        """Настройка браузера для обхода Cloudflare в headless режиме"""
        print("🎭 Запуск headless браузера для обхода Cloudflare...")

        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(
            headless=True,  # Headless режим для серверов
            args=[
                '--no-sandbox',
                '--disable-dev-shm-usage',
                '--disable-blink-features=AutomationControlled',
                '--disable-extensions',
                '--no-first-run',
                '--disable-default-apps',
                '--disable-features=TranslateUI',
                '--disable-ipc-flooding-protection',
                '--disable-web-security',
                '--allow-running-insecure-content',
                '--ignore-certificate-errors',
                '--ignore-ssl-errors',
                '--ignore-certificate-errors-spki-list',
                '--disable-features=VizDisplayCompositor'
            ]
        )

        self.context = await self.browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            locale='en-US',
            timezone_id='America/New_York',
            accept_downloads=True,
            extra_http_headers={
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
                'Accept-Language': 'en-US,en;q=0.9',
                'Accept-Encoding': 'gzip, deflate, br',
                'Cache-Control': 'max-age=0',
                'Sec-Fetch-Dest': 'document',
                'Sec-Fetch-Mode': 'navigate',
                'Sec-Fetch-Site': 'none',
                'Sec-Fetch-User': '?1',
                'Upgrade-Insecure-Requests': '1',
                'sec-ch-ua': '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
                'sec-ch-ua-mobile': '?0',
                'sec-ch-ua-platform': '"Windows"'
            }
        )

        self.page = await self.context.new_page()

        # Скрываем автоматизацию более тщательно
        await self.page.add_init_script("""
            // Удаляем webdriver property
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined,
            });

            // Добавляем chrome объект
            window.chrome = {
                runtime: {},
                loadTimes: function() {},
                csi: function() {},
                app: {}
            };

            // Переопределяем plugins
            Object.defineProperty(navigator, 'plugins', {
                get: () => [1, 2, 3, 4, 5],
            });

            // Переопределяем languages
            Object.defineProperty(navigator, 'languages', {
                get: () => ['en-US', 'en'],
            });

            // Переопределяем permissions
            const originalQuery = window.navigator.permissions.query;
            window.navigator.permissions.query = (parameters) => (
                parameters.name === 'notifications' ?
                    Promise.resolve({ state: Notification.permission }) :
                    originalQuery(parameters)
            );

            // Убираем automation флаги
            delete window.cdc_adoQpoasnfa76pfcZLmcfl_Array;
            delete window.cdc_adoQpoasnfa76pfcZLmcfl_Promise;
            delete window.cdc_adoQpoasnfa76pfcZLmcfl_Symbol;
        """)

        print("✅ Headless браузер настроен для обхода Cloudflare")

    async def bypass_cloudflare_and_download(self, file_url):
        """Обходит Cloudflare и скачивает файл в headless режиме"""
        try:
            print(f"🔗 Начинаем обход Cloudflare для: {file_url}")

            # Настраиваем обработчик скачивания
            download_info = {'downloads': [], 'completed_files': []}

            async def handle_download(download):
                try:
                    filename = download.suggested_filename
                    if not filename:
                        # Извлекаем имя файла из URL
                        parsed_url = urlparse(file_url)
                        filename = parsed_url.path.split('/')[-1]
                        if not filename or not filename.endswith('.apk'):
                            filename = f"downloaded_file_{int(time.time())}.apk"

                    print(f"📥 Начато скачивание: {filename}")
                    download_info['downloads'].append(download)

                    filepath = self.download_dir / filename
                    print(f"💾 Сохраняем как: {filepath}")

                    await download.save_as(filepath)
                    download_info['completed_files'].append(str(filepath))

                    print(f"✅ Файл сохранен: {filepath}")

                    if filepath.exists():
                        size_mb = filepath.stat().st_size / (1024 * 1024)
                        print(f"📊 Размер файла: {size_mb:.2f} MB")

                        if size_mb > 100:
                            print("🎉 Отличный размер файла!")
                        elif size_mb > 10:
                            print("✅ Файл скачан успешно")
                        else:
                            print("⚠️ Файл может быть неполным")

                except Exception as e:
                    print(f"⚠️ Ошибка в обработчике скачивания: {e}")

            # Подключаем обработчик скачивания
            self.page.on("download", handle_download)

            # Переходим на страницу с файлом
            print(f"🌐 Переходим на страницу: {file_url}")

            try:
                response = await self.page.goto(file_url, wait_until='domcontentloaded', timeout=60000)
                print(f"📄 Статус ответа: {response.status}")
            except Exception as goto_error:
                if "Download is starting" in str(goto_error):
                    print("✅ Скачивание началось сразу при переходе")
                else:
                    print(f"⚠️ Ошибка перехода: {goto_error}")

            # Проверяем, есть ли Cloudflare челлендж
            print("🔍 Проверяем наличие Cloudflare челленджа...")

            # Ждем и проверяем различные индикаторы Cloudflare
            cloudflare_selectors = [
                '[data-ray]',  # Cloudflare Ray ID
                '.cf-browser-verification',  # Страница верификации
                '#cf-content',  # Контент Cloudflare
                'title:has-text("Just a moment")',  # Заголовок челленджа
                'h1:has-text("Checking your browser")',  # Текст проверки
                '.cf-spinner-allow-5-seconds'  # Спиннер ожидания
            ]

            cloudflare_detected = False
            for selector in cloudflare_selectors:
                try:
                    element = self.page.locator(selector).first
                    if await element.is_visible(timeout=5000):
                        print(f"🛡️ Обнаружен Cloudflare челлендж: {selector}")
                        cloudflare_detected = True
                        break
                except:
                    continue

            if cloudflare_detected:
                print("⏳ Ожидаем прохождения Cloudflare челленджа (headless)...")

                # Ждем прохождения челленджа (до 60 секунд в headless)
                wait_time = 0
                while wait_time < 60:
                    await self.page.wait_for_timeout(1000)
                    wait_time += 1

                    # Проверяем, прошел ли челлендж
                    try:
                        # Если появился контент или началось скачивание
                        if download_info['downloads']:
                            print("✅ Cloudflare челлендж пройден - скачивание началось!")
                            break

                        # Проверяем изменение URL или исчезновение челленджа
                        current_url = self.page.url
                        title = await self.page.title()

                        if 'just a moment' not in title.lower() and 'checking' not in title.lower():
                            print("✅ Cloudflare челлендж пройден - страница изменилась!")
                            break

                    except:
                        pass

                    if wait_time % 10 == 0:
                        print(f"⏳ Ожидание прохождения челленджа: {wait_time}с")

            # Если скачивание еще не началось, пробуем принудительно
            if not download_info['downloads']:
                print("🔄 Пробуем принудительно начать скачивание...")

                # Несколько попыток с разными стратегиями
                for attempt in range(3):
                    try:
                        print(f"🔄 Попытка {attempt + 1}/3...")
                        await self.page.goto(file_url, wait_until='commit', timeout=30000)
                        await self.page.wait_for_timeout(5000)

                        if download_info['downloads']:
                            break

                    except Exception as retry_error:
                        if "Download is starting" in str(retry_error):
                            print("✅ Скачивание началось при повторном переходе")
                            break
                        else:
                            print(f"⚠️ Попытка {attempt + 1} неудачна: {retry_error}")

            # Ждем начала скачивания
            print("⏳ Ожидаем начала скачивания...")
            wait_time = 0
            while wait_time < 120 and not download_info['downloads']:  # 2 минуты
                await self.page.wait_for_timeout(1000)
                wait_time += 1

                if wait_time % 30 == 0:
                    print(f"⏳ Ожидание начала: {wait_time}с")

            if download_info['downloads']:
                print("📥 Скачивание обнаружено, ожидаем завершения...")

                # Ждем завершения скачивания (до 20 минут для больших файлов)
                wait_time = 0
                while wait_time < 1200 and not download_info['completed_files']:
                    await self.page.wait_for_timeout(1000)
                    wait_time += 1

                    if wait_time % 60 == 0:
                        print(f"⏳ Скачивание: {wait_time//60} мин")

                if download_info['completed_files']:
                    await self.page.wait_for_timeout(3000)
                    return download_info['completed_files'][0]

            print("❌ Скачивание не удалось - файл не найден")
            return None

        except Exception as e:
            print(f"❌ Ошибка при скачивании: {e}")
            print(f"❌ Трейсбек: {traceback.format_exc()}")
            return None

    async def cleanup(self):
        """Безопасная очистка ресурсов"""
        try:
            print("🧹 Очистка ресурсов...")
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

            print("✅ Ресурсы очищены")
        except Exception as e:
            print(f"⚠️ Ошибка при очистке: {e}")

    async def run(self, file_url):
        """Основной метод выполнения"""
        try:
            print("🛡️ Запуск Cloudflare Downloader (Headless)")
            print(f"📁 Папка для загрузки: {self.download_dir}")
            print(f"🔗 URL файла: {file_url}")
            print("=" * 60)

            await self.setup_browser()
            downloaded_file = await self.bypass_cloudflare_and_download(file_url)

            if downloaded_file:
                print("=" * 60)
                print("🎉 СКАЧИВАНИЕ ЗАВЕРШЕНО!")

                file_path = Path(downloaded_file)
                if file_path.exists():
                    size_mb = file_path.stat().st_size / (1024 * 1024)

                    print(f"📱 Файл: {file_path.name}")
                    print(f"📊 Размер: {size_mb:.2f} MB")
                    print(f"📂 Путь: {file_path.absolute()}")

                return downloaded_file
            else:
                print("❌ Не удалось скачать файл")
                return None

        except Exception as e:
            print(f"❌ Критическая ошибка: {e}")
            print(f"❌ Трейсбек: {traceback.format_exc()}")
            return None
        finally:
            await self.cleanup()
async def main():
    """Главная функция"""
    try:
        print("🛡️ Запуск Cloudflare Downloader (Headless)")

        # URL файла для скачивания
        file_url = "https://s1.spiderdown.com/Endless%20Wander/Endless-Wander-2.4.38-mod.apk"

        download_path = "/www/wwwroot/tools.bromod.ru/5PLAYpy/downloads"

        downloader = CloudflareDownloaderHeadless(download_path)
        result = await downloader.run(file_url)

        if result:
            print(f"\n🎯 Результат: Файл сохранен в {result}")

            file_path = Path(result)
            if file_path.exists():
                size_bytes = file_path.stat().st_size
                size_mb = size_bytes / (1024 * 1024)

                print(f"📊 Детали файла:")
                print(f"   Имя: {file_path.name}")
                print(f"   Размер: {size_mb:.2f} MB ({size_bytes:,} байт)")
                print(f"   Путь: {file_path.absolute()}")
        else:
            print("\n💥 Загрузка не удалась")

    except Exception as e:
        print(f"❌ Ошибка в main(): {e}")
        print(f"❌ Трейсбек: {traceback.format_exc()}")
if __name__ == "__main__":
    asyncio.run(main())
