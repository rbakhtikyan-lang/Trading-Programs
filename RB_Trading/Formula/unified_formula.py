"""
Unified Trading Formulas - RB Formula + Roger's Formula
Объединённый модуль технического анализа
"""

import statistics
from colorama import Fore, Style
from datetime import datetime


class RBFormula:
    """Статистический анализ свечных данных: High/Low, диапазоны, волатильность"""
    
    def __init__(self):
        self.results = {}
    
    def calculate(self, conn, symbol, timeframe, limit=100):
        """Основной расчёт статистических метрик"""
        try:
            cursor = conn.cursor()
            
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
            
            # Конвертируем Decimal в float
            highs = [float(row[2]) for row in rows]
            lows = [float(row[3]) for row in rows]
            opens = [float(row[4]) for row in rows]
            closes = [float(row[5]) for row in rows]
            volumes = [float(row[6]) for row in rows]
            
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
        ranges = [h - l for h, l in zip(highs, lows)]
        return {
            'avg_range': statistics.mean(ranges),
            'max_range': max(ranges),
            'min_range': min(ranges),
            'median_range': statistics.median(ranges),
            'std_dev_range': statistics.stdev(ranges) if len(ranges) > 1 else 0
        }
    
    def _analyze_price_movement(self, opens, closes):
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
        return {
            'total_volume': sum(volumes),
            'avg_volume': statistics.mean(volumes),
            'max_volume': max(volumes),
            'min_volume': min(volumes),
            'median_volume': statistics.median(volumes)
        }
    
    def _calculate_volatility(self, highs, lows, closes):
        ranges = [h - l for h, l in zip(highs, lows)]
        atr = statistics.mean(ranges)
        price_std = statistics.stdev(closes) if len(closes) > 1 else 0
        avg_close = statistics.mean(closes)
        cv = (price_std / avg_close * 100) if avg_close != 0 else 0
        
        return {
            'atr': atr,
            'price_std_dev': price_std,
            'coefficient_of_variation': cv,
            'volatility_level': self._get_volatility_level(cv)
        }
    
    def _get_volatility_level(self, cv):
        if cv < 1: return 'Очень низкая'
        elif cv < 2: return 'Низкая'
        elif cv < 3: return 'Средняя'
        elif cv < 5: return 'Высокая'
        else: return 'Очень высокая'
    
    def _find_support_resistance(self, highs, lows):
        all_prices = highs + lows
        all_prices.sort()
        
        support_levels = []
        resistance_levels = []
        
        price_range = max(all_prices) - min(all_prices)
        num_zones = 10
        zone_size = price_range / num_zones if price_range > 0 else 1
        
        zones = {}
        for price in all_prices:
            zone = int((price - min(all_prices)) / zone_size)
            zones[zone] = zones.get(zone, 0) + 1
        
        sorted_zones = sorted(zones.items(), key=lambda x: x[1], reverse=True)
        
        if len(sorted_zones) >= 2:
            resistance_zone = sorted_zones[0][0]
            support_zone = sorted_zones[-1][0]
            resistance_levels.append(min(all_prices) + (resistance_zone + 0.5) * zone_size)
            support_levels.append(min(all_prices) + (support_zone + 0.5) * zone_size)
        
        return {
            'resistance_levels': resistance_levels[:3],
            'support_levels': support_levels[:3],
            'current_range': {
                'high': max(all_prices),
                'low': min(all_prices)
            }
        }
    
    def display_results(self, results):
        """Вывод результатов статистического анализа"""
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


