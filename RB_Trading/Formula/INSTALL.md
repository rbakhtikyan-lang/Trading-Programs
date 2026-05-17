# 🛠️ Инструкция по установке

Пошаговое руководство по установке и настройке программы для трейдинга.

## Требования

- Python 3.8 или выше
- PostgreSQL 12 или выше
- pip (менеджер пакетов Python)
- Интернет соединение

## Шаг 1: Установка Python

### Ubuntu/Debian
```bash
sudo apt update
sudo apt install python3 python3-pip python3-venv
```

### macOS
```bash
brew install python3
```

### Windows
Скачайте установщик с [python.org](https://www.python.org/downloads/)

## Шаг 2: Установка PostgreSQL

### Ubuntu/Debian
```bash
sudo apt update
sudo apt install postgresql postgresql-contrib
sudo systemctl start postgresql
sudo systemctl enable postgresql
```

### macOS
```bash
brew install postgresql@14
brew services start postgresql@14
```

### Windows
Скачайте установщик с [postgresql.org](https://www.postgresql.org/download/windows/)

## Шаг 3: Настройка PostgreSQL

### 1. Создание базы данных

```bash
# Войти в PostgreSQL как пользователь postgres
sudo -u postgres psql

# Или на macOS/Windows:
psql -U postgres
```

### 2. Выполнить следующие команды в psql:

```sql
-- Создать базу данных
CREATE DATABASE trading_db;

-- Создать пользователя (опционально)
CREATE USER trading_user WITH PASSWORD 'your_strong_password';

-- Дать права пользователю
GRANT ALL PRIVILEGES ON DATABASE trading_db TO trading_user;

-- Подключиться к базе
\c trading_db

-- Дать права на схему
GRANT ALL ON SCHEMA public TO trading_user;

-- Выйти
\q
```

### 3. Импортировать схему базы данных

```bash
# Для пользователя postgres
sudo -u postgres psql -d trading_db -f base.sql

# Или с custom пользователем
psql -U trading_user -d trading_db -f base.sql
```

## Шаг 4: Установка зависимостей Python

### Создание виртуального окружения (рекомендуется)

```bash
# Перейти в директорию проекта
cd trading_program

# Создать виртуальное окружение
python3 -m venv venv

# Активировать виртуальное окружение
# На Linux/macOS:
source venv/bin/activate

# На Windows:
venv\Scripts\activate
```

### Установка пакетов

```bash
pip install -r requirements.txt
```

## Шаг 5: Настройка конфигурации

### Вариант 1: Прямое редактирование main.py

Откройте `main.py` и измените параметры подключения к БД:

```python
def connect_to_db(self):
    try:
        self.conn = psycopg2.connect(
            dbname="trading_db",
            user="postgres",          # Ваш пользователь
            password="your_password",  # Ваш пароль
            host="localhost",
            port="5432"
        )
```

### Вариант 2: Использование переменных окружения (рекомендуется)

```bash
# Скопировать пример конфигурации
cp .env.example .env

# Отредактировать .env файл
nano .env  # или любой другой редактор
```

Затем обновить код для использования .env:

```python
from dotenv import load_dotenv
import os

load_dotenv()

self.conn = psycopg2.connect(
    dbname=os.getenv('DB_NAME', 'trading_db'),
    user=os.getenv('DB_USER', 'postgres'),
    password=os.getenv('DB_PASSWORD'),
    host=os.getenv('DB_HOST', 'localhost'),
    port=os.getenv('DB_PORT', '5432')
)
```

## Шаг 6: Проверка установки

### Тест подключения к PostgreSQL

```bash
psql -U postgres -d trading_db -c "SELECT version();"
```

### Тест Python зависимостей

```bash
python3 -c "import ccxt, psycopg2, colorama; print('Все зависимости установлены!')"
```

### Проверка таблиц в БД

```bash
psql -U postgres -d trading_db -c "\dt"
```

Вы должны увидеть таблицы: candles, analysis_results, support_resistance_levels, event_log

## Шаг 7: Первый запуск

```bash
python3 main.py
```

Если всё настроено правильно, вы увидите:
```
======================================================================
                    ПРОГРАММА ДЛЯ ТРЕЙДИНГА
======================================================================

✓ Успешное подключение к базе данных

──────────────────────────────────────────────────────────────────────
ГЛАВНОЕ МЕНЮ:
──────────────────────────────────────────────────────────────────────
1. Подключиться к CEX
2. Загрузить свечные данные
3. Показать сохраненные данные
4. Выполнить анализ (RB Formula)
5. Статистика по монете
0. Выход
──────────────────────────────────────────────────────────────────────
```

## Шаг 8: Тестовый запуск

### 1. Подключиться к CEX
- Выберите опцию `1`
- Нажмите Enter (demo режим без API ключей)

### 2. Загрузить данные
- Выберите опцию `2`
- Символ: `BTC/USDT`
- Таймфрейм: `1h`
- Количество: `50`
- Сохранить: `y`

### 3. Просмотр данных
- Выберите опцию `3`
- Символ: `BTC/USDT`
- Количество: `10`

### 4. Анализ
- Выберите опцию `4`
- Символ: `BTC/USDT`
- Таймфрейм: `1h`

## Возможные проблемы и решения

### Проблема 1: "ModuleNotFoundError: No module named 'ccxt'"

**Решение:**
```bash
pip install ccxt
```

### Проблема 2: "FATAL: password authentication failed"

**Решение:**
1. Проверьте пароль в конфигурации
2. Убедитесь, что пользователь существует:
```bash
sudo -u postgres psql -c "\du"
```

### Проблема 3: "could not connect to server: Connection refused"

**Решение:**
1. Проверьте, запущен ли PostgreSQL:
```bash
sudo systemctl status postgresql
# или
brew services list | grep postgresql
```

2. Запустите PostgreSQL:
```bash
sudo systemctl start postgresql
# или
brew services start postgresql@14
```

### Проблема 4: "relation 'candles' does not exist"

**Решение:**
Схема БД не импортирована. Выполните:
```bash
sudo -u postgres psql -d trading_db -f base.sql
```

### Проблема 5: "ccxt.NetworkError"

**Решение:**
1. Проверьте интернет соединение
2. Попробуйте другую биржу
3. Подождите несколько минут (возможно rate limit)

### Проблема 6: Символ не найден

**Решение:**
Используйте правильный формат символа:
- ✅ `BTC/USDT`
- ✅ `ETH/USDT`
- ❌ `BTCUSDT`
- ❌ `btc/usdt`

## Дополнительная настройка

### Автозапуск PostgreSQL

**Ubuntu/Debian:**
```bash
sudo systemctl enable postgresql
```

**macOS:**
```bash
brew services start postgresql@14
```

### Создание ярлыка для запуска

**Linux/macOS:**
```bash
echo '#!/bin/bash
cd /path/to/trading_program
source venv/bin/activate
python3 main.py
' > run_trading.sh

chmod +x run_trading.sh
```

**Windows:**
Создайте файл `run_trading.bat`:
```batch
@echo off
cd C:\path\to\trading_program
call venv\Scripts\activate
python main.py
pause
```

## Обновление зависимостей

```bash
pip install --upgrade -r requirements.txt
```

## Резервное копирование базы данных

```bash
# Создать бэкап
pg_dump -U postgres trading_db > trading_db_backup.sql

# Восстановить из бэкапа
psql -U postgres -d trading_db < trading_db_backup.sql
```

## Удаление

### Удаление виртуального окружения
```bash
rm -rf venv
```

### Удаление базы данных
```bash
sudo -u postgres psql -c "DROP DATABASE trading_db;"
sudo -u postgres psql -c "DROP USER trading_user;"
```

## Получение помощи

Если возникли проблемы:
1. Проверьте логи PostgreSQL: `/var/log/postgresql/`
2. Проверьте таблицу event_log в БД
3. Запустите программу с флагом verbose (если добавлен)

## Готово! 🎉

Теперь программа готова к использованию. Удачной торговли!
