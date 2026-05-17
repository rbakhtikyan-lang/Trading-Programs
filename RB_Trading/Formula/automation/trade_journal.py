"""
Trade Journal - Журнал сделок с автоматической статистикой
"""

import psycopg2
from datetime import datetime, timedelta
from colorama import Fore, Style, init

init(autoreset=True)


class TradeJournal:
    """Журнал торговых сделок"""
    
    def __init__(self, conn):
        self.conn = conn
        self.create_tables()
    
    def create_tables(self):
        """Создать таблицы для журнала"""
        cursor = self.conn.cursor()
        
        # Таблица сделок
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS trades (
                id SERIAL PRIMARY KEY,
                datetime TIMESTAMP DEFAULT NOW(),
                symbol VARCHAR(20) NOT NULL,
                timeframe VARCHAR(10),
                direction VARCHAR(10) NOT NULL,  -- LONG или SHORT
                entry_price DECIMAL(20, 8) NOT NULL,
                exit_price DECIMAL(20, 8),
                target_price DECIMAL(20, 8),
                stop_price DECIMAL(20, 8),
                position_size DECIMAL(20, 8),
                leverage INTEGER DEFAULT 1,
                profit_usdt DECIMAL(20, 8),
                profit_percent DECIMAL(10, 4),
                status VARCHAR(20) DEFAULT 'OPEN',  -- OPEN, CLOSED, STOPPED
                notes TEXT,
                created_at TIMESTAMP DEFAULT NOW()
            );
        """)
        
        # Индекс для быстрого поиска
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_trades_datetime 
            ON trades(datetime DESC);
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_trades_symbol 
            ON trades(symbol, datetime DESC);
        """)
        
        self.conn.commit()
        cursor.close()
    
    def add_trade(self, symbol, direction, entry_price, target_price, stop_price, 
                  position_size, leverage=3, timeframe='5m', notes=''):
        """
        Добавить новую сделку
        
        Args:
            symbol: Торговая пара
            direction: LONG или SHORT
            entry_price: Цена входа
            target_price: Цель тейк-профита
            stop_price: Стоп-лосс
            position_size: Размер позиции в USDT
            leverage: Плечо
            timeframe: Таймфрейм
            notes: Заметки
        """
        cursor = self.conn.cursor()
        
        cursor.execute("""
            INSERT INTO trades (
                symbol, timeframe, direction, entry_price, 
                target_price, stop_price, position_size, leverage, notes
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """, (symbol, timeframe, direction, entry_price, 
              target_price, stop_price, position_size, leverage, notes))
        
        trade_id = cursor.fetchone()[0]
        self.conn.commit()
        cursor.close()
        
        print(f"{Fore.GREEN}✓ Сделка #{trade_id} добавлена в журнал{Style.RESET_ALL}")
        return trade_id
    
    def close_trade(self, trade_id, exit_price, notes=''):
        """
        Закрыть сделку
        
        Args:
            trade_id: ID сделки
            exit_price: Цена выхода
            notes: Дополнительные заметки
        """
        cursor = self.conn.cursor()
        
        # Получаем данные сделки
        cursor.execute("""
            SELECT direction, entry_price, position_size, leverage
            FROM trades WHERE id = %s
        """, (trade_id,))
        
        row = cursor.fetchone()
        if not row:
            print(f"{Fore.RED}✗ Сделка #{trade_id} не найдена{Style.RESET_ALL}")
            return
        
        direction, entry_price, position_size, leverage = row
        entry_price = float(entry_price)
        position_size = float(position_size)
        exit_price = float(exit_price)
        
        # Рассчитываем профит
        if direction == 'LONG':
            profit_percent = ((exit_price - entry_price) / entry_price) * 100
        else:  # SHORT
            profit_percent = ((entry_price - exit_price) / entry_price) * 100
        
        profit_usdt = (position_size * leverage) * (profit_percent / 100)
        
        # Определяем статус
        cursor.execute("SELECT stop_price FROM trades WHERE id = %s", (trade_id,))
        stop_price = float(cursor.fetchone()[0])
        
        if direction == 'LONG':
            status = 'STOPPED' if exit_price <= stop_price else 'CLOSED'
        else:
            status = 'STOPPED' if exit_price >= stop_price else 'CLOSED'
        
        # Обновляем сделку
        cursor.execute("""
            UPDATE trades 
            SET exit_price = %s,
                profit_usdt = %s,
                profit_percent = %s,
                status = %s,
                notes = COALESCE(notes, '') || %s
            WHERE id = %s
        """, (exit_price, profit_usdt, profit_percent, status, f"\n{notes}" if notes else "", trade_id))
        
        self.conn.commit()
        cursor.close()
        
        color = Fore.GREEN if profit_usdt > 0 else Fore.RED
        print(f"{color}✓ Сделка #{trade_id} закрыта: {profit_usdt:+.2f} USDT ({profit_percent:+.2f}%){Style.RESET_ALL}")
        
        return profit_usdt
    
    def get_open_trades(self):
        """Получить открытые сделки"""
        cursor = self.conn.cursor()
        
        cursor.execute("""
            SELECT id, datetime, symbol, direction, entry_price, 
                   target_price, stop_price, position_size, leverage
            FROM trades
            WHERE status = 'OPEN'
            ORDER BY datetime DESC
        """)
        
        trades = cursor.fetchall()
        cursor.close()
        
        return trades
    
    def get_daily_stats(self, date=None):
        """Получить статистику за день"""
        if date is None:
            date = datetime.now().date()
        
        cursor = self.conn.cursor()
        
        # Общая статистика
        cursor.execute("""
            SELECT 
                COUNT(*) as total_trades,
                COUNT(CASE WHEN status = 'CLOSED' AND profit_usdt > 0 THEN 1 END) as wins,
                COUNT(CASE WHEN status = 'CLOSED' AND profit_usdt <= 0 THEN 1 END) as losses,
                COUNT(CASE WHEN status = 'STOPPED' THEN 1 END) as stopped,
                COUNT(CASE WHEN status = 'OPEN' THEN 1 END) as open_trades,
                COALESCE(SUM(CASE WHEN status != 'OPEN' THEN profit_usdt ELSE 0 END), 0) as total_profit,
                COALESCE(AVG(CASE WHEN status = 'CLOSED' AND profit_usdt > 0 THEN profit_usdt END), 0) as avg_win,
                COALESCE(AVG(CASE WHEN status = 'CLOSED' AND profit_usdt <= 0 THEN profit_usdt END), 0) as avg_loss
            FROM trades
            WHERE DATE(datetime) = %s
        """, (date,))
        
        stats = cursor.fetchone()
        cursor.close()
        
        return {
            'total_trades': stats[0],
            'wins': stats[1],
            'losses': stats[2],
            'stopped': stats[3],
            'open_trades': stats[4],
            'total_profit': float(stats[5]),
            'avg_win': float(stats[6]),
            'avg_loss': float(stats[7])
        }
    
    def show_daily_report(self, date=None):
        """Показать дневной отчёт"""
        if date is None:
            date = datetime.now().date()
        
        stats = self.get_daily_stats(date)
        
        total = stats['total_trades']
        wins = stats['wins']
        losses = stats['losses']
        stopped = stats['stopped']
        
        win_rate = (wins / total * 100) if total > 0 else 0
        
        print(f"\n{Fore.CYAN}{'═'*70}")
        print(f"{Fore.CYAN}ДНЕВНОЙ ОТЧЁТ - {date}")
        print(f"{Fore.CYAN}{'═'*70}{Style.RESET_ALL}\n")
        
        print(f"{Fore.WHITE}Всего сделок:{Style.RESET_ALL}     {Fore.CYAN}{total}{Style.RESET_ALL}")
        print(f"{Fore.GREEN}Успешных:{Style.RESET_ALL}         {Fore.GREEN}{wins}{Style.RESET_ALL} ({win_rate:.1f}%)")
        print(f"{Fore.RED}Убыточных:{Style.RESET_ALL}        {Fore.RED}{losses}{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}По стопу:{Style.RESET_ALL}         {Fore.YELLOW}{stopped}{Style.RESET_ALL}")
        print(f"{Fore.MAGENTA}Открытых:{Style.RESET_ALL}         {Fore.MAGENTA}{stats['open_trades']}{Style.RESET_ALL}\n")
        
        color = Fore.GREEN if stats['total_profit'] > 0 else Fore.RED
        print(f"{Fore.WHITE}Общий профит:{Style.RESET_ALL}     {color}{stats['total_profit']:+.2f} USDT{Style.RESET_ALL}")
        print(f"{Fore.WHITE}Средний выигрыш:{Style.RESET_ALL}  {Fore.GREEN}{stats['avg_win']:+.2f} USDT{Style.RESET_ALL}")
        print(f"{Fore.WHITE}Средний убыток:{Style.RESET_ALL}   {Fore.RED}{stats['avg_loss']:+.2f} USDT{Style.RESET_ALL}\n")
        
        # Цель
        target = 100  # $100 в день
        progress = (stats['total_profit'] / target * 100) if target > 0 else 0
        
        print(f"{Fore.YELLOW}Цель:{Style.RESET_ALL}              {Fore.CYAN}${target}{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}Выполнение:{Style.RESET_ALL}        {Fore.MAGENTA}{progress:.1f}%{Style.RESET_ALL}")
        
        # Прогресс-бар
        bar_length = 40
        filled = int(bar_length * min(progress, 100) / 100)
        bar = '█' * filled + '░' * (bar_length - filled)
        print(f"{Fore.CYAN}[{bar}]{Style.RESET_ALL}\n")
        
        print(f"{Fore.CYAN}{'═'*70}{Style.RESET_ALL}\n")


# Пример использования
if __name__ == "__main__":
    try:
        conn = psycopg2.connect(
            dbname="trading_db",
            user="postgres",
            host="/var/run/postgresql",
            port="5432"
        )
        
        journal = TradeJournal(conn)
        
        # Пример: добавить сделку
        # trade_id = journal.add_trade(
        #     symbol='BTC/USDT',
        #     direction='LONG',
        #     entry_price=68950,
        #     target_price=69100,
        #     stop_price=68875,
        #     position_size=300,
        #     leverage=3,
        #     notes='Roger Formula signal'
        # )
        
        # Показать дневной отчёт
        journal.show_daily_report()
        
        conn.close()
        
    except Exception as e:
        print(f"{Fore.RED}✗ Ошибка: {e}{Style.RESET_ALL}")
