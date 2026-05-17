"""
Утилита для проверки размера и статистики базы данных
"""

import psycopg2
from colorama import Fore, Style, init

init(autoreset=True)


def get_database_size(conn):
    """Получить размер базы данных"""
    cursor = conn.cursor()
    
    print(f"\n{Fore.CYAN}{'='*80}")
    print(f"{Fore.CYAN}РАЗМЕР БАЗЫ ДАННЫХ")
    print(f"{Fore.CYAN}{'='*80}{Style.RESET_ALL}\n")
    
    # Размер всей базы данных
    cursor.execute("""
        SELECT pg_size_pretty(pg_database_size('trading_db')) as size;
    """)
    db_size = cursor.fetchone()[0]
    
    print(f"{Fore.WHITE}Общий размер базы данных:{Style.RESET_ALL} {Fore.GREEN}{db_size}{Style.RESET_ALL}")
    
    # Размер каждой таблицы
    cursor.execute("""
        SELECT 
            tablename,
            pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size,
            pg_total_relation_size(schemaname||'.'||tablename) AS size_bytes
        FROM pg_tables
        WHERE schemaname = 'public'
        ORDER BY size_bytes DESC;
    """)
    
    tables = cursor.fetchall()
    
    print(f"\n{Fore.YELLOW}{'─'*80}")
    print(f"{Fore.YELLOW}РАЗМЕР ТАБЛИЦ")
    print(f"{Fore.YELLOW}{'─'*80}{Style.RESET_ALL}")
    print(f"{'Таблица':<30} {'Размер':<15} {'Байт':<20}")
    print(f"{Fore.YELLOW}{'─'*80}{Style.RESET_ALL}")
    
    for table_name, size, size_bytes in tables:
        print(f"{Fore.WHITE}{table_name:<30}{Style.RESET_ALL} {Fore.CYAN}{size:<15}{Style.RESET_ALL} {Fore.MAGENTA}{size_bytes:<20}{Style.RESET_ALL}")
    
    cursor.close()
    print(f"{Fore.YELLOW}{'─'*80}{Style.RESET_ALL}\n")


def get_table_stats(conn):
    """Получить статистику по таблицам"""
    cursor = conn.cursor()
    
    print(f"{Fore.CYAN}{'='*80}")
    print(f"{Fore.CYAN}СТАТИСТИКА ТАБЛИЦ")
    print(f"{Fore.CYAN}{'='*80}{Style.RESET_ALL}\n")
    
    # Количество записей в каждой таблице
    tables = ['candles', 'analysis_results', 'support_resistance_levels', 'event_log']
    
    print(f"{'Таблица':<30} {'Количество записей':<20}")
    print(f"{Fore.YELLOW}{'─'*80}{Style.RESET_ALL}")
    
    for table in tables:
        try:
            cursor.execute(f"SELECT COUNT(*) FROM {table};")
            count = cursor.fetchone()[0]
            print(f"{Fore.WHITE}{table:<30}{Style.RESET_ALL} {Fore.GREEN}{count:<20}{Style.RESET_ALL}")
        except Exception as e:
            print(f"{Fore.WHITE}{table:<30}{Style.RESET_ALL} {Fore.RED}Ошибка: {e}{Style.RESET_ALL}")
    
    cursor.close()
    print(f"{Fore.YELLOW}{'─'*80}{Style.RESET_ALL}\n")


