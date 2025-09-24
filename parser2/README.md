# Parser2 - Система обработки модифицированных приложений

Parser2 - это специализированная система для автоматического обновления модифицированных Android приложений с различных источников.

## 🚀 Особенности

- **Специализация на модах**: Работа с модифицированными приложениями
- **Поддержка liteapks.com**: Парсинг версий и ссылок для скачивания
- **Отдельная таблица отслеживания**: `file_tracking_mod` для модифицированных приложений
- **Поле mod-at**: Работа с полем `mod-at` вместо `apk-original`
- **Модульная архитектура**: Легкое расширение для новых источников

## 📁 Структура проекта

```
parser2/
├── __init__.py              # Инициализация модуля
├── config.py                # Конфигурация системы
├── main.py                  # Основной модуль обработки
├── database_api.py          # API для работы с базой данных
├── requirements.txt         # Зависимости Python
├── README.md               # Документация
└── lib/                    # Библиотеки
    ├── __init__.py
    ├── liteapks_downloader.py  # Загрузчик для liteapks.com
    ├── file_downloader.py      # Загрузчик файлов
    ├── duplicate_analyzer.py   # Анализатор дублей
    └── version_utils.py        # Утилиты для работы с версиями
```

## ⚙️ Конфигурация

### Основные настройки в `config.py`:

```python
# API конфигурация
API_CONFIG = {
    'url': 'https://5play.dev/api_script.php',
    'key': 'GBpk54ey547h54',
    'timeout': 30
}

# Пути и настройки файлов
LINKS_FILE = "step5mod_links.txt"
BASE_DOWNLOAD_DIR = "/www/n2.anplus1.com/files/mod"  # Отдельная папка для модов

# Настройки для модифицированных приложений
MOD_CONFIG = {
    'supported_formats': ['.apk', '.xapk'],
    'mod_types': ['premium', 'unlocked', 'pro', 'mod', 'hack'],
    'field_name': 'mod-at',  # Поле в xfields для модифицированных приложений
    'default_priority': 60,  # Приоритет для модифицированных приложений
    'file_prefix': 'MOD'  # Префикс для файлов модов
}
```

## 🗄️ База данных

### Таблица отслеживания модов: `file_tracking_mod`

```sql
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
```

## 📝 Формат файла ссылок

Файл `step5mod_links.txt` содержит ссылки в формате:

```
ID,[attachment=123:filename.apk],url1;url2;url3
```

Пример:
```
22,[attachment=979:MOD_AIDA64_2.12.apk],https://liteapks.com/aida64/
23,[attachment=980:MOD_WhatsApp_2.24.apk],https://liteapks.com/whatsapp/
```

## 🚀 Использование

### Установка зависимостей:

```bash
pip install -r parser2/requirements.txt
```

### Запуск:

```bash
# Быстрый режим
python parser2.py fast

# Полный режим
python parser2.py full

# С указанием файла ссылок
python parser2.py --links-file my_links.txt
```

## 🔧 API Endpoints

Parser2 использует следующие API endpoints:

- `check_mod_at` - Проверка версии в поле mod-at
- `check_duplicate_mod` - Проверка дублей для модифицированных приложений
- `add_tracking_mod` - Добавление в таблицу отслеживания модов
- `update_mod_at` - Обновление поля mod-at в dle_post
- `create_mod_tracking_table` - Создание таблицы отслеживания модов

## 📊 Логирование

Логи записываются в файл `logs/parser2_log.txt` и перезаписываются при каждом запуске.

## 🔍 Анализ дублей

Система проверяет дубли по:
- SHA-256 хешу (точное совпадение содержимого)
- Названию и версии приложения
- Размеру файла (с допустимым отклонением)

## 🌐 Поддерживаемые источники

- **liteapks.com** - Модифицированные приложения
- Легко добавляются новые источники через модульную архитектуру

## 🔄 Расширение функциональности

Для добавления нового источника:

1. Создайте новый модуль в `lib/` (например, `new_source_downloader.py`)
2. Добавьте конфигурацию в `config.py`
3. Обновите `main.py` для поддержки нового источника

## 📈 Мониторинг

Система предоставляет детальную статистику:
- Количество обработанных файлов
- Успешные загрузки
- Ошибки
- Пропущенные дубли
- Анализ дублей и похожих приложений

## 🛠️ Отладка

Для включения детального логирования установите в `config.py`:

```python
ENABLE_DETAILED_LOGGING = True
```

Это включит:
- Детальный анализ дублей
- Fuzzy matching похожих приложений
- Подробную статистику