class RogerFormula:
    """Авторская формула Roger's - проекция диапазона свечи для целей"""
    
    def __init__(self):
        self.results = {}
    
    def calculate(self, conn, symbol, timeframe, limit=100):
        """Основной расчёт по формуле Roger's"""
        try:
            cursor = conn.cursor()
            
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
            
            # Конвертируем Decimal в float
            highs = [float(row[2]) for row in rows]
            lows = [float(row[3]) for row in rows]
            opens = [float(row[4]) for row in rows]
            closes = [float(row[5]) for row in rows]
            volumes = [float(row[6]) for row in rows]
            
            current_candle = {
                'datetime': rows[0][1],
                'HP': highs[0],
                'LP': lows[0],
                'open': opens[0],
                'close': closes[0],
                'volume': volumes[0]
            }
            
            rb_analysis = self._apply_roger_formula(current_candle, highs, lows, closes)
            statistics_data = self._calculate_statistics(highs, lows, closes, volumes)
            signals = self._generate_trading_signals(current_candle, rb_analysis, statistics_data)
            
            results = {
                'symbol': symbol,
                'timeframe': timeframe,
                'datetime': current_candle['datetime'],
                'current_candle': current_candle,
                'rb_formula': rb_analysis,
                'statistics': statistics_data,
                'signals': signals,
                'candles_analyzed': len(rows)
            }
            
            return results
            
        except Exception as e:
            print(f"{Fore.RED}✗ Ошибка расчёта: {e}{Style.RESET_ALL}")
            import traceback
            traceback.print_exc()
            return None
    
    def _apply_roger_formula(self, candle, highs, lows, closes):
        """Применение авторской формулы Roger's"""
        HP = candle['HP']
        LP = candle['LP']
        
        # БЛОК 1
        max_potential_up = HP + LP
        max_potential_down = LP - HP
        
        # БЛОК 2
        A = HP - LP
        PL = HP + A
        
        # БЛОК 3
        PS = LP - A
        
        # БЛОК 4
        half_A = A / 2
        PL_scalp = HP + half_A
        PS_scalp = LP - half_A
        mid_point = LP + half_A
        
        # Динамический расчёт
        recent_20 = list(zip(highs[-20:], lows[-20:])) if len(highs) >= 20 else list(zip(highs, lows))
        avg_range = statistics.mean([h - l for h, l in recent_20]) if recent_20 else A
        
        PL_dynamic = HP + avg_range
        PS_dynamic = LP - avg_range
        range_ratio = A / avg_range if avg_range > 0 else 1
        
        return {
            'block_1_max_potential': {
                'up': max_potential_up,
                'down': max_potential_down,
                'description': 'Максимальный потенциал движения'
            },
            'block_2_long': {
                'A': A,
                'PL': PL,
                'PL_dynamic': PL_dynamic,
                'description': 'Цели для Long позиции'
            },
            'block_3_short': {
                'PS': PS,
                'PS_dynamic': PS_dynamic,
                'description': 'Цели для Short позиции'
            },
            'block_4_scalping': {
                'half_A': half_A,
                'PL_scalp': PL_scalp,
                'PS_scalp': PS_scalp,
                'mid_point': mid_point,
                'description': 'Уровни для скальпинга'
            },
            'advanced': {
                'avg_range_20': avg_range,
                'range_ratio': range_ratio,
                'volatility': 'Высокая' if range_ratio > 1.5 else 'Средняя' if range_ratio > 0.8 else 'Низкая'
            }
        }
    
    def _calculate_statistics(self, highs, lows, closes, volumes):
        return {
            'max_high': max(highs),
            'min_low': min(lows),
            'avg_range': statistics.mean([h - l for h, l in zip(highs, lows)]),
            'current_price': closes[0],
            'price_change_pct': ((closes[0] - closes[-1]) / closes[-1] * 100) if len(closes) > 1 else 0,
            'total_volume': sum(volumes),
            'avg_volume': statistics.mean(volumes)
        }
    
    def _generate_trading_signals(self, candle, rb_analysis, stats):
        current_price = candle['close']
        HP = candle['HP']
        LP = candle['LP']
        
        A = rb_analysis['block_2_long']['A']
        half_A = rb_analysis['block_4_scalping']['half_A']
        mid_point = rb_analysis['block_4_scalping']['mid_point']
        
        PL = rb_analysis['block_2_long']['PL']
        PS = rb_analysis['block_3_short']['PS']
        PL_scalp = rb_analysis['block_4_scalping']['PL_scalp']
        PS_scalp = rb_analysis['block_4_scalping']['PS_scalp']
        
        signals = []
        
        if current_price <= (LP + half_A):
            signals.append({
                'type': 'LONG',
                'strategy': 'Позиционная торговля',
                'entry': f"около {LP:.8f}",
                'target_1': f"{mid_point:.8f} (50% движения)",
                'target_2': f"{HP:.8f} (High)",
                'target_3': f"{PL:.8f} (RB Formula)",
                'stop_loss': f"{PS:.8f}",
                'risk_reward': f"1:{round((PL - LP) / A, 2)}" if A > 0 else "N/A"
            })
            signals.append({
                'type': 'LONG (Скальпинг)',
                'strategy': 'Быстрый профит',
                'entry': f"около {LP:.8f}",
                'target': f"{PL_scalp:.8f}",
                'stop_loss': f"{LP - (half_A * 0.5):.8f}",
                'expected_profit': f"{half_A:.8f} USDT"
            })
        
        if current_price >= (HP - half_A):
            signals.append({
                'type': 'SHORT',
                'strategy': 'Позиционная торговля',
                'entry': f"около {HP:.8f}",
                'target_1': f"{mid_point:.8f} (50% движения)",
                'target_2': f"{LP:.8f} (Low)",
                'target_3': f"{PS:.8f} (RB Formula)",
                'stop_loss': f"{PL:.8f}",
                'risk_reward': f"1:{round((HP - PS) / A, 2)}" if A > 0 else "N/A"
            })
            signals.append({
                'type': 'SHORT (Скальпинг)',
                'strategy': 'Быстрый профит',
                'entry': f"около {HP:.8f}",
                'target': f"{PS_scalp:.8f}",
                'stop_loss': f"{HP + (half_A * 0.5):.8f}",
                'expected_profit': f"{half_A:.8f} USDT"
            })
        
        if not signals:
            signals.append({
                'type': 'НЕЙТРАЛЬНО',
                'strategy': 'Ожидание',
                'message': f"Цена в середине диапазона ({mid_point:.2f}). Ждём движения к границам."
            })
        
        return signals
    
    def display_results(self, results):
        """Красивый вывод результатов в терминал"""
        if not results:
            print(f"{Fore.RED}✗ Нет результатов для отображения{Style.RESET_ALL}")
            return
        
        print(f"\n{Fore.CYAN}{'='*80}")
        print(f"{Fore.CYAN}ROGER'S FORMULA (RB) - РЕЗУЛЬТАТЫ АНАЛИЗА")
        print(f"{Fore.CYAN}{'='*80}{Style.RESET_ALL}\n")
        
        print(f"{Fore.YELLOW}{'─'*80}")
        print(f"{Fore.YELLOW}ОСНОВНАЯ ИНФОРМАЦИЯ")
        print(f"{Fore.YELLOW}{'─'*80}{Style.RESET_ALL}")
        print(f"{Fore.WHITE}Символ:{Style.RESET_ALL} {Fore.CYAN}{results['symbol']}{Style.RESET_ALL}")
        print(f"{Fore.WHITE}Таймфрейм:{Style.RESET_ALL} {Fore.CYAN}{results['timeframe']}{Style.RESET_ALL}")
        print(f"{Fore.WHITE}Время:{Style.RESET_ALL} {Fore.MAGENTA}{results['datetime']}{Style.RESET_ALL}")
        print(f"{Fore.WHITE}Свечей проанализировано:{Style.RESET_ALL} {Fore.CYAN}{results['candles_analyzed']}{Style.RESET_ALL}")
        
        candle = results['current_candle']
        print(f"\n{Fore.YELLOW}{'─'*80}")
        print(f"{Fore.YELLOW}ТЕКУЩАЯ СВЕЧА")
        print(f"{Fore.YELLOW}{'─'*80}{Style.RESET_ALL}")
        print(f"{Fore.WHITE}High Price (HP):{Style.RESET_ALL} {Fore.GREEN}{candle['HP']:.8f}{Style.RESET_ALL}")
        print(f"{Fore.WHITE}Low Price (LP):{Style.RESET_ALL} {Fore.RED}{candle['LP']:.8f}{Style.RESET_ALL}")
        print(f"{Fore.WHITE}Close:{Style.RESET_ALL} {Fore.CYAN}{candle['close']:.8f}{Style.RESET_ALL}")
        print(f"{Fore.WHITE}Volume:{Style.RESET_ALL} {Fore.MAGENTA}{candle['volume']:.2f}{Style.RESET_ALL}")
        
        rb = results['rb_formula']
        
        block1 = rb['block_1_max_potential']
        print(f"\n{Fore.YELLOW}{'─'*80}")
        print(f"{Fore.YELLOW}БЛОК 1: МАКСИМАЛЬНЫЙ ПОТЕНЦИАЛ ДВИЖЕНИЯ")
        print(f"{Fore.YELLOW}{'─'*80}{Style.RESET_ALL}")
        print(f"{Fore.WHITE}Потенциал ВВЕРХ (HP + LP):{Style.RESET_ALL} {Fore.GREEN}{block1['up']:.8f}{Style.RESET_ALL}")
        print(f"{Fore.WHITE}Потенциал ВНИЗ (LP - HP):{Style.RESET_ALL} {Fore.RED}{block1['down']:.8f}{Style.RESET_ALL}")
        
        block2 = rb['block_2_long']
        print(f"\n{Fore.YELLOW}{'─'*80}")
        print(f"{Fore.YELLOW}БЛОК 2: ЦЕЛИ ДЛЯ LONG ПОЗИЦИИ")
        print(f"{Fore.YELLOW}{'─'*80}{Style.RESET_ALL}")
        print(f"{Fore.WHITE}Диапазон (A = HP - LP):{Style.RESET_ALL} {Fore.CYAN}{block2['A']:.8f}{Style.RESET_ALL}")
        print(f"{Fore.WHITE}Price Long (PL = HP + A):{Style.RESET_ALL} {Fore.GREEN}{block2['PL']:.8f}{Style.RESET_ALL}")
        print(f"{Fore.WHITE}PL Dynamic (учёт истории):{Style.RESET_ALL} {Fore.GREEN}{block2['PL_dynamic']:.8f}{Style.RESET_ALL}")
        
        block3 = rb['block_3_short']
        print(f"\n{Fore.YELLOW}{'─'*80}")
        print(f"{Fore.YELLOW}БЛОК 3: ЦЕЛИ ДЛЯ SHORT ПОЗИЦИИ")
        print(f"{Fore.YELLOW}{'─'*80}{Style.RESET_ALL}")
        print(f"{Fore.WHITE}Price Short (PS = LP - A):{Style.RESET_ALL} {Fore.RED}{block3['PS']:.8f}{Style.RESET_ALL}")
        print(f"{Fore.WHITE}PS Dynamic (учёт истории):{Style.RESET_ALL} {Fore.RED}{block3['PS_dynamic']:.8f}{Style.RESET_ALL}")
        
        block4 = rb['block_4_scalping']
        print(f"\n{Fore.YELLOW}{'─'*80}")
        print(f"{Fore.YELLOW}БЛОК 4: УРОВНИ ДЛЯ СКАЛЬПИНГА")
        print(f"{Fore.YELLOW}{'─'*80}{Style.RESET_ALL}")
        print(f"{Fore.WHITE}Половина диапазона (A/2):{Style.RESET_ALL} {Fore.CYAN}{block4['half_A']:.8f}{Style.RESET_ALL}")
        print(f"{Fore.WHITE}PL Скальпинг:{Style.RESET_ALL} {Fore.GREEN}{block4['PL_scalp']:.8f}{Style.RESET_ALL}")
        print(f"{Fore.WHITE}PS Скальпинг:{Style.RESET_ALL} {Fore.RED}{block4['PS_scalp']:.8f}{Style.RESET_ALL}")
        print(f"{Fore.WHITE}Середина свечи:{Style.RESET_ALL} {Fore.MAGENTA}{block4['mid_point']:.8f}{Style.RESET_ALL}")
        
        adv = rb['advanced']
        print(f"\n{Fore.YELLOW}{'─'*80}")
        print(f"{Fore.YELLOW}ДОПОЛНИТЕЛЬНЫЙ АНАЛИЗ")
        print(f"{Fore.YELLOW}{'─'*80}{Style.RESET_ALL}")
        print(f"{Fore.WHITE}Средний диапазон (20 свечей):{Style.RESET_ALL} {Fore.CYAN}{adv['avg_range_20']:.8f}{Style.RESET_ALL}")
        print(f"{Fore.WHITE}Соотношение к среднему:{Style.RESET_ALL} {Fore.CYAN}{adv['range_ratio']:.2f}x{Style.RESET_ALL}")
        print(f"{Fore.WHITE}Волатильность:{Style.RESET_ALL} {Fore.MAGENTA}{adv['volatility']}{Style.RESET_ALL}")
        
        print(f"\n{Fore.YELLOW}{'='*80}")
        print(f"{Fore.YELLOW}ТОРГОВЫЕ СИГНАЛЫ (на основе RB Formula)")
        print(f"{Fore.YELLOW}{'='*80}{Style.RESET_ALL}")
        
        for i, signal in enumerate(results['signals'], 1):
            signal_type = signal['type']
            
            if 'LONG' in signal_type:
                color = Fore.GREEN
            elif 'SHORT' in signal_type:
                color = Fore.RED
            else:
                color = Fore.YELLOW
            
            print(f"\n{color}{'─'*80}")
            print(f"{color}СИГНАЛ #{i}: {signal_type}")
            print(f"{color}{'─'*80}{Style.RESET_ALL}")
            
            for key, value in signal.items():
                if key != 'type':
                    print(f"{Fore.WHITE}{key.replace('_', ' ').title()}:{Style.RESET_ALL} {value}")
        
        print(f"\n{Fore.CYAN}{'='*80}{Style.RESET_ALL}\n")
        
        if adv['range_ratio'] < 0.3:
            print(f"{Fore.YELLOW}{'⚠'*40}")
            print(f"{Fore.YELLOW}⚠ ПРЕДУПРЕЖДЕНИЕ: ОЧЕНЬ НИЗКАЯ ВОЛАТИЛЬНОСТЬ!")
            print(f"{Fore.YELLOW}{'⚠'*40}{Style.RESET_ALL}")
            print(f"{Fore.WHITE}Текущий диапазон {adv['range_ratio']:.2f}x от среднего{Style.RESET_ALL}")
            print(f"{Fore.YELLOW}Рекомендации:{Style.RESET_ALL}")
            print(f"  • Эта монета имеет крайне низкую волатильность")
            print(f"  • Профит будет минимальным (<1%)")
            print(f"  • Рассмотрите более волатильные активы:")
            print(f"    - BTC/USDT, ETH/USDT (основные)")
            print(f"    - SOL/USDT, BNB/USDT (альткоины)")
            print(f"  • Или используйте больший таймфрейм (1h, 4h, 1d)")
            print(f"{Fore.YELLOW}{'─'*80}{Style.RESET_ALL}\n")


# ============================================================
# Обратная совместимость: импорты из старых файлов
# ============================================================

# Если кто-то импортирует from unified_formula import RBFormula
# или from unified_formula import RogerFormula — всё будет работать
