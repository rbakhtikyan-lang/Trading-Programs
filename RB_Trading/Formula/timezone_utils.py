"""
Утилиты для работы с часовыми поясами в торговой программе
"""

from datetime import datetime, timezone
import pytz
from colorama import Fore, Style, init

init(autoreset=True)


def check_timezone_info():
    """Показать информацию о часовых поясах"""
    
    print(f"\n{Fore.CYAN}{'='*70}")
    print(f"{Fore.CYAN}ИНФОРМАЦИЯ О ЧАСОВЫХ ПОЯСАХ")
    print(f"{Fore.CYAN}{'='*70}{Style.RESET_ALL}\n")
    
    # Текущее время
    now_utc = datetime.now(timezone.utc)
    now_local = datetime.now()
    
    print(f"{Fore.YELLOW}Текущее время:{Style.RESET_ALL}")
    print(f"  UTC (биржи):     {Fore.GREEN}{now_utc.strftime('%Y-%m-%d %H:%M:%S UTC')}{Style.RESET_ALL}")
    print(f"  Локальное время: {Fore.CYAN}{now_local.strftime('%Y-%m-%d %H:%M:%S')}{Style.RESET_ALL}")
    
    # Разница
    offset = (now_local - now_utc.replace(tzinfo=None)).total_seconds() / 3600
    print(f"  Разница:         {Fore.MAGENTA}{offset:+.1f} часов{Style.RESET_ALL}")
    
    # Популярные часовые пояса
    print(f"\n{Fore.YELLOW}Популярные торговые зоны:{Style.RESET_ALL}")
    
    zones = {
        'UTC': 'UTC',
        'New York': 'America/New_York',
        'London': 'Europe/London',
        'Tokyo': 'Asia/Tokyo',
        'Hong Kong': 'Asia/Hong_Kong',
        'Sydney': 'Australia/Sydney'
    }
    
    for city, tz_name in zones.items():
        try:
            tz = pytz.timezone(tz_name)
            time_in_tz = now_utc.astimezone(tz)
            print(f"  {city:12} {time_in_tz.strftime('%H:%M:%S %Z')}")
        except:
            pass
    
    print(f"\n{Fore.YELLOW}{'─'*70}{Style.RESET_ALL}\n")


def convert_timestamp_to_datetime(timestamp_ms, use_utc=True):
    """
    Конвертация timestamp в datetime
    
    Args:
        timestamp_ms: Timestamp в миллисекундах
        use_utc: Использовать UTC (True) или локальное время (False)
    
    Returns:
        datetime объект
    """
    if use_utc:
        return datetime.utcfromtimestamp(timestamp_ms / 1000)
    else:
        return datetime.fromtimestamp(timestamp_ms / 1000)


