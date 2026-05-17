"""
Monitor Core - Ядро мониторинга торговых сигналов
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import time
import psycopg2
from datetime import datetime
from colorama import Fore, Style
from cex_api import CEXConnector
from unified_formula import RogerFormula


class MonitorCore:
    """Ядро автоматического мониторинга"""
    
    def __init__(self, symbols, timeframe='5m'):
        self.symbols = symbols
        self.timeframe = timeframe
        
        print(f"{Fore.YELLOW}Подключение к бирже...{Style.RESET_ALL}")
        self.cex = CEXConnector()
        
        if not self.cex.exchange:
            raise Exception("CEX не подключен")
        
        print(f"{Fore.GREEN}✓ Подключено к {self.cex.exchange_name}{Style.RESET_ALL}")
        
        print(f"{Fore.YELLOW}Подключение к БД...{Style.RESET_ALL}")
        self.conn = psycopg2.connect(
            dbname="trading_db",
            user="postgres",
            host="/var/run/postgresql",
            port="5432"
        )
        print(f"{Fore.GREEN}✓ Подключено к БД{Style.RESET_ALL}")
        
        self.roger = RogerFormula()
    
    def save_candles(self, symbol, candles):
        """Сохранение свечей в БД"""
        try:
            cursor = self.conn.cursor()
            for candle in candles[-10:]:
                timestamp, open_p, high, low, close_p, volume = candle
                dt = datetime.utcfromtimestamp(timestamp / 1000)
                cursor.execute("""
                    INSERT INTO candles (symbol, timeframe, timestamp, datetime, high, low, open, close, volume)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (symbol, timeframe, timestamp) DO NOTHING
                """, (symbol, self.timeframe, timestamp, dt, high, low, open_p, close_p, volume))
            self.conn.commit()
            cursor.close()
        except Exception as e:
            print(f"{Fore.RED}✗ Ошибка сохранения свечей: {e}{Style.RESET_ALL}")
            self.conn.rollback()
    
    def scan_symbol(self, symbol):
        """Сканировать одну монету — возвращает результат или None"""
        try:
            if not self.cex.exchange:
                print(f"{Fore.RED}✗ Биржа не подключена{Style.RESET_ALL}")
                return None
            
            # Загружаем свечи
            print(f"{Fore.CYAN}Загружаю данные {symbol}...{Style.RESET_ALL}", end=' ')
            candles = self.cex.fetch_ohlcv(symbol, self.timeframe, 100)
            
            if not candles or len(candles) == 0:
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
                return None
            
            # Фильтруем только активные сигналы
            active_signals = []
            for s in signals:
                if isinstance(s, dict):
                    signal_type = s.get('type', '')
                    if signal_type in ['LONG', 'SHORT', 'LONG (Скальпинг)', 'SHORT (Скальпинг)']:
                        active_signals.append(s)
            
            if active_signals:
                return {
                    'symbol': symbol,
                    'signals': active_signals,
                    'current_candle': results.get('current_candle', {}),
                    'rb_formula': results.get('rb_formula', {})
                }
            
            return None
        
        except Exception as e:
            print(f"{Fore.RED}✗ Неожиданная ошибка при сканировании {symbol}: {e}{Style.RESET_ALL}")
            import traceback
            traceback.print_exc()
            return None
    
    def close(self):
        """Закрытие соединений"""
        if self.conn:
            self.conn.close()
            print(f"{Fore.GREEN}✓ Соединение с БД закрыто{Style.RESET_ALL}")
