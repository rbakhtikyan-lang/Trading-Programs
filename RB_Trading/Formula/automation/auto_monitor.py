"""
Auto Monitor - Автоматический мониторинг торговых сигналов
Сканирует несколько монет каждые 5 минут и показывает сигналы
"""

import sys
import os

# Добавляем родительскую папку в путь для импорта
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import time
import psycopg2
from datetime import datetime
from colorama import Fore, Style, init
from cex_api import CEXConnector
from roger_formula import RogerFormula

init(autoreset=True)


class AutoMonitor:
    """Автоматический мониторинг торговых сигналов"""
    
    def __init__(self, symbols, timeframe='5m', check_interval=300):
        """
        Args:
            symbols: Список монет для мониторинга
            timeframe: Таймфрейм для анализа
            check_interval: Интервал проверки в секундах (300 = 5 минут)
        """
        self.symbols = symbols
        self.timeframe = timeframe
        self.check_interval = check_interval
        
        print(f"{Fore.YELLOW}Подключение к бирже...{Style.RESET_ALL}")
        self.cex = CEXConnector()
        
        # Проверяем что биржа инициализировалась
        if not self.cex.exchange:
            print(f"{Fore.RED}✗ ОШИБКА: Биржа не инициализирована!{Style.RESET_ALL}")
            print(f"{Fore.YELLOW}Проверь подключение к интернету{Style.RESET_ALL}")
            raise Exception("CEX не подключен")
        
        print(f"{Fore.GREEN}✓ Подключено к {self.cex.exchange_name}{Style.RESET_ALL}")
        
        print(f"{Fore.YELLOW}Подключение к БД...{Style.RESET_ALL}")
        self.conn = psycopg2.connect(
            dbname="trading_db",
            user="postgres",
            host="/var/run/postgresql",
            port="5432"
        )
        
        self.roger = RogerFormula()
        
        print(f"{Fore.CYAN}{'='*80}")
        print(f"{Fore.CYAN}AUTO MONITOR - Автоматический мониторинг сигналов")
        print(f"{Fore.CYAN}{'='*80}{Style.RESET_ALL}\n")
        print(f"{Fore.WHITE}Монеты:{Style.RESET_ALL} {Fore.CYAN}{', '.join(symbols)}{Style.RESET_ALL}")
        print(f"{Fore.WHITE}Таймфрейм:{Style.RESET_ALL} {Fore.CYAN}{timeframe}{Style.RESET_ALL}")
        print(f"{Fore.WHITE}Интервал:{Style.RESET_ALL} {Fore.CYAN}{check_interval // 60} минут{Style.RESET_ALL}\n")
    
    def scan_symbol(self, symbol):
        """Сканировать одну монету на сигналы"""
        try:
            # Проверяем что биржа работает
            if not self.cex.exchange:
                print(f"{Fore.RED}✗ Биржа не подключена{Style.RESET_ALL}")
                return None
            
            # Загружаем свежие данные
            print(f"{Fore.CYAN}Загружаю данные {symbol}...{Style.RESET_ALL}", end=' ')
            candles = self.cex.fetch_ohlcv(symbol, self.timeframe, 100)
            
            if not candles:
                print(f"{Fore.YELLOW}⚠ Нет данных{Style.RESET_ALL}")
                return None
            
            print(f"{Fore.GREEN}✓ {len(candles)} свечей{Style.RESET_ALL}")
            
            # Сохраняем в БД
            self.save_candles(symbol, candles)
            
            # Анализируем по Roger's Formula
            results = self.roger.calculate(self.conn, symbol, self.timeframe, 100)
            
            if not results:
                print(f"{Fore.YELLOW}⚠ Нет результатов анализа{Style.RESET_ALL}")
                return None
            
            # Проверяем сигналы
            signals = results.get('signals')
            
            if not signals:
                print(f"{Fore.YELLOW}⚠ Нет сигналов в результатах{Style.RESET_ALL}")
                return None
            
            # Фильтруем только LONG и SHORT сигналы (не нейтральные)
            active_signals = [s for s in signals if s.get('type') in ['LONG', 'SHORT', 'LONG (Скальпинг)', 'SHORT (Скальпинг)']]
            
            if active_signals:
                return {
                    'symbol': symbol,
                    'signals': active_signals,
                    'current_candle': results['current_candle'],
                    'rb_formula': results['rb_formula']
                }
            
            return None
            
        except Exception as e:
            print(f"{Fore.RED}✗ Ошибка сканирования {symbol}: {e}{Style.RESET_ALL}")
            import traceback
            traceback.print_exc()
            return None
    
    def save_candles(self, symbol, candles):
        """Быстрое сохранение свечей"""
        cursor = self.conn.cursor()
        
        for candle in candles[-10:]:  # Сохраняем только последние 10
            timestamp, open_p, high, low, close_p, volume = candle
            dt = datetime.utcfromtimestamp(timestamp / 1000)
            
            cursor.execute("""
                INSERT INTO candles (symbol, timeframe, timestamp, datetime, high, low, open, close, volume)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (symbol, timeframe, timestamp) DO NOTHING
            """, (symbol, self.timeframe, timestamp, dt, high, low, open_p, close_p, volume))
        
        self.conn.commit()
        cursor.close()
    
    def show_signal(self, result):
        """Красиво показать сигнал"""
        symbol = result['symbol']
        candle = result['current_candle']
        signals = result['signals']
        
        for signal in signals:
            signal_type = signal['type']
            
            # Цвет в зависимости от типа
            if 'LONG' in signal_type:
                color = Fore.GREEN
                emoji = '🟢'
            else:
                color = Fore.RED
                emoji = '🔴'
            
            print(f"\n{color}{'─'*80}")
            print(f"{emoji} {signal_type} СИГНАЛ - {symbol}")
            print(f"{color}{'─'*80}{Style.RESET_ALL}")
            
            print(f"{Fore.WHITE}Время:{Style.RESET_ALL}       {Fore.MAGENTA}{candle['datetime']}{Style.RESET_ALL}")
            print(f"{Fore.WHITE}Цена:{Style.RESET_ALL}        {Fore.CYAN}{candle['close']:.8f}{Style.RESET_ALL}")
            
            # Стратегия
            if 'strategy' in signal:
                print(f"{Fore.WHITE}Стратегия:{Style.RESET_ALL}   {Fore.YELLOW}{signal['strategy']}{Style.RESET_ALL}")
            
            # Параметры входа
            if 'entry' in signal:
                print(f"\n{Fore.YELLOW}Вход:{Style.RESET_ALL}")
                print(f"  {signal['entry']}")
            
            # Цели
            if 'target_1' in signal:
                print(f"\n{Fore.GREEN}Цели:{Style.RESET_ALL}")
                print(f"  1️⃣  {signal.get('target_1', 'N/A')}")
                print(f"  2️⃣  {signal.get('target_2', 'N/A')}")
                print(f"  3️⃣  {signal.get('target_3', 'N/A')}")
            elif 'target' in signal:
                print(f"\n{Fore.GREEN}Цель:{Style.RESET_ALL}")
                print(f"  {signal['target']}")
            
            # Стоп-лосс
            if 'stop_loss' in signal:
                print(f"\n{Fore.RED}Стоп-лосс:{Style.RESET_ALL}")
                print(f"  {signal['stop_loss']}")
            
            # Профит
            if 'expected_profit' in signal:
                print(f"\n{Fore.CYAN}Ожидаемый профит:{Style.RESET_ALL} {Fore.GREEN}{signal['expected_profit']}{Style.RESET_ALL}")
            
            # Risk/Reward
            if 'risk_reward' in signal:
                print(f"{Fore.CYAN}Risk/Reward:{Style.RESET_ALL} {Fore.MAGENTA}{signal['risk_reward']}{Style.RESET_ALL}")
            
            print(f"{color}{'─'*80}{Style.RESET_ALL}")
    
    def run(self):
        """Запустить мониторинг"""
        print(f"{Fore.GREEN}✓ Мониторинг запущен! Нажмите Ctrl+C для остановки{Style.RESET_ALL}\n")
        
        scan_count = 0
        
        try:
            while True:
                scan_count += 1
                now = datetime.now().strftime("%H:%M:%S")
                
                print(f"{Fore.CYAN}{'='*80}")
                print(f"{Fore.CYAN}Сканирование #{scan_count} - {now}")
                print(f"{Fore.CYAN}{'='*80}{Style.RESET_ALL}")
                
                signals_found = 0
                
                for symbol in self.symbols:
                    print(f"{Fore.YELLOW}⏳ Сканирую {symbol}...{Style.RESET_ALL}", end=' ')
                    
                    result = self.scan_symbol(symbol)
                    
                    if result:
                        print(f"{Fore.GREEN}✓ Сигнал найден!{Style.RESET_ALL}")
                        self.show_signal(result)
                        signals_found += 1
                    else:
                        print(f"{Fore.WHITE}○ Нет сигналов{Style.RESET_ALL}")
                
                if signals_found == 0:
                    print(f"\n{Fore.YELLOW}○ Сигналов не обнаружено{Style.RESET_ALL}")
                
                # Ждём следующего сканирования
                next_scan = datetime.now()
                next_scan = next_scan.replace(second=0, microsecond=0)
                
                # Округляем до следующих 5 минут
                minutes = (next_scan.minute // 5 + 1) * 5
                if minutes >= 60:
                    next_scan = next_scan.replace(hour=next_scan.hour + 1, minute=0)
                else:
                    next_scan = next_scan.replace(minute=minutes)
                
                next_scan_str = next_scan.strftime("%H:%M:%S")
                
                print(f"\n{Fore.CYAN}Следующее сканирование в {next_scan_str}...{Style.RESET_ALL}")
                print(f"{Fore.CYAN}{'='*80}{Style.RESET_ALL}\n")
                
                time.sleep(self.check_interval)
                
        except KeyboardInterrupt:
            print(f"\n\n{Fore.YELLOW}Мониторинг остановлен пользователем{Style.RESET_ALL}")
            self.cleanup()
    
    def cleanup(self):
        """Очистка ресурсов"""
        if self.conn:
            self.conn.close()
        print(f"{Fore.GREEN}✓ Ресурсы освобождены{Style.RESET_ALL}")


# Запуск
if __name__ == "__main__":
    # Список монет для мониторинга
    symbols = [
        'BTC/USDT',
        'ETH/USDT',
        'SOL/USDT',
        'BNB/USDT',
        'AVAX/USDT'
    ]
    
    # Создаём монитор
    monitor = AutoMonitor(
        symbols=symbols,
        timeframe='5m',      # Таймфрейм
        check_interval=300   # 5 минут
    )
    
    # Запускаем
    monitor.run()
