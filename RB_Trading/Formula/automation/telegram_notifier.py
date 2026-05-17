"""
Telegram Notifier - Отправка торговых сигналов в Telegram
"""

import requests
from datetime import datetime
from colorama import Fore, Style, init

init(autoreset=True)


class TelegramNotifier:
    """Отправка уведомлений в Telegram"""
    
    def __init__(self, bot_token=None, chat_id=None):
        """
        Args:
            bot_token: Токен Telegram бота (от @BotFather)
            chat_id: ID вашего чата (от @userinfobot)
        """
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.enabled = bot_token and chat_id
        
        if self.enabled:
            self.test_connection()
    
    def test_connection(self):
        """Проверка подключения"""
        try:
            url = f"https://api.telegram.org/bot{self.bot_token}/getMe"
            response = requests.get(url, timeout=5)
            
            if response.status_code == 200:
                bot_info = response.json()
                print(f"{Fore.GREEN}✓ Telegram бот подключен: @{bot_info['result']['username']}{Style.RESET_ALL}")
            else:
                print(f"{Fore.RED}✗ Ошибка подключения к Telegram{Style.RESET_ALL}")
                self.enabled = False
        except Exception as e:
            print(f"{Fore.RED}✗ Telegram недоступен: {e}{Style.RESET_ALL}")
            self.enabled = False
    
    def send_message(self, text, parse_mode='HTML'):
        """Отправить сообщение"""
        if not self.enabled:
            return False
        
        try:
            url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
            
            data = {
                'chat_id': self.chat_id,
                'text': text,
                'parse_mode': parse_mode
            }
            
            response = requests.post(url, json=data, timeout=5)
            return response.status_code == 200
            
        except Exception as e:
            print(f"{Fore.RED}✗ Ошибка отправки в Telegram: {e}{Style.RESET_ALL}")
            return False
    
    def send_signal(self, symbol, signal_type, signal_data, current_price):
        """
        Отправить торговый сигнал
        
        Args:
            symbol: Торговая пара
            signal_type: Тип сигнала (LONG/SHORT)
            signal_data: Данные сигнала (dict)
            current_price: Текущая цена
        """
        # Эмодзи в зависимости от типа
        if 'LONG' in signal_type:
            emoji = '🟢'
            direction = 'LONG'
        else:
            emoji = '🔴'
            direction = 'SHORT'
        
        # Формируем сообщение
        message = f"{emoji} <b>{direction} СИГНАЛ</b>\n\n"
        message += f"📊 <b>{symbol}</b>\n"
        message += f"⏰ {datetime.now().strftime('%H:%M:%S')}\n"
        message += f"💰 Цена: <code>{current_price:.8f}</code>\n\n"
        
        # Вход
        if 'entry' in signal_data:
            message += f"<b>Вход:</b> {signal_data['entry']}\n"
        
        # Цели
        if 'target_1' in signal_data:
            message += f"\n<b>Цели:</b>\n"
            message += f"1️⃣ {signal_data.get('target_1', 'N/A')}\n"
            message += f"2️⃣ {signal_data.get('target_2', 'N/A')}\n"
            message += f"3️⃣ {signal_data.get('target_3', 'N/A')}\n"
        elif 'target' in signal_data:
            message += f"\n<b>Цель:</b> {signal_data['target']}\n"
        
        # Стоп
        if 'stop_loss' in signal_data:
            message += f"\n🛑 <b>Стоп-лосс:</b> {signal_data['stop_loss']}\n"
        
        # Профит
        if 'expected_profit' in signal_data:
            message += f"\n💵 <b>Профит:</b> {signal_data['expected_profit']}\n"
        
        # R/R
        if 'risk_reward' in signal_data:
            message += f"📊 <b>R/R:</b> {signal_data['risk_reward']}\n"
        
        message += f"\n━━━━━━━━━━━━━━━━━━━━"
        message += f"\n<i>Roger's Formula</i>"
        
        return self.send_message(message)
    
    def send_trade_closed(self, symbol, direction, entry, exit, profit_usdt, profit_percent):
        """
        Уведомление о закрытой сделке
        
        Args:
            symbol: Торговая пара
            direction: LONG/SHORT
            entry: Цена входа
            exit: Цена выхода
            profit_usdt: Профит в USDT
            profit_percent: Профит в %
        """
        # Эмодзи
        if profit_usdt > 0:
            emoji = '✅'
            color_tag = '✅'
        else:
            emoji = '❌'
            color_tag = '❌'
        
        message = f"{emoji} <b>Сделка закрыта</b>\n\n"
        message += f"📊 <b>{symbol}</b> | {direction}\n"
        message += f"⏰ {datetime.now().strftime('%H:%M:%S')}\n\n"
        message += f"🔵 Вход: <code>{entry:.8f}</code>\n"
        message += f"🔴 Выход: <code>{exit:.8f}</code>\n\n"
        message += f"{color_tag} <b>Профит: {profit_usdt:+.2f} USDT ({profit_percent:+.2f}%)</b>\n"
        message += f"\n━━━━━━━━━━━━━━━━━━━━"
        
        return self.send_message(message)
    
    def send_daily_report(self, stats):
        """
        Отправить дневной отчёт
        
        Args:
            stats: Статистика за день (dict)
        """
        total = stats['total_trades']
        wins = stats['wins']
        losses = stats['losses']
        profit = stats['total_profit']
        
        win_rate = (wins / total * 100) if total > 0 else 0
        
        # Эмодзи для профита
        if profit > 0:
            profit_emoji = '📈'
        else:
            profit_emoji = '📉'
        
        message = f"📊 <b>ДНЕВНОЙ ОТЧЁТ</b>\n"
        message += f"📅 {datetime.now().strftime('%d.%m.%Y')}\n\n"
        message += f"<b>Сделок:</b> {total}\n"
        message += f"✅ Успешных: {wins} ({win_rate:.1f}%)\n"
        message += f"❌ Убыточных: {losses}\n\n"
        message += f"{profit_emoji} <b>Профит: {profit:+.2f} USDT</b>\n"
        
        # Цель
        target = 100
        progress = (profit / target * 100) if target > 0 else 0
        
        message += f"\n🎯 Цель: ${target}\n"
        message += f"📊 Выполнение: {progress:.1f}%\n"
        
        # Прогресс-бар
        bar_length = 10
        filled = int(bar_length * min(progress, 100) / 100)
        bar = '█' * filled + '░' * (bar_length - filled)
        message += f"[{bar}]\n"
        
        message += f"\n━━━━━━━━━━━━━━━━━━━━"
        message += f"\n<i>Roger's Trading System</i>"
        
        return self.send_message(message)