def get_candles_stats(conn):
    """Детальная статистика по свечам"""
    cursor = conn.cursor()
    
    print(f"{Fore.CYAN}{'='*80}")
    print(f"{Fore.CYAN}ДЕТАЛЬНАЯ СТАТИСТИКА СВЕЧЕЙ")
    print(f"{Fore.CYAN}{'='*80}{Style.RESET_ALL}\n")
    
    # Статистика по символам
    cursor.execute("""
        SELECT 
            symbol,
            timeframe,
            COUNT(*) as count,
            MIN(datetime) as first_date,
            MAX(datetime) as last_date,
            pg_size_pretty(
                pg_total_relation_size('candles') * COUNT(*) / 
                (SELECT COUNT(*) FROM candles)::bigint
            ) as approx_size
        FROM candles
        GROUP BY symbol, timeframe
        ORDER BY count DESC;
    """)
    
    rows = cursor.fetchall()
    
    if rows:
        print(f"{'Символ':<15} {'TF':<8} {'Свечей':<12} {'Первая дата':<20} {'Последняя дата':<20} {'~Размер':<12}")
        print(f"{Fore.YELLOW}{'─'*100}{Style.RESET_ALL}")
        
        total_candles = 0
        for symbol, tf, count, first_date, last_date, size in rows:
            total_candles += count
            print(f"{Fore.WHITE}{symbol:<15}{Style.RESET_ALL} "
                  f"{Fore.CYAN}{tf:<8}{Style.RESET_ALL} "
                  f"{Fore.GREEN}{count:<12}{Style.RESET_ALL} "
                  f"{Fore.MAGENTA}{str(first_date):<20}{Style.RESET_ALL} "
                  f"{Fore.MAGENTA}{str(last_date):<20}{Style.RESET_ALL} "
                  f"{Fore.YELLOW}{size:<12}{Style.RESET_ALL}")
        
        print(f"{Fore.YELLOW}{'─'*100}{Style.RESET_ALL}")
        print(f"{Fore.WHITE}ИТОГО:{Style.RESET_ALL} {Fore.GREEN}{total_candles} свечей{Style.RESET_ALL}\n")
    else:
        print(f"{Fore.YELLOW}⚠ Нет данных в таблице candles{Style.RESET_ALL}\n")
    
    cursor.close()


def get_index_stats(conn):
    """Статистика по индексам"""
    cursor = conn.cursor()
    
    print(f"{Fore.CYAN}{'='*80}")
    print(f"{Fore.CYAN}ИНДЕКСЫ")
    print(f"{Fore.CYAN}{'='*80}{Style.RESET_ALL}\n")
    
    cursor.execute("""
        SELECT 
            indexname,
            tablename,
            pg_size_pretty(pg_relation_size(indexname::regclass)) as size
        FROM pg_indexes
        WHERE schemaname = 'public'
        ORDER BY pg_relation_size(indexname::regclass) DESC;
    """)
    
    indexes = cursor.fetchall()
    
    print(f"{'Индекс':<40} {'Таблица':<25} {'Размер':<15}")
    print(f"{Fore.YELLOW}{'─'*80}{Style.RESET_ALL}")
    
    for index_name, table_name, size in indexes:
        print(f"{Fore.WHITE}{index_name:<40}{Style.RESET_ALL} "
              f"{Fore.CYAN}{table_name:<25}{Style.RESET_ALL} "
              f"{Fore.GREEN}{size:<15}{Style.RESET_ALL}")
    
    cursor.close()
    print(f"{Fore.YELLOW}{'─'*80}{Style.RESET_ALL}\n")


def estimate_storage_needs(conn):
    """Оценка потребностей в хранилище"""
    cursor = conn.cursor()
    
    print(f"{Fore.CYAN}{'='*80}")
    print(f"{Fore.CYAN}ОЦЕНКА ПОТРЕБНОСТЕЙ В ХРАНИЛИЩЕ")
    print(f"{Fore.CYAN}{'='*80}{Style.RESET_ALL}\n")
    
    # Получаем размер одной записи
    cursor.execute("SELECT COUNT(*) FROM candles;")
    total_candles = cursor.fetchone()[0]
    
    if total_candles > 0:
        cursor.execute("""
            SELECT pg_total_relation_size('candles');
        """)
        total_bytes = cursor.fetchone()[0]
        
        bytes_per_candle = total_bytes / total_candles
        
        print(f"{Fore.WHITE}Средний размер одной свечи:{Style.RESET_ALL} {Fore.CYAN}{bytes_per_candle:.2f} байт{Style.RESET_ALL}")
        print(f"{Fore.WHITE}Всего свечей:{Style.RESET_ALL} {Fore.GREEN}{total_candles:,}{Style.RESET_ALL}\n")
        
        # Прогнозы
        scenarios = [
            ("1 день (1m свечи)", 1440),
            ("1 неделя (1m свечи)", 1440 * 7),
            ("1 месяц (1m свечи)", 1440 * 30),
            ("1 год (1m свечи)", 1440 * 365),
            ("1 год (5m свечи)", 288 * 365),
            ("1 год (1h свечи)", 24 * 365),
        ]
        
        print(f"{Fore.YELLOW}Прогноз размера для одного символа:{Style.RESET_ALL}")
        print(f"{'Период':<30} {'Свечей':<15} {'Размер':<15}")
        print(f"{Fore.YELLOW}{'─'*80}{Style.RESET_ALL}")
        
        for scenario, candles_count in scenarios:
            size_bytes = candles_count * bytes_per_candle
            size_mb = size_bytes / (1024 * 1024)
            
            if size_mb < 1:
                size_str = f"{size_bytes / 1024:.2f} KB"
            elif size_mb < 1024:
                size_str = f"{size_mb:.2f} MB"
            else:
                size_str = f"{size_mb / 1024:.2f} GB"
            
            print(f"{Fore.WHITE}{scenario:<30}{Style.RESET_ALL} "
                  f"{Fore.CYAN}{candles_count:,}  {Style.RESET_ALL} "
                  f"{Fore.GREEN}{size_str:<15}{Style.RESET_ALL}")
        
        print(f"\n{Fore.YELLOW}💡 Рекомендации:{Style.RESET_ALL}")
        print(f"  - Для краткосрочной торговли (скальпинг) используй 1m-5m")
        print(f"  - Для свинг-трейдинга используй 1h-4h")
        print(f"  - Для долгосрочного анализа используй 1d")
        print(f"  - Регулярно очищай старые данные (старше 3-6 месяцев)\n")
    else:
        print(f"{Fore.YELLOW}⚠ Нет данных для оценки{Style.RESET_ALL}\n")
    
    cursor.close()