def check_database_times(conn, symbol='BTC/USDT', limit=5):
    """
    Проверить времена в базе данных
    """
    print(f"\n{Fore.CYAN}{'='*70}")
    print(f"{Fore.CYAN}ПРОВЕРКА ВРЕМЕНИ В БАЗЕ ДАННЫХ")
    print(f"{Fore.CYAN}{'='*70}{Style.RESET_ALL}\n")
    
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT timestamp, datetime, high, low
        FROM candles
        WHERE symbol = %s
        ORDER BY timestamp DESC
        LIMIT %s
    """, (symbol, limit))
    
    rows = cursor.fetchall()
    
    if not rows:
        print(f"{Fore.YELLOW}⚠ Нет данных для {symbol}{Style.RESET_ALL}")
        return
    
    print(f"{Fore.YELLOW}Последние {limit} записей для {symbol}:{Style.RESET_ALL}\n")
    print(f"{'Timestamp':<15} {'В БД (datetime)':<25} {'UTC (правильно)':<25} {'Совпадает?'}")
    print(f"{Fore.YELLOW}{'─'*95}{Style.RESET_ALL}")
    
    for row in rows:
        timestamp_ms, db_datetime, high, low = row
        
        # Правильное UTC время
        correct_utc = datetime.utcfromtimestamp(timestamp_ms / 1000)
        
        # Сравнение
        match = (db_datetime == correct_utc)
        
        status = f"{Fore.GREEN}✓" if match else f"{Fore.RED}✗"
        
        print(f"{timestamp_ms:<15} {str(db_datetime):<25} {str(correct_utc):<25} {status}{Style.RESET_ALL}")
    
    cursor.close()
    
    print(f"\n{Fore.YELLOW}Примечание:{Style.RESET_ALL}")
    print(f"  - Если есть ✗ (красный крестик), значит время сохранено неправильно")
    print(f"  - Binance и другие биржи всегда работают в UTC")
    print(f"  - Программа теперь сохраняет в UTC (после обновления)\n")


def fix_database_times(conn, symbol=None):
    """
    Исправить времена в базе данных (конвертировать в UTC)
    
    Args:
        conn: Подключение к PostgreSQL
        symbol: Символ для исправления (None = все)
    """
    print(f"\n{Fore.YELLOW}⚠ ВНИМАНИЕ: Эта операция изменит все записи в БД!{Style.RESET_ALL}")
    confirm = input(f"{Fore.WHITE}Продолжить? (yes/no): {Style.RESET_ALL}")
    
    if confirm.lower() != 'yes':
        print(f"{Fore.CYAN}Операция отменена{Style.RESET_ALL}")
        return
    
    cursor = conn.cursor()
    
    try:
        # Получаем все записи
        if symbol:
            cursor.execute("SELECT id, timestamp, datetime FROM candles WHERE symbol = %s", (symbol,))
        else:
            cursor.execute("SELECT id, timestamp, datetime FROM candles")
        
        rows = cursor.fetchall()
        
        print(f"\n{Fore.YELLOW}Обновление {len(rows)} записей...{Style.RESET_ALL}")
        
        updated = 0
        for row_id, timestamp_ms, old_datetime in rows:
            # Правильное UTC время
            correct_utc = datetime.utcfromtimestamp(timestamp_ms / 1000)
            
            # Обновляем только если отличается
            if old_datetime != correct_utc:
                cursor.execute("""
                    UPDATE candles 
                    SET datetime = %s 
                    WHERE id = %s
                """, (correct_utc, row_id))
                updated += 1
        
        conn.commit()
        
        print(f"{Fore.GREEN}✓ Обновлено {updated} записей{Style.RESET_ALL}")
        print(f"{Fore.GREEN}✓ Все времена теперь в UTC{Style.RESET_ALL}\n")
        
    except Exception as e:
        conn.rollback()
        print(f"{Fore.RED}✗ Ошибка: {e}{Style.RESET_ALL}")
    
    cursor.close()


def show_candle_times(candles, limit=5):
    """
    Показать времена свечей из CCXT
    
    Args:
        candles: Список свечей от биржи
        limit: Сколько показать
    """
    print(f"\n{Fore.CYAN}{'='*70}")
    print(f"{Fore.CYAN}ВРЕМЕНА СВЕЧЕЙ ОТ БИРЖИ")
    print(f"{Fore.CYAN}{'='*70}{Style.RESET_ALL}\n")
    
    print(f"{'Timestamp (ms)':<15} {'UTC время':<25} {'Open':<12} {'High':<12}")
    print(f"{Fore.YELLOW}{'─'*70}{Style.RESET_ALL}")
    
    for candle in candles[:limit]:
        timestamp_ms = candle[0]
        open_price = candle[1]
        high = candle[2]
        
        utc_time = datetime.utcfromtimestamp(timestamp_ms / 1000)
        
        print(f"{timestamp_ms:<15} {str(utc_time):<25} {open_price:<12.2f} {high:<12.2f}")
    
    print(f"\n{Fore.YELLOW}Примечание: Все времена в UTC (биржевое время){Style.RESET_ALL}\n")


# Пример использования
if __name__ == "__main__":
    import psycopg2
    
    # Показать информацию о часовых поясах
    check_timezone_info()
    
    # Подключиться к БД и проверить
    try:
        conn = psycopg2.connect(
            dbname="trading_db",
            user="postgres",
            host="/var/run/postgresql",
            port="5432"
        )
        
        # Проверить времена в БД
        check_database_times(conn, 'BTC/USDT', 10)
        
        # Если нужно исправить - раскомментируй:
        fix_database_times(conn, 'BTC/USDT')
        
        conn.close()
        
    except Exception as e:
        print(f"{Fore.RED}✗ Ошибка подключения к БД: {e}{Style.RESET_ALL}")
