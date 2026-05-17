"""
Roger's Formula (RB Formula) - Авторская торговая система
Разработчик: Roger
Концепция: Проекция диапазона свечи для определения целей
"""

import statistics
from colorama import Fore, Style
from datetime import datetime


class RogerFormula:
    """Авторская формула Roger's для технического анализа"""
    
    def __init__(self):
        self.results = {}
    
    def calculate(self, conn, symbol, timeframe, limit=100):
        """
        Основной расчёт по формуле Roger's
        
        Args:
            conn: Подключение к PostgreSQL
            symbol: Торговая пара
            timeframe: Таймфрейм
            limit: Количество свечей для анализа
        """
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
            
            # Текущая свеча (последняя)
            current_candle = {
                'datetime': rows[0][1],
                'HP': highs[0],  # High Price
                'LP': lows[0],   # Low Price
                'open': opens[0],
                'close': closes[0],
                'volume': volumes[0]
            }
            
            # Применяем формулу Roger's
            rb_analysis = self._apply_roger_formula(
                current_candle, 
                highs, 
                lows, 
                closes
            )
            
            # Общая статистика
            statistics_data = self._calculate_statistics(highs, lows, closes, volumes)
            
            # Торговые сигналы
            signals = self._generate_trading_signals(
                current_candle,
                rb_analysis,
                statistics_data
            )
            
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
        """
        Применение авторской формулы Roger's
        
        Блок_1: Максимальный потенциал
        Блок_2: Price Long (цель для лонга)
        Блок_3: Price Short (цель для шорта)
        Блок_4: Скальпинг (половина диапазона)
        """
        HP = candle['HP']  # High Price текущей свечи
        LP = candle['LP']  # Low Price текущей свечи
        
        # БЛОК 1: Максимальный потенциал движения
        max_potential_up = HP + LP      # Потенциал вверх
        max_potential_down = LP - HP    # Потенциал вниз (отрицательный)
        
        # БЛОК 2: Average (диапазон) и Price Long
        A = HP - LP                     # Диапазон текущей свечи
        PL = HP + A                     # Цель для Long позиции
        
        # БЛОК 3: Price Short
        PS = LP - A                     # Цель для Short позиции
        
        # БЛОК 4: Скальпинг (половина диапазона)
        half_A = A / 2
        PL_scalp = HP + half_A          # Быстрая цель Long
        PS_scalp = LP - half_A          # Быстрая цель Short
        mid_point = LP + half_A         # Центр свечи
        
        # ДОПОЛНИТЕЛЬНО: Динамический расчёт на основе истории
        avg_range = statistics.mean([h - l for h, l in zip(highs[-20:], lows[-20:])])
        
        PL_dynamic = HP + avg_range     # Long цель с учётом средней волатильности
        PS_dynamic = LP - avg_range     # Short цель с учётом средней волатильности
        
        # Соотношение текущего диапазона к среднему
        range_ratio = A / avg_range if avg_range > 0 else 1
        
        return {
            'block_1_max_potential': {
                'up': max_potential_up,
                'down': max_potential_down,
                'description': 'Максимальный потенциал движения'
            },
            'block_2_long': {
                'A': A,                     # Диапазон
                'PL': PL,                   # Основная цель
                'PL_dynamic': PL_dynamic,   # С учётом истории
                'description': 'Цели для Long позиции'
            },
            'block_3_short': {
                'PS': PS,                   # Основная цель
                'PS_dynamic': PS_dynamic,   # С учётом истории
                'description': 'Цели для Short позиции'
            },
            'block_4_scalping': {
                'half_A': half_A,
                'PL_scalp': PL_scalp,       # Быстрый профит Long
                'PS_scalp': PS_scalp,       # Быстрый профит Short
                'mid_point': mid_point,     # Центр свечи
                'description': 'Уровни для скальпинга'
            },
            'advanced': {
                'avg_range_20': avg_range,
                'range_ratio': range_ratio,
                'volatility': 'Высокая' if range_ratio > 1.5 else 'Средняя' if range_ratio > 0.8 else 'Низкая'
            }
        }
    
    def _calculate_statistics(self, highs, lows, closes, volumes):
        """Базовая статистика для контекста"""
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
        """
        Генерация торговых сигналов на основе формулы Roger's
        """
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
        
        # Сигнал LONG
        if current_price <= (LP + half_A):  # Цена в нижней половине
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
            
            # Скальпинг LONG
            signals.append({
                'type': 'LONG (Скальпинг)',
                'strategy': 'Быстрый профит',
                'entry': f"около {LP:.8f}",
                'target': f"{PL_scalp:.8f}",
                'stop_loss': f"{LP - (half_A * 0.5):.8f}",
                'expected_profit': f"{half_A:.8f} USDT"
            })
        
        # Сигнал SHORT
        if current_price >= (HP - half_A):  # Цена в верхней половине
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
            
            # Скальпинг SHORT
            signals.append({
                'type': 'SHORT (Скальпинг)',
                'strategy': 'Быстрый профит',
                'entry': f"около {HP:.8f}",
                'target': f"{PS_scalp:.8f}",
                'stop_loss': f"{HP + (half_A * 0.5):.8f}",
                'expected_profit': f"{half_A:.8f} USDT"
            })
        
        # Нейтральная зона
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
        
        # Основная информация
        print(f"{Fore.YELLOW}{'─'*80}")
        print(f"{Fore.YELLOW}ОСНОВНАЯ ИНФОРМАЦИЯ")
        print(f"{Fore.YELLOW}{'─'*80}{Style.RESET_ALL}")
        print(f"{Fore.WHITE}Символ:{Style.RESET_ALL} {Fore.CYAN}{results['symbol']}{Style.RESET_ALL}")
        print(f"{Fore.WHITE}Таймфрейм:{Style.RESET_ALL} {Fore.CYAN}{results['timeframe']}{Style.RESET_ALL}")
        print(f"{Fore.WHITE}Время:{Style.RESET_ALL} {Fore.MAGENTA}{results['datetime']}{Style.RESET_ALL}")
        print(f"{Fore.WHITE}Свечей проанализировано:{Style.RESET_ALL} {Fore.CYAN}{results['candles_analyzed']}{Style.RESET_ALL}")
        
        # Текущая свеча
        candle = results['current_candle']
        print(f"\n{Fore.YELLOW}{'─'*80}")
        print(f"{Fore.YELLOW}ТЕКУЩАЯ СВЕЧА")
        print(f"{Fore.YELLOW}{'─'*80}{Style.RESET_ALL}")
        print(f"{Fore.WHITE}High Price (HP):{Style.RESET_ALL} {Fore.GREEN}{candle['HP']:.8f}{Style.RESET_ALL}")
        print(f"{Fore.WHITE}Low Price (LP):{Style.RESET_ALL} {Fore.RED}{candle['LP']:.8f}{Style.RESET_ALL}")
        print(f"{Fore.WHITE}Close:{Style.RESET_ALL} {Fore.CYAN}{candle['close']:.8f}{Style.RESET_ALL}")
        print(f"{Fore.WHITE}Volume:{Style.RESET_ALL} {Fore.MAGENTA}{candle['volume']:.2f}{Style.RESET_ALL}")
        
        # БЛОК 1: Максимальный потенциал
        rb = results['rb_formula']
        block1 = rb['block_1_max_potential']
        print(f"\n{Fore.YELLOW}{'─'*80}")
        print(f"{Fore.YELLOW}БЛОК 1: МАКСИМАЛЬНЫЙ ПОТЕНЦИАЛ ДВИЖЕНИЯ")
        print(f"{Fore.YELLOW}{'─'*80}{Style.RESET_ALL}")
        print(f"{Fore.WHITE}Потенциал ВВЕРХ (HP + LP):{Style.RESET_ALL} {Fore.GREEN}{block1['up']:.8f}{Style.RESET_ALL}")
        print(f"{Fore.WHITE}Потенциал ВНИЗ (LP - HP):{Style.RESET_ALL} {Fore.RED}{block1['down']:.8f}{Style.RESET_ALL}")
        
        # БЛОК 2: Long
        block2 = rb['block_2_long']
        print(f"\n{Fore.YELLOW}{'─'*80}")
        print(f"{Fore.YELLOW}БЛОК 2: ЦЕЛИ ДЛЯ LONG ПОЗИЦИИ")
        print(f"{Fore.YELLOW}{'─'*80}{Style.RESET_ALL}")
        print(f"{Fore.WHITE}Диапазон (A = HP - LP):{Style.RESET_ALL} {Fore.CYAN}{block2['A']:.8f}{Style.RESET_ALL}")
        print(f"{Fore.WHITE}Price Long (PL = HP + A):{Style.RESET_ALL} {Fore.GREEN}{block2['PL']:.8f}{Style.RESET_ALL}")
        print(f"{Fore.WHITE}PL Dynamic (учёт истории):{Style.RESET_ALL} {Fore.GREEN}{block2['PL_dynamic']:.8f}{Style.RESET_ALL}")
        
        # БЛОК 3: Short
        block3 = rb['block_3_short']
        print(f"\n{Fore.YELLOW}{'─'*80}")
        print(f"{Fore.YELLOW}БЛОК 3: ЦЕЛИ ДЛЯ SHORT ПОЗИЦИИ")
        print(f"{Fore.YELLOW}{'─'*80}{Style.RESET_ALL}")
        print(f"{Fore.WHITE}Price Short (PS = LP - A):{Style.RESET_ALL} {Fore.RED}{block3['PS']:.8f}{Style.RESET_ALL}")
        print(f"{Fore.WHITE}PS Dynamic (учёт истории):{Style.RESET_ALL} {Fore.RED}{block3['PS_dynamic']:.8f}{Style.RESET_ALL}")
        
        # БЛОК 4: Скальпинг
        block4 = rb['block_4_scalping']
        print(f"\n{Fore.YELLOW}{'─'*80}")
        print(f"{Fore.YELLOW}БЛОК 4: УРОВНИ ДЛЯ СКАЛЬПИНГА")
        print(f"{Fore.YELLOW}{'─'*80}{Style.RESET_ALL}")
        print(f"{Fore.WHITE}Половина диапазона (A/2):{Style.RESET_ALL} {Fore.CYAN}{block4['half_A']:.8f}{Style.RESET_ALL}")
        print(f"{Fore.WHITE}PL Скальпинг:{Style.RESET_ALL} {Fore.GREEN}{block4['PL_scalp']:.8f}{Style.RESET_ALL}")
        print(f"{Fore.WHITE}PS Скальпинг:{Style.RESET_ALL} {Fore.RED}{block4['PS_scalp']:.8f}{Style.RESET_ALL}")
        print(f"{Fore.WHITE}Середина свечи:{Style.RESET_ALL} {Fore.MAGENTA}{block4['mid_point']:.8f}{Style.RESET_ALL}")
        
        # Дополнительный анализ
        adv = rb['advanced']
        print(f"\n{Fore.YELLOW}{'─'*80}")
        print(f"{Fore.YELLOW}ДОПОЛНИТЕЛЬНЫЙ АНАЛИЗ")
        print(f"{Fore.YELLOW}{'─'*80}{Style.RESET_ALL}")
        print(f"{Fore.WHITE}Средний диапазон (20 свечей):{Style.RESET_ALL} {Fore.CYAN}{adv['avg_range_20']:.8f}{Style.RESET_ALL}")
        print(f"{Fore.WHITE}Соотношение к среднему:{Style.RESET_ALL} {Fore.CYAN}{adv['range_ratio']:.2f}x{Style.RESET_ALL}")
        print(f"{Fore.WHITE}Волатильность:{Style.RESET_ALL} {Fore.MAGENTA}{adv['volatility']}{Style.RESET_ALL}")
        
        # Торговые сигналы
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
        
        # Предупреждение о низкой волатильности
        adv = results['rb_formula']['advanced']
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


# Пример использования
if __name__ == "__main__":
    import psycopg2
    from colorama import init
    
    init(autoreset=True)
    
    try:
        conn = psycopg2.connect(
            dbname="trading_db",
            user="postgres",
            host="/var/run/postgresql",
            port="5432"
        )
        
        roger = RogerFormula()
        results = roger.calculate(conn, 'BTC/USDT', '1m', 100)
        
        if results:
            roger.display_results(results)
        
        conn.close()
        
    except Exception as e:
        print(f"{Fore.RED}✗ Ошибка: {e}{Style.RESET_ALL}")
