#!/usr/bin/env python3
"""
Конфигурация системы обработки файлов для parser2
Специализирован для работы с модифицированными приложениями
"""

# Конфигурация API
API_CONFIG = {
    'url': 'https://5play.dev/api_script.php',
    'key': 'GBpk54ey547h54',
    'timeout': 30
}
 
# Пути и настройки файлов
LINKS_FILE = "step5mod_links.txt"
BASE_DOWNLOAD_DIR = "/www/n2.anplus1.com/files/mod"  # Отдельная папка для модов

# SQL запросы для создания таблицы отслеживания модов
CREATE_TRACKING_TABLE = """
CREATE TABLE IF NOT EXISTS file_tracking_mod (
    id INT AUTO_INCREMENT PRIMARY KEY,
    news_id INT NOT NULL,
    app_name VARCHAR(255) NOT NULL,
    version VARCHAR(100) NOT NULL,
    file_size BIGINT NOT NULL,
    file_path VARCHAR(500) NOT NULL,
    checksum VARCHAR(32) NOT NULL,
    sha256_hash VARCHAR(64) NULL,
    package_name VARCHAR(255) NULL,
    source_priority INT DEFAULT 0,
    download_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    source_url VARCHAR(500) NOT NULL,
    mod_type VARCHAR(100) NULL,
    mod_features TEXT NULL,
    INDEX idx_news_id (news_id),
    INDEX idx_app_name (app_name),
    INDEX idx_sha256 (sha256_hash),
    INDEX idx_package_name (package_name),
    INDEX idx_source_priority (source_priority),
    INDEX idx_mod_type (mod_type)
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

# Настройки для парсера liteapks.com
LITEAPKS_CONFIG = {
    'base_url': 'https://liteapks.com',
    'search_selectors': [
        '.app-title',
        'h1.app-title',
        '.title'
    ],
    'version_selectors': [
        '.version',
        '.app-version',
        '.ver',
        '[data-version]'
    ],
    'download_selectors': [
        '.download-btn',
        '.download-link',
        'a[href*="download"]',
        '.btn-download'
    ],
    'file_info_selectors': [
        '.file-info',
        '.app-info',
        '.details'
    ]
}

# Настройки для модифицированных приложений
MOD_CONFIG = {
    'supported_formats': ['.apk', '.xapk'],
    'mod_types': ['premium', 'unlocked', 'pro', 'mod', 'hack'],
    'field_name': 'mod-at',  # Поле в xfields для модифицированных приложений
    'default_priority': 60,  # Приоритет для модифицированных приложений
    'file_prefix': 'MOD'  # Префикс для файлов модов
}

