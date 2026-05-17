"""
Модуль RB Formula для математического анализа свечных данных
Выполняет различные расчеты на основе данных High/Low
"""

from colorama import Fore, Style
import statistics
from datetime import datetime


class RBFormula:
    """Класс для выполнения математических операций с данными свечей"""
    
    def __init__(self):
        self.results = {}
    
    def calculate(self, conn, symbol, timeframe, limit=100):
        """
        Выполнить расчеты для указанного символа
        
        Args:
            conn: Подключение к PostgreSQL
            symbol: Торговая пара
            timeframe: Таймфрейм
            limit: Количество свечей для анализа
        
        Returns:
            Dictionary с результатами расчетов
        """
        try:
            cursor = conn.cursor()
            
            # Получение данных из БД
            cursor.execute("""
                SELECT timestamp, datetime, high, low, open, close, volume
                FROM candles
                WHERE symbol = %s AND timeframe = %s
                ORDER BY timestamp DESC
                LIMIT %s
            """, (symbol, timeframe, limit))
            
            rows = cursor.fetchall()
            cursor.close()
            
            if not rows:
                return None
            
            # Подготовка данных (конвертируем Decimal в float)
            highs = [float(row[2]) for row in rows]
            lows = [float(row[3]) for row in rows]
            opens = [float(row[4]) for row in rows]
            closes = [float(row[5]) for row in rows]
            volumes = [float(row[6]) for row in rows]
            
            # Расчет различных метрик
            results = {
                'symbol': symbol,
                'timeframe': timeframe,
                'candles_count': len(rows),
                'date_range': {
                    'start': rows[-1][1],
                    'end': rows[0][1]
                },
                'high_low_analysis': self._analyze_high_low(highs, lows),
                'range_analysis': self._analyze_range(highs, lows),
                'price_movement': self._analyze_price_movement(opens, closes),
                'volume_analysis': self._analyze_volume(volumes),
                'volatility': self._calculate_volatility(highs, lows, closes),
                'support_resistance': self._find_support_resistance(highs, lows)
            }
            
            return results
            
        except Exception as e:
            print(f"{Fore.RED}✗ Ошибка расчета: {e}{Style.RESET_ALL}")
            return None
    
    def _analyze_high_low(self, highs, lows):
        """Анализ максимумов и минимумов"""
        return {
            'max_high': max(highs),
            'min_high': min(highs),
            'avg_high': statistics.mean(highs),
            'max_low': max(lows),
            'min_low': min(lows),
            'avg_low': statistics.mean(lows),
            'total_range': max(highs) - min(lows)
        }
    
    def _analyze_range(self, highs, lows):
        """Анализ диапазонов свечей"""
        ranges = [h - l for h, l in zip(highs, lows)]
        
        return {
            'avg_range': statistics.mean(ranges),
            'max_range': max(ranges),
            'min_range': min(ranges),
            'median_range': statistics.median(ranges),
            'std_dev_range': statistics.stdev(ranges) if len(ranges) > 1 else 0
        }
    
    def _analyze_price_movement(self, opens, closes):
        """Анализ движения цены"""
        movements = [c - o for o, c in zip(opens, closes)]
        bullish = sum(1 for m in movements if m > 0)
        bearish = sum(1 for m in movements if m < 0)
        neutral = sum(1 for m in movements if m == 0)
        
        return {
            'total_movement': sum(movements),
            'avg_movement': statistics.mean(movements),
            'bullish_candles': bullish,
            'bearish_candles': bearish,
            'neutral_candles': neutral,
            'bullish_percentage': (bullish / len(movements)) * 100,
            'bearish_percentage': (bearish / len(movements)) * 100
        }
    
    def _analyze_volume(self, volumes):
        """Анализ объема торгов"""
        return {
            'total_volume': sum(volumes),
            'avg_volume': statistics.mean(volumes),
            'max_volume': max(volumes),
            'min_volume': min(volumes),
            'median_volume': statistics.median(volumes)
        }
    
    def _calculate_volatility(self, highs, lows, closes):
        """Расчет волатильности"""
        # ATR (Average True Range) упрощенный
        ranges = [h - l for h, l in zip(highs, lows)]
        atr = statistics.mean(ranges)
        
        # Стандартное отклонение цен закрытия
        price_std = statistics.stdev(closes) if len(closes) > 1 else 0
        
        # Коэффициент вариации
        avg_close = statistics.mean(closes)
        cv = (price_std / avg_close * 100) if avg_close != 0 else 0
        
        return {
            'atr': atr,
            'price_std_dev': price_std,
            'coefficient_of_variation': cv,
            'volatility_level': self._get_volatility_level(cv)
        }
    
    def _get_volatility_level(self, cv):
        """Определение уровня волатильности"""
        if cv < 1:
            return 'Очень низкая'
        elif cv < 2:
            return 'Низкая'
        elif cv < 3:
            return 'Средняя'
        elif cv < 5:
            return 'Высокая'
        else:
            return 'Очень высокая'
    
    def _find_support_resistance(self, highs, lows):
        """Поиск уровней поддержки и сопротивления"""
        # Простой метод на основе кластеризации цен
        all_prices = highs + lows
        all_prices.sort()
        
        # Находим уровни где цена часто останавливалась
        support_levels = []
        resistance_levels = []
        
        # Разделяем на зоны
        price_range = max(all_prices) - min(all_prices)
        num_zones = 10
        zone_size = price_range / num_zones
        
        zones = {}
        for price in all_prices:
            zone = int((price - min(all_prices)) / zone_size)
            zones[zone] = zones.get(zone, 0) + 1
        
        # Находим наиболее частые зоны
        sorted_zones = sorted(zones.items(), key=lambda x: x[1], reverse=True)
        
        if len(sorted_zones) >= 2:
            # Первая зона - сопротивление (верхняя)
            # Последняя зона - поддержка (нижняя)
            resistance_zone = sorted_zones[0][0]
            support_zone = sorted_zones[-1][0]
            
            resistance_levels.append(min(all_prices) + (resistance_zone + 0.5) * zone_size)
            support_levels.append(min(all_prices) + (support_zone + 0.5) * zone_size)
        
        return {
            'resistance_levels': resistance_levels[:3],  # Топ 3
            'support_levels': support_levels[:3],  # Топ 3
            'current_range': {
                'high': max(all_prices),
                'low': min(all_prices)
            }
        }
    
    def display_results(self, results):
        """
        Вывод результатов анализа в терминал
        
        Args:
            results: Dictionary с результатами расчетов
        """
        if not results:
            print(f"{Fore.RED}✗ Нет результатов для отображения{Style.RESET_ALL}")
            return
        
        print(f"\n{Fore.CYAN}{'='*80}")
        print(f"{Fore.CYAN}РЕЗУЛЬТАТЫ АНАЛИЗА RB FORMULA")
        print(f"{Fore.CYAN}{'='*80}{Style.RESET_ALL}\n")
        
        # Основная информация
        print(f"{Fore.YELLOW}{'─'*80}")
        print(f"{Fore.YELLOW}ОСНОВНАЯ ИНФОРМАЦИЯ")
        print(f"{Fore.YELLOW}{'─'*80}{Style.RESET_ALL}")
        print(f"{Fore.WHITE}Символ:{Style.RESET_ALL} {Fore.CYAN}{results['symbol']}{Style.RESET_ALL}")
        print(f"{Fore.WHITE}Таймфрейм:{Style.RESET_ALL} {Fore.CYAN}{results['timeframe']}{Style.RESET_ALL}")
        print(f"{Fore.WHITE}Количество свечей:{Style.RESET_ALL} {Fore.CYAN}{results['candles_count']}{Style.RESET_ALL}")
        print(f"{Fore.WHITE}Период:{Style.RESET_ALL} {Fore.MAGENTA}{results['date_range']['start']}{Style.RESET_ALL} → {Fore.MAGENTA}{results['date_range']['end']}{Style.RESET_ALL}")
        
        # High/Low анализ
        hl = results['high_low_analysis']
        print(f"\n{Fore.YELLOW}{'─'*80}")
        print(f"{Fore.YELLOW}АНАЛИЗ HIGH/LOW")
        print(f"{Fore.YELLOW}{'─'*80}{Style.RESET_ALL}")
        print(f"{Fore.WHITE}Максимальный High:{Style.RESET_ALL} {Fore.GREEN}{hl['max_high']:.8f}{Style.RESET_ALL}")
        print(f"{Fore.WHITE}Минимальный Low:{Style.RESET_ALL} {Fore.RED}{hl['min_low']:.8f}{Style.RESET_ALL}")
        print(f"{Fore.WHITE}Средний High:{Style.RESET_ALL} {Fore.CYAN}{hl['avg_high']:.8f}{Style.RESET_ALL}")
        print(f"{Fore.WHITE}Средний Low:{Style.RESET_ALL} {Fore.CYAN}{hl['avg_low']:.8f}{Style.RESET_ALL}")
        print(f"{Fore.WHITE}Общий диапазон:{Style.RESET_ALL} {Fore.MAGENTA}{hl['total_range']:.8f}{Style.RESET_ALL}")
        
        # Анализ диапазонов
        ra = results['range_analysis']
        print(f"\n{Fore.YELLOW}{'─'*80}")
        print(f"{Fore.YELLOW}АНАЛИЗ ДИАПАЗОНОВ СВЕЧЕЙ")
        print(f"{Fore.YELLOW}{'─'*80}{Style.RESET_ALL}")
        print(f"{Fore.WHITE}Средний диапазон:{Style.RESET_ALL} {Fore.CYAN}{ra['avg_range']:.8f}{Style.RESET_ALL}")
        print(f"{Fore.WHITE}Максимальный диапазон:{Style.RESET_ALL} {Fore.GREEN}{ra['max_range']:.8f}{Style.RESET_ALL}")
        print(f"{Fore.WHITE}Минимальный диапазон:{Style.RESET_ALL} {Fore.RED}{ra['min_range']:.8f}{Style.RESET_ALL}")
        print(f"{Fore.WHITE}Медианный диапазон:{Style.RESET_ALL} {Fore.CYAN}{ra['median_range']:.8f}{Style.RESET_ALL}")
        print(f"{Fore.WHITE}Стандартное отклонение:{Style.RESET_ALL} {Fore.MAGENTA}{ra['std_dev_range']:.8f}{Style.RESET_ALL}")
        
        # Движение цены
        pm = results['price_movement']
        print(f"\n{Fore.YELLOW}{'─'*80}")
        print(f"{Fore.YELLOW}ДВИЖЕНИЕ ЦЕНЫ")
        print(f"{Fore.YELLOW}{'─'*80}{Style.RESET_ALL}")
        print(f"{Fore.WHITE}Общее движение:{Style.RESET_ALL} {Fore.CYAN}{pm['total_movement']:.8f}{Style.RESET_ALL}")
        print(f"{Fore.WHITE}Среднее движение:{Style.RESET_ALL} {Fore.CYAN}{pm['avg_movement']:.8f}{Style.RESET_ALL}")
        print(f"{Fore.WHITE}Бычьих свечей:{Style.RESET_ALL} {Fore.GREEN}{pm['bullish_candles']} ({pm['bullish_percentage']:.1f}%){Style.RESET_ALL}")
        print(f"{Fore.WHITE}Медвежьих свечей:{Style.RESET_ALL} {Fore.RED}{pm['bearish_candles']} ({pm['bearish_percentage']:.1f}%){Style.RESET_ALL}")
        print(f"{Fore.WHITE}Нейтральных свечей:{Style.RESET_ALL} {Fore.YELLOW}{pm['neutral_candles']}{Style.RESET_ALL}")
        
        # Анализ объема
        va = results['volume_analysis']
        print(f"\n{Fore.YELLOW}{'─'*80}")
        print(f"{Fore.YELLOW}АНАЛИЗ ОБЪЕМА")
        print(f"{Fore.YELLOW}{'─'*80}{Style.RESET_ALL}")
        print(f"{Fore.WHITE}Общий объем:{Style.RESET_ALL} {Fore.CYAN}{va['total_volume']:.2f}{Style.RESET_ALL}")
        print(f"{Fore.WHITE}Средний объем:{Style.RESET_ALL} {Fore.CYAN}{va['avg_volume']:.2f}{Style.RESET_ALL}")
        print(f"{Fore.WHITE}Максимальный объем:{Style.RESET_ALL} {Fore.GREEN}{va['max_volume']:.2f}{Style.RESET_ALL}")
        print(f"{Fore.WHITE}Минимальный объем:{Style.RESET_ALL} {Fore.RED}{va['min_volume']:.2f}{Style.RESET_ALL}")
        
        # Волатильность
        vol = results['volatility']
        print(f"\n{Fore.YELLOW}{'─'*80}")
        print(f"{Fore.YELLOW}ВОЛАТИЛЬНОСТЬ")
        print(f"{Fore.YELLOW}{'─'*80}{Style.RESET_ALL}")
        print(f"{Fore.WHITE}ATR (Average True Range):{Style.RESET_ALL} {Fore.CYAN}{vol['atr']:.8f}{Style.RESET_ALL}")
        print(f"{Fore.WHITE}Стандартное отклонение цены:{Style.RESET_ALL} {Fore.CYAN}{vol['price_std_dev']:.8f}{Style.RESET_ALL}")
        print(f"{Fore.WHITE}Коэффициент вариации:{Style.RESET_ALL} {Fore.CYAN}{vol['coefficient_of_variation']:.2f}%{Style.RESET_ALL}")
        print(f"{Fore.WHITE}Уровень волатильности:{Style.RESET_ALL} {Fore.MAGENTA}{vol['volatility_level']}{Style.RESET_ALL}")
        
        # Поддержка/Сопротивление
        sr = results['support_resistance']
        print(f"\n{Fore.YELLOW}{'─'*80}")
        print(f"{Fore.YELLOW}УРОВНИ ПОДДЕРЖКИ И СОПРОТИВЛЕНИЯ")
        print(f"{Fore.YELLOW}{'─'*80}{Style.RESET_ALL}")
        
        if sr['resistance_levels']:
            print(f"{Fore.WHITE}Уровни сопротивления:{Style.RESET_ALL}")
            for i, level in enumerate(sr['resistance_levels'], 1):
                print(f"  {Fore.GREEN}{i}. {level:.8f}{Style.RESET_ALL}")
        
        if sr['support_levels']:
            print(f"{Fore.WHITE}Уровни поддержки:{Style.RESET_ALL}")
            for i, level in enumerate(sr['support_levels'], 1):
                print(f"  {Fore.RED}{i}. {level:.8f}{Style.RESET_ALL}")
        
        print(f"\n{Fore.CYAN}{'='*80}{Style.RESET_ALL}\n")


# Пример использования
if __name__ == "__main__":
    import psycopg2
    
    # Подключение к БД
    try:
        conn = psycopg2.connect(
            dbname="trading_db",
            user="postgres",
            password="your_password",
            host="localhost"
        )
        
        rb = RBFormula()
        results = rb.calculate(conn, 'BTC/USDT', '1h', 100)
        
        if results:
            rb.display_results(results)
        
        conn.close()
        
    except Exception as e:
        print(f"{Fore.RED}✗ Ошибка: {e}{Style.RESET_ALL}")