# Настройка и тестирование
if __name__ == "__main__":
    print(f"{Fore.CYAN}{'='*70}")
    print(f"{Fore.CYAN}НАСТРОЙКА TELEGRAM УВЕДОМЛЕНИЙ")
    print(f"{Fore.CYAN}{'='*70}{Style.RESET_ALL}\n")
    
    print(f"{Fore.YELLOW}Для настройки Telegram уведомлений:{Style.RESET_ALL}\n")
    print(f"1. Создай бота:")
    print(f"   - Открой @BotFather в Telegram")
    print(f"   - Отправь /newbot")
    print(f"   - Следуй инструкциям")
    print(f"   - Получи токен (выглядит как: 123456789:ABC-DEF1234ghIkl-zyx57W2v1u123ew11)\n")
    
    print(f"2. Узнай свой Chat ID:")
    print(f"   - Открой @userinfobot в Telegram")
    print(f"   - Отправь /start")
    print(f"   - Скопируй свой ID (например: 123456789)\n")
    
    print(f"3. Запусти бота:")
    print(f"   - Найди своего бота в Telegram")
    print(f"   - Отправь /start\n")
    
    print(f"{Fore.CYAN}{'─'*70}{Style.RESET_ALL}\n")
    
    # Запрашиваем данные
    bot_token = input(f"{Fore.WHITE}Введи Bot Token (или Enter для пропуска): {Style.RESET_ALL}").strip()
    
    if bot_token:
        chat_id = input(f"{Fore.WHITE}Введи Chat ID: {Style.RESET_ALL}").strip()
        
        # Тестируем
        notifier = TelegramNotifier(bot_token, chat_id)
        
        if notifier.enabled:
            print(f"\n{Fore.GREEN}Отправляю тестовое сообщение...{Style.RESET_ALL}")
            
            success = notifier.send_message(
                "🎉 <b>Telegram уведомления настроены!</b>\n\n"
                "Теперь ты будешь получать торговые сигналы прямо в Telegram!\n\n"
                "<i>Roger's Trading System</i>"
            )
            
            if success:
                print(f"{Fore.GREEN}✓ Сообщение отправлено! Проверь Telegram{Style.RESET_ALL}\n")
                
                # Сохраняем настройки
                with open('telegram_config.txt', 'w') as f:
                    f.write(f"BOT_TOKEN={bot_token}\n")
                    f.write(f"CHAT_ID={chat_id}\n")
                
                print(f"{Fore.GREEN}✓ Настройки сохранены в telegram_config.txt{Style.RESET_ALL}")
            else:
                print(f"{Fore.RED}✗ Не удалось отправить сообщение{Style.RESET_ALL}")
    else:
        print(f"\n{Fore.YELLOW}Настройка пропущена. Уведомления отключены.{Style.RESET_ALL}")
