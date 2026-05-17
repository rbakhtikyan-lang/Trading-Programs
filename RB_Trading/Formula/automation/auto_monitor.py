"""
Auto Monitor - Точка входа для автоматического мониторинга
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import time
from datetime import datetime
from colorama import Fore, Style, init
from monitor import MonitorCore
from notifier import SignalNotifier
from config import get_config

init(autoreset=True)


class AutoMonitor:
    """Автоматический мониторинг торговых сигналов (тонкая обёртка)"""
    
    def __init__(self, symbols=None, timeframe='5m', check_interval=300):
        if symbols is None:
            config = get_config()
            symbols = config['symbols']
            timeframe = config['timeframe']
        
        self.check_interval = check_interval
        
        print(f"{Fore.CYAN}{'='*80}")
        print(f"{Fore.CYAN}AUTO MONITOR - Автоматический мониторинг сигналов")
        print(f"{Fore.CYAN}{'='*80}{Style.RESET_ALL}\n")
        
        self.core = MonitorCore(symbols, timeframe)
        self.notifier = SignalNotifier()
        
        print(f"{Fore.WHITE}Монеты:{Style.RESET_ALL} {Fore.CYAN}{', '.join(symbols)}{Style.RESET_ALL}")
        print(f"{Fore.WHITE}Таймфрейм:{Style.RESET_ALL} {Fore.CYAN}{timeframe}{Style.RESET_ALL}")
        print(f"{Fore.WHITE}Интервал:{Style.RESET_ALL} {Fore.CYAN}{check_interval // 60} минут{Style.RESET_ALL}\n")
    
    def run(self):
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
                for symbol in self.core.symbols:
                    print(f"{Fore.YELLOW}⏳ Сканирую {symbol}...{Style.RESET_ALL}", end=' ')
                    result = self.core.scan_symbol(symbol)
                    
                    if result:
                        print(f"{Fore.GREEN}✓ Сигнал найден!{Style.RESET_ALL}")
                        self.notifier.show_signal(result)
                        signals_found += 1
                    else:
                        print(f"{Fore.WHITE}○ Нет сигналов{Style.RESET_ALL}")
                
                if signals_found == 0:
                    print(f"\n{Fore.YELLOW}○ Сигналов не обнаружено{Style.RESET_ALL}")
                
                print(f"\n{Fore.CYAN}Следующее сканирование через {self.check_interval // 60} мин...{Style.RESET_ALL}")
                print(f"{Fore.CYAN}{'='*80}{Style.RESET_ALL}\n")
                
                time.sleep(self.check_interval)
                
        except KeyboardInterrupt:
            print(f"\n\n{Fore.YELLOW}Мониторинг остановлен пользователем{Style.RESET_ALL}")
            self.core.close()
            print(f"{Fore.GREEN}✓ Ресурсы освобождены{Style.RESET_ALL}")


if __name__ == "__main__":
    config = get_config()
    monitor = AutoMonitor(symbols=config['symbols'], timeframe=config['timeframe'])
    monitor.run()