def cleanup_old_data(conn, days=30, dry_run=True):
    """
    Очистка старых данных
    
    Args:
        conn: Подключение к БД
        days: Удалить данные старше N дней
        dry_run: Только показать, сколько будет удалено (не удалять на самом деле)
    """
    cursor = conn.cursor()
    
    print(f"\n{Fore.CYAN}{'='*80}")
    print(f"{Fore.CYAN}ОЧИСТКА СТАРЫХ ДАННЫХ")
    print(f"{Fore.CYAN}{'='*80}{Style.RESET_ALL}\n")
    
    # Проверяем сколько будет удалено
    cursor.execute("""
        SELECT COUNT(*), MIN(datetime), MAX(datetime)
        FROM candles
        WHERE datetime < NOW() - INTERVAL '%s days';
    """, (days,))
    
    count, min_date, max_date = cursor.fetchone()
    
    if count > 0:
        print(f"{Fore.YELLOW}Найдено старых записей:{Style.RESET_ALL} {Fore.RED}{count}{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}Период:{Style.RESET_ALL} {Fore.MAGENTA}{min_date}{Style.RESET_ALL} → {Fore.MAGENTA}{max_date}{Style.RESET_ALL}\n")
        
        if dry_run:
            print(f"{Fore.CYAN}Режим просмотра (dry_run=True). Данные НЕ удалены.{Style.RESET_ALL}")
            print(f"{Fore.CYAN}Чтобы удалить, запусти с dry_run=False{Style.RESET_ALL}\n")
        else:
            confirm = input(f"{Fore.RED}⚠ УДАЛИТЬ {count} записей? (yes/no): {Style.RESET_ALL}")
            
            if confirm.lower() == 'yes':
                cursor.execute("""
                    DELETE FROM candles
                    WHERE datetime < NOW() - INTERVAL '%s days';
                """, (days,))
                conn.commit()
                print(f"{Fore.GREEN}✓ Удалено {count} записей{Style.RESET_ALL}\n")
            else:
                print(f"{Fore.CYAN}Операция отменена{Style.RESET_ALL}\n")
    else:
        print(f"{Fore.GREEN}✓ Нет старых данных для удаления{Style.RESET_ALL}\n")
    
    cursor.close()


def main():
    """Главная функция"""
    try:
        # Подключение к БД
        conn = psycopg2.connect(
            dbname="trading_db",
            user="postgres",
            host="/var/run/postgresql",
            port="5432"
        )
        
        # Получаем все статистики
        get_database_size(conn)
        get_table_stats(conn)
        get_candles_stats(conn)
        get_index_stats(conn)
        estimate_storage_needs(conn)
        
        # Проверка старых данных (только просмотр)
        cleanup_old_data(conn, days=30, dry_run=True)
        
        conn.close()
        
        print(f"{Fore.GREEN}{'='*80}")
        print(f"{Fore.GREEN}Анализ завершён!")
        print(f"{Fore.GREEN}{'='*80}{Style.RESET_ALL}\n")
        
    except Exception as e:
        print(f"{Fore.RED}✗ Ошибка: {e}{Style.RESET_ALL}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
