# 🤖 AUTOMATION - Модули автоматизации

Эта папка содержит модули для автоматической торговли.

---

## 📁 Структура проекта:

```
RB_Trading/Formula/
├── main.py                  ← Основная программа
├── cex_api.py              ← CEX подключение
├── rb_formula.py           ← RB Formula
├── roger_formula.py        ← Roger's Formula
├── timezone_utils.py       
├── db_stats.py             
│
└── automation/             ← ТЫ ЗДЕСЬ
    ├── trade_journal.py       - Журнал сделок
    ├── auto_monitor.py        - Автомониторинг
    ├── telegram_notifier.py   - Telegram уведомления
    ├── trading_system.py      - Главная система
    ├── AUTOMATION_GUIDE.md    - Инструкции
    └── README.md              - Этот файл
```

---

## 🚀 БЫСТРЫЙ СТАРТ:

### Запуск из этой папки:

```bash
# Перейди в automation
cd /home/roger/Desktop/RB_Trading/Formula/automation/

# Запусти автомониторинг
python auto_monitor.py

# ИЛИ запусти главную систему
python trading_system.py
```

---

## ✅ Модули автоматически найдут родительские файлы!

Импорты настроены так:
```python
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
```

Это значит файлы из `automation/` видят:
- `cex_api.py`
- `roger_formula.py`
- и другие из родительской папки

---

## 📖 Полная документация:

Читай **AUTOMATION_GUIDE.md** для:
- Подробных инструкций
- Настройки Telegram
- Стратегий торговли
- Советов и ожиданий

---

## 🎯 Что где запускать:

### Из `/Formula/`:
```bash
python main.py              # Главное меню программы
python db_stats.py          # Статистика БД
python timezone_utils.py    # Проверка времени
```

### Из `/Formula/automation/`:
```bash
python auto_monitor.py      # Автомониторинг сигналов
python trading_system.py    # Полная торговая система
python telegram_notifier.py # Настройка Telegram
python trade_journal.py     # Показать дневной отчёт
```

---

## 🔧 Если что-то не работает:

### Ошибка импорта:
```
ModuleNotFoundError: No module named 'cex_api'
```

**Решение:** Запускай из папки `automation/`:
```bash
cd /home/roger/Desktop/RB_Trading/Formula/automation/
python auto_monitor.py
```

### PostgreSQL не запущен:
```bash
sudo systemctl start postgresql
sudo pg_ctlcluster 18 main start
```

---

## ✨ Готово к работе!

Читай **AUTOMATION_GUIDE.md** и начинай! 🚀
