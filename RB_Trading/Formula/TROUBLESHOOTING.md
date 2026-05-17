# 🔧 Решение проблем

## Проблема 1: "permission denied for sequence candles_id_seq"

**Ошибка:**
```
✗ Ошибка сохранения: permission denied for sequence candles_id_seq
```

**Причина:** У пользователя PostgreSQL нет прав на использование sequence (автоинкремент ID).

### Решение:

**Вариант 1 (Быстрое исправление):**

```bash
# Выполните скрипт исправления прав
sudo -u postgres psql -d trading_db -f fix_permissions.sql
```

**Вариант 2 (Ручное исправление):**

```bash
# Зайдите в PostgreSQL
sudo -u postgres psql

# Подключитесь к базе данных
\c trading_db

# Дайте права на все таблицы и sequences
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO postgres;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO postgres;

# Если используете другого пользователя (не postgres), замените на своего:
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO your_username;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO your_username;

# Выйдите
\q
```

**Вариант 3 (Пересоздать базу данных):**

```bash
# Удалить старую базу
sudo -u postgres psql -c "DROP DATABASE IF EXISTS trading_db;"

# Создать новую
sudo -u postgres psql -c "CREATE DATABASE trading_db;"

# Импортировать схему заново
sudo -u postgres psql -d trading_db -f base.sql

# Дать права
sudo -u postgres psql -d trading_db -f fix_permissions.sql
```

---

## Проблема 2: Подключение к PostgreSQL

**Ошибка:**
```
connection to server on socket "/var/run/postgresql/.s.PGSQL.5432" failed
```

**Решение:**

```bash
# Проверьте, запущен ли PostgreSQL
sudo systemctl status postgresql

# Если не запущен, запустите
sudo systemctl start postgresql

# Включите автозапуск
sudo systemctl enable postgresql

# На macOS:
brew services start postgresql@16
```

---

## Проблема 3: Неверный пароль PostgreSQL

**Ошибка:**
```
FATAL: password authentication failed
```

**Решение:**

1. **Найдите правильный метод аутентификации:**

```bash
# Откройте файл pg_hba.conf
sudo nano /etc/postgresql/16/main/pg_hba.conf

# Найдите строки для local connections и измените на:
local   all             postgres                                peer
local   all             all                                     peer
```

2. **Или установите пароль для пользователя postgres:**

```bash
sudo -u postgres psql
ALTER USER postgres PASSWORD 'your_new_password';
\q
```

3. **Обновите пароль в main.py:**

```python
self.conn = psycopg2.connect(
    dbname="trading_db",
    user="postgres",
    password="your_new_password",  # <- здесь
    host="localhost",
    port="5432"
)
```

---

## Проблема 4: API Key Issues

**Симптом:** Вы видели что ввели API Key, но не ввели API Secret.

**Важно:** Для ПУБЛИЧНЫХ данных (история свечей) API ключи **НЕ НУЖНЫ**!

**Решение:**

При подключении к CEX просто нажимайте Enter два раза:
```
Введите API Key (или нажмите Enter для demo): [просто Enter]
Введите API Secret (или нажмите Enter для demo): [просто Enter]
```

Если вы всё-таки хотите использовать API ключи:
1. Получите их на Binance: Account → API Management
2. Вводите **ОБА** ключа - и API Key, и API Secret
3. **Никогда не публикуйте** свои ключи!

---

## Проблема 5: Модуль не найден

**Ошибка:**
```
ModuleNotFoundError: No module named 'ccxt'
```

**Решение:**

```bash
# Установите зависимости
pip install -r requirements.txt

# Или по отдельности
pip install ccxt psycopg2-binary colorama

# На некоторых системах нужен pip3
pip3 install -r requirements.txt
```

---

## Проблема 6: Символ не найден

**Ошибка:**
```
Symbol not found
```

**Решение:**

Используйте правильный формат символа:
- ✅ `BTC/USDT` (слэш обязателен)
- ✅ `ETH/USDT`
- ✅ `SOL/USDT`
- ❌ `BTCUSDT` (без слэша)
- ❌ `btc/usdt` (маленькие буквы)

---

## Проблема 7: Таблица не существует

**Ошибка:**
```
relation 'candles' does not exist
```

**Решение:**

Схема базы данных не импортирована:

```bash
# Импортируйте схему
sudo -u postgres psql -d trading_db -f base.sql

# Проверьте, что таблицы созданы
sudo -u postgres psql -d trading_db -c "\dt"
```

---

## Проверка работоспособности

### Тест 1: Проверка PostgreSQL

```bash
# Проверка версии
psql --version

# Проверка подключения
sudo -u postgres psql -c "SELECT version();"

# Проверка базы данных
sudo -u postgres psql -l | grep trading_db
```

### Тест 2: Проверка Python

```bash
# Проверка версии Python
python --version  # Должно быть 3.8+

# Проверка модулей
python -c "import ccxt, psycopg2, colorama; print('OK')"
```

### Тест 3: Проверка таблиц

```bash
sudo -u postgres psql -d trading_db -c "SELECT COUNT(*) FROM candles;"
```

### Тест 4: Проверка прав

```bash
sudo -u postgres psql -d trading_db -c "\dp candles"
sudo -u postgres psql -d trading_db -c "\dp candles_id_seq"
```

---

## Полная переустановка

Если ничего не помогает:

```bash
# 1. Удалить всё
sudo -u postgres psql -c "DROP DATABASE IF EXISTS trading_db;"
rm -rf /path/to/trading_program

# 2. Скачать заново
# (скачайте файлы программы)

# 3. Установить зависимости
pip install -r requirements.txt

# 4. Создать базу данных
sudo -u postgres psql -c "CREATE DATABASE trading_db;"
sudo -u postgres psql -d trading_db -f base.sql
sudo -u postgres psql -d trading_db -f fix_permissions.sql

# 5. Запустить программу
python main.py
```

---

## Логи для диагностики

### Лог PostgreSQL

```bash
# Ubuntu/Debian
sudo tail -f /var/log/postgresql/postgresql-16-main.log

# macOS
tail -f /usr/local/var/log/postgresql@16.log
```

### Включить debug в программе

В main.py добавьте в начале:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

---

## Нужна помощь?

Если проблема не решена:

1. Скопируйте **полный текст ошибки**
2. Скопируйте **версии**:
   ```bash
   python --version
   psql --version
   pip list | grep -E "ccxt|psycopg2|colorama"
   ```
3. Опишите что делали перед ошибкой

---

## Быстрая диагностика

Запустите этот скрипт для диагностики:

```bash
#!/bin/bash
echo "=== Диагностика ==="
echo "Python: $(python --version)"
echo "PostgreSQL: $(psql --version)"
echo "База данных:"
sudo -u postgres psql -l | grep trading_db
echo "Модули Python:"
python -c "import ccxt; print('ccxt: OK')" 2>&1
python -c "import psycopg2; print('psycopg2: OK')" 2>&1
python -c "import colorama; print('colorama: OK')" 2>&1
echo "Таблицы:"
sudo -u postgres psql -d trading_db -c "\dt" 2>&1
echo "=== Конец диагностики ==="
```

Сохраните как `diagnose.sh`, выполните `chmod +x diagnose.sh && ./diagnose.sh`
