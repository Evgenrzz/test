#!/usr/bin/env python3
"""
Конфигурация системы обработки файлов
"""

# Конфигурация базы данных
DB_CONFIG = {
    'host': '79.174.12.174',
    'database': 'ook',
    'user': 'ook',
    'password': 'LqDP2vrZznr8vxJI7RzN'
}

# Пути и настройки файлов
LINKS_FILE = "step4_links.txt"
BASE_DOWNLOAD_DIR = "/www/n2.anplus1.com/files"

# SQL запросы
CREATE_TRACKING_TABLE = """
CREATE TABLE IF NOT EXISTS file_tracking (
    id INT AUTO_INCREMENT PRIMARY KEY,
    news_id INT NOT NULL,
    app_name VARCHAR(255) NOT NULL,
    version VARCHAR(100) NOT NULL,
    file_size BIGINT NOT NULL,
    file_path VARCHAR(500) NOT NULL,
    checksum VARCHAR(32) NOT NULL,
    sha256_hash VARCHAR(64) NOT NULL,
    package_name VARCHAR(255) NULL,
    source_priority INT DEFAULT 0,
    download_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    source_url VARCHAR(500) NOT NULL,
    INDEX idx_news_id (news_id),
    INDEX idx_app_name (app_name),
    INDEX idx_sha256 (sha256_hash),
    INDEX idx_package_name (package_name),
    INDEX idx_source_priority (source_priority)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
"""

# Настройки браузера
BROWSER_ARGS = [
    "--no-sandbox",
    "--disable-blink-features=AutomationControlled",
    "--disable-dev-shm-usage"
]

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

# Таймауты
CLOUDFLARE_TIMEOUT = 120
PAGE_LOAD_TIMEOUT = 60000
DOWNLOAD_TIMEOUT = 30

# Настройки производительности
ENABLE_SHA256_CHECK = True  # Включить проверку SHA-256
ENABLE_FUZZY_MATCHING = True  # Включить fuzzy matching
ENABLE_SIZE_CHECK = True  # Включить проверку по размеру
ENABLE_DETAILED_LOGGING = True  # Включить детальное логирование

