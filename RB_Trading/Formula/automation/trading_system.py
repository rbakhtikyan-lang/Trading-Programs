"""
Trading System - Полная система автоматизации торговли
Объединяет: Auto Monitor + Trade Journal + Telegram + Dashboard
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
from trade_journal import TradeJournal
from telegram_notifier import TelegramNotifier

init(autoreset=True)


class TradingSystem:
    """Полная торговая система с автоматизацией"""
    
    def __init__(self, config):
        """
        Args:
            config: Конфигурация системы (dict)
        """
        self.config = config
        
        # Подключение к бирже
        self.cex = CEXConnector()
        
        # Подключение к БД
        self.conn = psycopg2.connect(
            dbname="trading_db",
            user="postgres",
            host="/var/run/postgresql",
            port="5432"
        )
        
        # Модули
        self.roger = RogerFormula()
        self.journal = TradeJournal(self.conn)
        
        # Telegram (опционально)
        telegram_token = config.get('telegram_token')
        telegram_chat = config.get('telegram_chat')
        self.telegram = TelegramNotifier(telegram_token, telegram_chat)
        
        self.print_header()
    
    def print_header(self):
        """Показать заголовок системы"""
        print(f"\n{Fore.CYAN}{'='*80}")
        print(f"{Fore.CYAN}         ROGER'S AUTOMATED TRADING SYSTEM")
        print(f"{Fore.CYAN}{'='*80}{Style.RESET_ALL}\n")
        
        print(f"{Fore.WHITE}Монеты:{Style.RESET_ALL}      {Fore.CYAN}{', '.join(self.config['symbols'])}{Style.RESET_ALL}")
        print(f"{Fore.WHITE}Таймфрейм:{Style.RESET_ALL}   {Fore.CYAN}{self.config['timeframe']}{Style.RESET_ALL}")
        print(f"{Fore.WHITE}Капитал:{Style.RESET_ALL}     {Fore.GREEN}{self.config['capital']} USDT{Style.RESET_ALL}")
        print(f"{Fore.WHITE}Плечо:{Style.RESET_ALL}       {Fore.YELLOW}{self.config['leverage']}x{Style.RESET_ALL}")
        print(f"{Fore.WHITE}Цель/день:{Style.RESET_ALL}   {Fore.MAGENTA}${self.config['daily_target']}{Style.RESET_ALL}")
        print(f"{Fore.WHITE}Telegram:{Style.RESET_ALL}    {Fore.GREEN if self.telegram.enabled else Fore.RED}{'Вкл' if self.telegram.enabled else 'Выкл'}{Style.RESET_ALL}\n")
    
    def scan_all_symbols(self):
        """Сканировать все монеты"""
        signals_found = []
        
        for symbol in self.config['symbols']:
            try:
                # Загружаем данные
                candles = self.cex.fetch_ohlcv(symbol, self.config['timeframe'], 100)
                
                if not candles:
                    continue
                
                # Сохраняем последние 10 свечей
                self.save_candles(symbol, candles[-10:])
                
                # Анализируем
                results = self.roger.calculate(self.conn, symbol, self.config['timeframe'], 100)
                
                if not results:
                    continue
                
                # Ищем активные сигналы
                signals = results['signals']
                active = [s for s in signals if s['type'] in ['LONG', 'SHORT', 'LONG (Скальпинг)', 'SHORT (Скальпинг)']]
                
                if active:
                    signals_found.append({
                        'symbol': symbol,
                        'signals': active,
                        'current_candle': results['current_candle'],
                        'rb_formula': results['rb_formula']
                    })
                    
            except Exception as e:
                print(f"{Fore.RED}✗ Ошибка {symbol}: {e}{Style.RESET_ALL}")
        
        return signals_found
    
    def save_candles(self, symbol, candles):
        """Сохранить свечи в БД"""
        cursor = self.conn.cursor()
        
        for candle in candles:
            timestamp, open_p, high, low, close_p, volume = candle
            dt = datetime.utcfromtimestamp(timestamp / 1000)
            
            cursor.execute("""
                INSERT INTO candles (symbol, timeframe, timestamp, datetime, high, low, open, close, volume)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (symbol, timeframe, timestamp) DO NOTHING
            """, (symbol, self.config['timeframe'], timestamp, dt, high, low, open_p, close_p, volume))
        
        self.conn.commit()
        cursor.close()
    
    def show_signals(self, signals_list):
        """Показать найденные сигналы"""
        for result in signals_list:
            symbol = result['symbol']
            candle = result['current_candle']
            signals = result['signals']
            
            for signal in signals:
                signal_type = signal['type']
                
                # Цвет
                if 'LONG' in signal_type:
                    color = Fore.GREEN
                    emoji = '🟢'
                else:
                    color = Fore.RED
                    emoji = '🔴'
                
                print(f"\n{color}{'─'*80}")
                print(f"{emoji} {signal_type} - {symbol}")
                print(f"{color}{'─'*80}{Style.RESET_ALL}")
                
                print(f"{Fore.WHITE}Время:{Style.RESET_ALL}    {Fore.MAGENTA}{candle['datetime']}{Style.RESET_ALL}")
                print(f"{Fore.WHITE}Цена:{Style.RESET_ALL}     {Fore.CYAN}{candle['close']:.8f}{Style.RESET_ALL}")
                
                # Детали сигнала
                for key, value in signal.items():
                    if key not in ['type', 'strategy']:
                        print(f"{Fore.YELLOW}{key}:{Style.RESET_ALL} {value}")
                
                # Отправка в Telegram
                if self.telegram.enabled:
                    self.telegram.send_signal(
                        symbol,
                        signal_type,
                        signal,
                        candle['close']
                    )
                
                print(f"{color}{'─'*80}{Style.RESET_ALL}")
    
    def show_dashboard(self):
        """Показать дашборд со статистикой"""
        stats = self.journal.get_daily_stats()
        
        print(f"\n{Fore.CYAN}{'='*80}")
        print(f"{Fore.CYAN}СТАТИСТИКА ЗА СЕГОДНЯ")
        print(f"{Fore.CYAN}{'='*80}{Style.RESET_ALL}\n")
        
        print(f"{Fore.WHITE}Сделок:{Style.RESET_ALL}       {Fore.CYAN}{stats['total_trades']}{Style.RESET_ALL}")
        print(f"{Fore.GREEN}Успешных:{Style.RESET_ALL}     {Fore.GREEN}{stats['wins']}{Style.RESET_ALL}")
        print(f"{Fore.RED}Убыточных:{Style.RESET_ALL}    {Fore.RED}{stats['losses']}{Style.RESET_ALL}")
        print(f"{Fore.MAGENTA}Открытых:{Style.RESET_ALL}     {Fore.MAGENTA}{stats['open_trades']}{Style.RESET_ALL}\n")
        
        profit_color = Fore.GREEN if stats['total_profit'] > 0 else Fore.RED
        print(f"{Fore.WHITE}Профит:{Style.RESET_ALL}       {profit_color}{stats['total_profit']:+.2f} USDT{Style.RESET_ALL}\n")
        
        # Прогресс к цели
        target = self.config['daily_target']
        progress = (stats['total_profit'] / target * 100) if target > 0 else 0
        
        print(f"{Fore.YELLOW}Цель:{Style.RESET_ALL}         ${target}")
        print(f"{Fore.YELLOW}Прогресс:{Style.RESET_ALL}     {progress:.1f}%")
        
        # Прогресс-бар
        bar_length = 40
        filled = int(bar_length * min(progress, 100) / 100)
        bar = '█' * filled + '░' * (bar_length - filled)
        print(f"{Fore.CYAN}[{bar}]{Style.RESET_ALL}\n")
        
        print(f"{Fore.CYAN}{'='*80}{Style.RESET_ALL}\n")
    
    def run_continuous(self):
        """Непрерывный мониторинг"""
        print(f"{Fore.GREEN}✓ Система запущена! Ctrl+C для остановки{Style.RESET_ALL}\n")
        
        scan_count = 0
        
        try:
            while True:
                scan_count += 1
                now = datetime.now().strftime("%H:%M:%S")
                
                print(f"{Fore.CYAN}{'='*80}")
                print(f"Сканирование #{scan_count} - {now}")
                print(f"{Fore.CYAN}{'='*80}{Style.RESET_ALL}\n")
                
                # Сканируем все монеты
                signals = self.scan_all_symbols()
                
                if signals:
                    print(f"{Fore.GREEN}✓ Найдено {len(signals)} сигналов!{Style.RESET_ALL}")
                    self.show_signals(signals)
                else:
                    print(f"{Fore.YELLOW}○ Сигналов не обнаружено{Style.RESET_ALL}")
                
                # Показываем статистику
                self.show_dashboard()
                
                # Ждём 5 минут
                print(f"{Fore.CYAN}Следующее сканирование через 5 минут...{Style.RESET_ALL}\n")
                time.sleep(300)
                
        except KeyboardInterrupt:
            print(f"\n{Fore.YELLOW}Система остановлена{Style.RESET_ALL}")
            self.cleanup()
    
    def run_menu(self):
        """Режим с меню"""
        while True:
            print(f"\n{Fore.CYAN}{'='*80}")
            print(f"{Fore.CYAN}ГЛАВНОЕ МЕНЮ")
            print(f"{Fore.CYAN}{'='*80}{Style.RESET_ALL}\n")
            
            print(f"{Fore.WHITE}1.{Style.RESET_ALL} Сканировать сейчас")
            print(f"{Fore.WHITE}2.{Style.RESET_ALL} Запустить автомониторинг")
            print(f"{Fore.WHITE}3.{Style.RESET_ALL} Добавить сделку вручную")
            print(f"{Fore.WHITE}4.{Style.RESET_ALL} Закрыть сделку")
            print(f"{Fore.WHITE}5.{Style.RESET_ALL} Показать дневной отчёт")
            print(f"{Fore.WHITE}6.{Style.RESET_ALL} Отправить отчёт в Telegram")
            print(f"{Fore.WHITE}0.{Style.RESET_ALL} Выход\n")
            
            choice = input(f"{Fore.CYAN}Выбери опцию: {Style.RESET_ALL}")
            
            if choice == '1':
                signals = self.scan_all_symbols()
                if signals:
                    self.show_signals(signals)
                else:
                    print(f"{Fore.YELLOW}○ Сигналов не найдено{Style.RESET_ALL}")
            
            elif choice == '2':
                self.run_continuous()
            
            elif choice == '3':
                self.add_trade_manually()
            
            elif choice == '4':
                self.close_trade_manually()
            
            elif choice == '5':
                self.journal.show_daily_report()
            
            elif choice == '6':
                stats = self.journal.get_daily_stats()
                if self.telegram.enabled:
                    self.telegram.send_daily_report(stats)
                    print(f"{Fore.GREEN}✓ Отчёт отправлен в Telegram{Style.RESET_ALL}")
                else:
                    print(f"{Fore.RED}✗ Telegram не настроен{Style.RESET_ALL}")
            
            elif choice == '0':
                print(f"\n{Fore.CYAN}До свидания!{Style.RESET_ALL}\n")
                break
    
    def add_trade_manually(self):
        """Добавить сделку вручную"""
        print(f"\n{Fore.CYAN}Добавление сделки{Style.RESET_ALL}\n")
        
        symbol = input("Символ: ").upper()
        direction = input("Направление (LONG/SHORT): ").upper()
        entry = float(input("Цена входа: "))
        target = float(input("Целевая цена: "))
        stop = float(input("Стоп-лосс: "))
        position = float(input(f"Размер позиции (по умолчанию {self.config['capital']}): ") or self.config['capital'])
        
        self.journal.add_trade(
            symbol=symbol,
            direction=direction,
            entry_price=entry,
            target_price=target,
            stop_price=stop,
            position_size=position,
            leverage=self.config['leverage']
        )
    
    def close_trade_manually(self):
        """Закрыть сделку вручную"""
        # Показываем открытые сделки
        open_trades = self.journal.get_open_trades()
        
        if not open_trades:
            print(f"{Fore.YELLOW}Нет открытых сделок{Style.RESET_ALL}")
            return
        
        print(f"\n{Fore.CYAN}Открытые сделки:{Style.RESET_ALL}\n")
        for trade in open_trades:
            print(f"{trade[0]}. {trade[2]} {trade[3]} @ {trade[4]}")
        
        trade_id = int(input(f"\n{Fore.WHITE}ID сделки для закрытия: {Style.RESET_ALL}"))
        exit_price = float(input(f"{Fore.WHITE}Цена выхода: {Style.RESET_ALL}"))
        
        self.journal.close_trade(trade_id, exit_price)
    
    def cleanup(self):
        """Очистка ресурсов"""
        if self.conn:
            self.conn.close()
        print(f"{Fore.GREEN}✓ Ресурсы освобождены{Style.RESET_ALL}")


# Главный запуск
if __name__ == "__main__":
    # Конфигурация
    config = {
        'symbols': [
            'BTC/USDT',
            'ETH/USDT',
            'SOL/USDT',
            'BNB/USDT',
            'AVAX/USDT'
        ],
        'timeframe': '5m',
        'capital': 100,
        'leverage': 3,
        'daily_target': 100,
        'telegram_token': None,  # Заполни из telegram_config.txt
        'telegram_chat': None    # Заполни из telegram_config.txt
    }
    
    # Загружаем Telegram настройки если есть
    try:
        with open('telegram_config.txt', 'r') as f:
            for line in f:
                if line.startswith('BOT_TOKEN='):
                    config['telegram_token'] = line.split('=')[1].strip()
                elif line.startswith('CHAT_ID='):
                    config['telegram_chat'] = line.split('=')[1].strip()
    except:
        pass
    
    # Запуск системы
    system = TradingSystem(config)
    system.run_menu()
