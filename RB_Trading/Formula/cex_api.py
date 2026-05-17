"""
Модуль для работы с CEX (Centralized Exchange)
Использует библиотеку ccxt для подключения к биржам
"""

import ccxt
from datetime import datetime
from colorama import Fore, Style


class CEXConnector:
    """Класс для подключения к CEX и получения данных"""
    
    def __init__(self, api_key=None, api_secret=None, exchange_name='okx'):
        """
        Инициализация коннектора
        
        Args:
            api_key: API ключ (опционально для публичных данных)
            api_secret: API секрет (опционально для публичных данных)
            exchange_name: Название биржи (по умолчанию binance)
        """
        self.exchange_name = exchange_name
        self.api_key = api_key
        self.api_secret = api_secret
        self.exchange = None
        
        self._init_exchange()
    
    def _init_exchange(self):
        """Инициализация подключения к бирже"""
        try:
            exchange_class = getattr(ccxt, self.exchange_name)
            
            config = {
                'enableRateLimit': True,
            }
            
            if self.api_key and self.api_secret:
                config['apiKey'] = self.api_key
                config['secret'] = self.api_secret
            
            self.exchange = exchange_class(config)
            
        except AttributeError:
            print(f"{Fore.RED}✗ Биржа {self.exchange_name} не поддерживается{Style.RESET_ALL}")
            self.exchange = None
        except Exception as e:
            print(f"{Fore.RED}✗ Ошибка инициализации биржи: {e}{Style.RESET_ALL}")
            self.exchange = None
    
    def test_connection(self):
        """Тестирование подключения к бирже"""
        if not self.exchange:
            return False
        
        try:
            self.exchange.load_markets()
            return True
        except Exception as e:
            print(f"{Fore.RED}✗ Ошибка подключения: {e}{Style.RESET_ALL}")
            return False
    
    def get_available_symbols(self):
        """Получить список доступных торговых пар"""
        if not self.exchange:
            return []
        
        try:
            markets = self.exchange.load_markets()
            return list(markets.keys())
        except Exception as e:
            print(f"{Fore.RED}✗ Ошибка получения символов: {e}{Style.RESET_ALL}")
            return []
    
    def fetch_ohlcv(self, symbol, timeframe='1h', limit=100, since=None):
        """
        Получить OHLCV данные (Open, High, Low, Close, Volume)
        
        Args:
            symbol: Торговая пара (например, 'BTC/USDT')
            timeframe: Таймфрейм ('1m', '5m', '15m', '1h', '4h', '1d' и т.д.)
            limit: Количество свечей
            since: Время начала в миллисекундах (опционально)
        
        Returns:
            List of candles: [[timestamp, open, high, low, close, volume], ...]
        """
        if not self.exchange:
            print(f"{Fore.RED}✗ Биржа не инициализирована{Style.RESET_ALL}")
            return []
        
        try:
            # Проверка поддержки символа
            if symbol not in self.exchange.markets:
                self.exchange.load_markets()
            
            # Получение данных
            ohlcv = self.exchange.fetch_ohlcv(
                symbol=symbol,
                timeframe=timeframe,
                limit=limit,
                since=since
            )
            
            return ohlcv
            
        except ccxt.NetworkError as e:
            print(f"{Fore.RED}✗ Ошибка сети: {e}{Style.RESET_ALL}")
            return []
        except ccxt.ExchangeError as e:
            print(f"{Fore.RED}✗ Ошибка биржи: {e}{Style.RESET_ALL}")
            return []
        except Exception as e:
            print(f"{Fore.RED}✗ Неожиданная ошибка: {e}{Style.RESET_ALL}")
            return []
    
    def fetch_all_historical_data(self, symbol, timeframe='1d', start_date=None):
        """
        Получить всю историческую информацию по свечам
        
        Args:
            symbol: Торговая пара
            timeframe: Таймфрейм
            start_date: Дата начала (datetime объект или timestamp в мс)
        
        Returns:
            List of all candles
        """
        if not self.exchange:
            print(f"{Fore.RED}✗ Биржа не инициализирована{Style.RESET_ALL}")
            return []
        
        all_candles = []
        
        try:
            # Если start_date - datetime объект, конвертируем в timestamp
            if isinstance(start_date, datetime):
                since = int(start_date.timestamp() * 1000)
            elif start_date:
                since = start_date
            else:
                # По умолчанию берем с начала 2020 года
                since = int(datetime(2020, 1, 1).timestamp() * 1000)
            
            print(f"{Fore.YELLOW}⏳ Загрузка исторических данных...{Style.RESET_ALL}")
            
            while True:
                candles = self.fetch_ohlcv(symbol, timeframe, limit=1000, since=since)
                
                if not candles:
                    break
                
                all_candles.extend(candles)
                
                # Обновляем since для следующей итерации
                since = candles[-1][0] + 1
                
                print(f"{Fore.CYAN}  Загружено {len(all_candles)} свечей...{Style.RESET_ALL}", end='\r')
                
                # Если получили меньше 1000, значит это все данные
                if len(candles) < 1000:
                    break
            
            print(f"\n{Fore.GREEN}✓ Всего загружено {len(all_candles)} свечей{Style.RESET_ALL}")
            return all_candles
            
        except Exception as e:
            print(f"\n{Fore.RED}✗ Ошибка загрузки исторических данных: {e}{Style.RESET_ALL}")
            return all_candles
    
    def get_ticker(self, symbol):
        """Получить текущую цену и информацию о тикере"""
        if not self.exchange:
            return None
        
        try:
            ticker = self.exchange.fetch_ticker(symbol)
            return ticker
        except Exception as e:
            print(f"{Fore.RED}✗ Ошибка получения тикера: {e}{Style.RESET_ALL}")
            return None
    
    def display_candle_data(self, candles, limit=10):
        """
        Вывести данные свечей в терминал
        
        Args:
            candles: Список свечей
            limit: Количество свечей для вывода
        """
        if not candles:
            print(f"{Fore.YELLOW}⚠ Нет данных для отображения{Style.RESET_ALL}")
            return
        
        print(f"\n{Fore.CYAN}{'─'*120}")
        print(f"{Fore.CYAN}{'Дата/Время':<20} {'Open':<15} {'High':<15} {'Low':<15} {'Close':<15} {'Volume':<15}")
        print(f"{Fore.CYAN}{'─'*120}{Style.RESET_ALL}")
        
        # Показываем только последние limit свечей
        display_candles = candles[-limit:] if len(candles) > limit else candles
        
        for candle in display_candles:
            timestamp, open_price, high, low, close_price, volume = candle
            dt = datetime.fromtimestamp(timestamp / 1000)
            
            # Определяем цвет для close (зеленый если выросла, красный если упала)
            close_color = Fore.GREEN if close_price >= open_price else Fore.RED
            
            print(f"{Fore.WHITE}{dt.strftime('%Y-%m-%d %H:%M:%S'):<20} "
                  f"{Fore.YELLOW}{open_price:<15.8f} "
                  f"{Fore.GREEN}{high:<15.8f} "
                  f"{Fore.RED}{low:<15.8f} "
                  f"{close_color}{close_price:<15.8f} "
                  f"{Fore.MAGENTA}{volume:<15.2f}{Style.RESET_ALL}")
        
        print(f"{Fore.CYAN}{'─'*120}{Style.RESET_ALL}\n")


# Пример использования
if __name__ == "__main__":
    # Создание коннектора (без API ключей для публичных данных)
    connector = CEXConnector()
    
    # Тестирование подключения
    if connector.test_connection():
        print(f"{Fore.GREEN}✓ Успешное подключение к бирже{Style.RESET_ALL}")
        
        # Получение данных
        candles = connector.fetch_ohlcv('BTC/USDT', '1h', 20)
        
        if candles:
            connector.display_candle_data(candles)
    else:
        print(f"{Fore.RED}✗ Не удалось подключиться к бирже{Style.RESET_ALL}")
