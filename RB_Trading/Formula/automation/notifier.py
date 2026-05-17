"""
Signal Notifier - Вывод торговых сигналов
"""

from colorama import Fore, Style


class SignalNotifier:
    """Вывод сигналов в консоль / Telegram"""
    
    @staticmethod
    def show_signal(result):
        """Красиво показать сигнал в консоли"""
        symbol = result['symbol']
        candle = result['current_candle']
        signals = result['signals']
        
        for signal in signals:
            signal_type = signal['type']
            
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
            
            if 'strategy' in signal:
                print(f"{Fore.WHITE}Стратегия:{Style.RESET_ALL}   {Fore.YELLOW}{signal['strategy']}{Style.RESET_ALL}")
            
            if 'entry' in signal:
                print(f"\n{Fore.YELLOW}Вход:{Style.RESET_ALL}")
                print(f"  {signal['entry']}")
            
            if 'target_1' in signal:
                print(f"\n{Fore.GREEN}Цели:{Style.RESET_ALL}")
                print(f"  1️  {signal.get('target_1', 'N/A')}")
                print(f"  2️  {signal.get('target_2', 'N/A')}")
                print(f"  3️  {signal.get('target_3', 'N/A')}")
            elif 'target' in signal:
                print(f"\n{Fore.GREEN}Цель:{Style.RESET_ALL}")
                print(f"  {signal['target']}")
            
            if 'stop_loss' in signal:
                print(f"\n{Fore.RED}Стоп-лосс:{Style.RESET_ALL}")
                print(f"  {signal['stop_loss']}")
            
            if 'expected_profit' in signal:
                print(f"\n{Fore.CYAN}Ожидаемый профит:{Style.RESET_ALL} {Fore.GREEN}{signal['expected_profit']}{Style.RESET_ALL}")
            
            if 'risk_reward' in signal:
                print(f"{Fore.CYAN}Risk/Reward:{Style.RESET_ALL} {Fore.MAGENTA}{signal['risk_reward']}{Style.RESET_ALL}")
            
            print(f"{color}{'─'*80}{Style.RESET_ALL}")
    
    @staticmethod
    def send_telegram(signal_data, chat_id=None, token=None):
        """Заготовка под Telegram-уведомления"""
        # TODO: реализовать отправку в Telegram
        pass
