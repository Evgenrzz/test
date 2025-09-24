#!/usr/bin/env python3
"""
Загрузчик файлов для parser2
Специализирован для работы с модифицированными приложениями
"""
import os
import re
import time
import hashlib
import aiohttp
import asyncio
from pathlib import Path
from .version_utils import VersionUtils


class FileDownloader:
    """Загрузчик файлов"""
    
    def __init__(self, config):
        self.config = config
        self.version_utils = VersionUtils()
        
    async def download_file(self, url, download_dir, filename=None):
        """Скачиваем файл"""
        print(f"📥 Скачиваем файл: {url}")
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=self.config['download_timeout']) as response:
                    if response.status == 200:
                        # Определяем имя файла
                        if not filename:
                            filename = self._get_filename_from_response(response, url)
                        
                        # Очищаем имя файла для spiderdown.com
                        filename = self._clean_spiderdown_filename(filename)
                        
                        # Создаем полный путь
                        file_path = download_dir / filename
                        
                        # Скачиваем файл
                        with open(file_path, 'wb') as f:
                            async for chunk in response.content.iter_chunked(8192):
                                f.write(chunk)
                        
                        file_size = file_path.stat().st_size
                        print(f"✅ Файл скачан: {filename} ({file_size} байт)")
                        
                        return file_path, file_size
                    else:
                        print(f"❌ Ошибка скачивания: HTTP {response.status}")
                        return None, 0
                        
        except Exception as e:
            print(f"❌ Ошибка скачивания файла: {e}")
            return None, 0
    
    def _get_filename_from_response(self, response, url):
        """Получаем имя файла из ответа или URL"""
        # Пробуем получить из Content-Disposition
        content_disposition = response.headers.get('Content-Disposition', '')
        if content_disposition:
            filename_match = re.search(r'filename[*]?=["\']?([^"\';]+)', content_disposition)
            if filename_match:
                return filename_match.group(1).strip()
        
        # Пробуем получить из URL
        url_path = url.split('/')[-1]
        if url_path and '.' in url_path:
            return url_path
        
        # Генерируем имя по умолчанию
        return f"downloaded_file_{int(time.time())}.apk"
    
    def _clean_spiderdown_filename(self, filename):
        """Очищаем имя файла от суффикса -9mod.com"""
        # Убираем "-9mod.com" из имени файла
        if "-9mod.com" in filename:
            # Разделяем имя файла и расширение
            name, ext = os.path.splitext(filename)
            # Убираем "-9mod.com" из имени
            cleaned_name = name.replace("-9mod.com", "")
            # Формируем новое имя файла
            filename = cleaned_name + ext
            print(f"🧹 Очищено имя файла: {filename}")
        
        return filename
    
    def calculate_checksum(self, file_path):
        """Вычисляем MD5 чексумму файла"""
        try:
            hash_md5 = hashlib.md5()
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_md5.update(chunk)
            return hash_md5.hexdigest()
        except Exception as e:
            print(f"❌ Ошибка вычисления MD5: {e}")
            return None
    
    def calculate_sha256(self, file_path):
        """Вычисляем SHA-256 хеш файла"""
        try:
            hash_sha256 = hashlib.sha256()
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_sha256.update(chunk)
            return hash_sha256.hexdigest()
        except Exception as e:
            print(f"❌ Ошибка вычисления SHA-256: {e}")
            return None
    
    def normalize_filename(self, filename, app_name, version):
        """Нормализуем имя файла"""
        # Извлекаем расширение
        name, ext = os.path.splitext(filename)
        
        # Очищаем имя приложения
        clean_app_name = re.sub(r'[^\w\s-]', '', app_name).strip()
        clean_app_name = re.sub(r'\s+', '_', clean_app_name)
        
        # Очищаем версию
        clean_version = re.sub(r'[^\w.-]', '', str(version))
        
        # Формируем новое имя
        new_name = f"{self.config['mod']['file_prefix']}_{clean_app_name}_{clean_version}"
        
        # Убираем лишние символы
        new_name = re.sub(r'[_]+', '_', new_name)
        new_name = new_name.strip('_')
        
        return f"{new_name}{ext}"
    
    def create_download_directory(self, base_dir):
        """Создаем директорию для скачивания"""
        from datetime import datetime
        
        # Создаем папку по месяцу
        current_date = datetime.now()
        month_dir = current_date.strftime("%Y-%m")
        
        download_dir = Path(base_dir) / month_dir
        download_dir.mkdir(parents=True, exist_ok=True)
        
        print(f"📁 Создана директория: {download_dir}")
        return download_dir
    
    def delete_old_file(self, file_path):
        """Удаляем старый файл"""
        try:
            if file_path.exists():
                file_path.unlink()
                print(f"🗑️ Удален старый файл: {file_path}")
                return True
            else:
                print(f"ℹ️ Файл не существует: {file_path}")
                return True
        except Exception as e:
            print(f"❌ Ошибка удаления файла: {e}")
            return False
    
    def get_file_info(self, file_path):
        """Получаем информацию о файле"""
        try:
            if not file_path.exists():
                return None
            
            stat = file_path.stat()
            return {
                'size': stat.st_size,
                'modified': stat.st_mtime,
                'created': stat.st_ctime
            }
        except Exception as e:
            print(f"❌ Ошибка получения информации о файле: {e}")
            return None
    
    def validate_file(self, file_path, expected_extensions=None):
        """Проверяем валидность файла"""
        if not file_path.exists():
            return False, "Файл не существует"
        
        # Проверяем размер
        file_size = file_path.stat().st_size
        if file_size == 0:
            return False, "Файл пустой"
        
        # Проверяем расширение
        if expected_extensions:
            ext = file_path.suffix.lower()
            if ext not in expected_extensions:
                return False, f"Неподдерживаемое расширение: {ext}"
        
        return True, "Файл валиден"