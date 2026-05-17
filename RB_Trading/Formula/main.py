#!/usr/bin/env python3
"""
Программа для трейдинга
Основной модуль управления
"""

import sys
from colorama import Fore, Back, Style, init
from cex_api import CEXConnector
from unified_formula import RBFormula
from unified_formula import RogerFormula
import psycopg2
from datetime import datetime

# Инициализация colorama
init(autoreset=True)

class TradingProgram:
    def __init__(self):
        self.cex = None
        self.rb_formula = RBFormula()
        self.roger_formula = RogerFormula()
        self.conn = None
        
    def connect_to_db(self):
        """Подключение к PostgreSQL"""
        try:
            self.conn = psycopg2.connect(
                dbname="trading_db",
                user="postgres",
                host="/var/run/postgresql",
                port="5432"
            )
            print(f"{Fore.GREEN}✓ Успешное подключение к базе данных{Style.RESET_ALL}")
            return True
        except Exception as e:
            print(f"{Fore.RED}✗ Ошибка подключения к БД: {e}{Style.RESET_ALL}")
            return False
    
    def print_header(self):
        """Печать заголовка программы"""
        print(f"\n{Fore.CYAN}{'='*70}")
        print(f"{Fore.CYAN}{' '*20}ПРОГРАММА ДЛЯ ТРЕЙДИНГА")
        print(f"{Fore.CYAN}{'='*70}{Style.RESET_ALL}\n")
    
    def print_menu(self):
        """Печать главного меню"""
        print(f"\n{Fore.YELLOW}{'─'*70}")
        print(f"{Fore.YELLOW}ГЛАВНОЕ МЕНЮ:")
        print(f"{Fore.YELLOW}{'─'*70}{Style.RESET_ALL}")
        print(f"{Fore.WHITE}1.{Style.RESET_ALL} Подключиться к CEX")
        print(f"{Fore.WHITE}2.{Style.RESET_ALL} Загрузить свечные данные")
        print(f"{Fore.WHITE}3.{Style.RESET_ALL} Показать сохраненные данные")
        print(f"{Fore.WHITE}4.{Style.RESET_ALL} Выполнить анализ (RB Formula)")
        print(f"{Fore.WHITE}5.{Style.RESET_ALL} Статистика по монете")
        print(f"{Fore.WHITE}6.{Style.RESET_ALL} 🔥 Roger's Formula (Авторский анализ)")
        print(f"{Fore.WHITE}0.{Style.RESET_ALL} Выход")
        print(f"{Fore.YELLOW}{'─'*70}{Style.RESET_ALL}")
    
    def connect_cex(self):
        """Подключение к CEX"""
        print(f"\n{Fore.CYAN}{'─'*70}")
        print(f"{Fore.CYAN}ПОДКЛЮЧЕНИЕ К CEX")
        print(f"{Fore.CYAN}{'─'*70}{Style.RESET_ALL}")
        
        print(f"{Fore.YELLOW}💡 Для публичных данных (история цен) ключи НЕ нужны!")
        print(f"{Fore.YELLOW}   Просто нажмите Enter два раза.{Style.RESET_ALL}\n")
        
        api_key = input(f"{Fore.WHITE}Введите API Key (или нажмите Enter для demo): {Style.RESET_ALL}")
        
        # Проверяем - если ввели API Key, то ОБЯЗАТЕЛЬНО нужен и Secret
        if api_key:
            api_secret = input(f"{Fore.WHITE}Введите API Secret (ОБЯЗАТЕЛЬНО если ввели Key): {Style.RESET_ALL}")
            if not api_secret:
                print(f"{Fore.RED}✗ Ошибка: Если вы ввели API Key, нужен и API Secret!{Style.RESET_ALL}")
                print(f"{Fore.YELLOW}   Используем demo режим (без ключей)...{Style.RESET_ALL}")
                api_key = None
                api_secret = None
        else:
            api_secret = None
        
        self.cex = CEXConnector(api_key if api_key else None, 
                                api_secret if api_secret else None)
        
        if self.cex.test_connection():
            if api_key:
                print(f"{Fore.GREEN}✓ Успешное подключение к CEX (с API ключами){Style.RESET_ALL}")
            else:
                print(f"{Fore.GREEN}✓ Успешное подключение к CEX (demo режим){Style.RESET_ALL}")
        else:
            print(f"{Fore.RED}✗ Ошибка подключения к CEX{Style.RESET_ALL}")
    
    def show_timeframe_info(self, timeframe):
        """Показать информацию о максимальном количестве свечей для таймфрейма"""
        
        timeframe_info = {
            '1m':  {'max': 1000, 'minutes': 1,    'name': '1 минута'},
            '3m':  {'max': 1000, 'minutes': 3,    'name': '3 минуты'},
            '5m':  {'max': 1000, 'minutes': 5,    'name': '5 минут'},
            '15m': {'max': 1000, 'minutes': 15,   'name': '15 минут'},
            '30m': {'max': 1000, 'minutes': 30,   'name': '30 минут'},
            '1h':  {'max': 1000, 'minutes': 60,   'name': '1 час'},
            '2h':  {'max': 1000, 'minutes': 120,  'name': '2 часа'},
            '4h':  {'max': 1000, 'minutes': 240,  'name': '4 часа'},
            '6h':  {'max': 1000, 'minutes': 360,  'name': '6 часов'},
            '8h':  {'max': 1000, 'minutes': 480,  'name': '8 часов'},
            '12h': {'max': 1000, 'minutes': 720,  'name': '12 часов'},
            '1d':  {'max': 1000, 'minutes': 1440, 'name': '1 день'},
            '3d':  {'max': 1000, 'minutes': 4320, 'name': '3 дня'},
            '1w':  {'max': 1000, 'minutes': 10080,'name': '1 неделя'},
        }
        
        info = timeframe_info.get(timeframe)
        if not info:
            print(f"{Fore.RED}✗ Неизвестный таймфрейм! Доступные: 1m, 3m, 5m, 15m, 30m, 1h, 2h, 4h, 6h, 8h, 12h, 1d, 3d, 1w{Style.RESET_ALL}")
            return None
        
        # Рассчитываем период который покрывают максимальные свечи
        total_minutes = info['max'] * info['minutes']
        total_hours   = total_minutes / 60
        total_days    = total_hours / 24
        total_months  = total_days / 30
        total_years   = total_days / 365
        
        # Форматируем период
        if total_days < 1:
            period = f"{total_hours:.1f} часов"
        elif total_days < 30:
            period = f"{total_days:.1f} дней"
        elif total_days < 365:
            period = f"{total_months:.1f} месяцев"
        else:
            period = f"{total_years:.1f} лет"
        
        # Рекомендуемые значения для разных целей
        rec_scalp  = min(100,  info['max'])
        rec_analis = min(500,  info['max'])
        rec_hist   = info['max']
        
        print(f"\n{Fore.CYAN}{'─'*70}")
        print(f"{Fore.CYAN}ИНФОРМАЦИЯ О ТАЙМФРЕЙМЕ: {timeframe.upper()}")
        print(f"{Fore.CYAN}{'─'*70}{Style.RESET_ALL}")
        print(f"  {Fore.WHITE}Таймфрейм:{Style.RESET_ALL}        {Fore.CYAN}{info['name']}{Style.RESET_ALL}")
        print(f"  {Fore.WHITE}Макс. свечей:{Style.RESET_ALL}     {Fore.GREEN}{info['max']} свечей{Style.RESET_ALL}")
        print(f"  {Fore.WHITE}Макс. период:{Style.RESET_ALL}     {Fore.MAGENTA}{period}{Style.RESET_ALL}")
        print(f"\n  {Fore.YELLOW}Рекомендуемое количество:{Style.RESET_ALL}")
        print(f"  {Fore.GREEN}⚡ Скальпинг:{Style.RESET_ALL}  {rec_scalp} свечей  "
              f"→ {Fore.MAGENTA}{rec_scalp * info['minutes'] / 60:.1f} ч.{Style.RESET_ALL}")
        print(f"  {Fore.CYAN}📊 Анализ:{Style.RESET_ALL}     {rec_analis} свечей  "
              f"→ {Fore.MAGENTA}{rec_analis * info['minutes'] / 60 / 24:.1f} дн.{Style.RESET_ALL}")
        print(f"  {Fore.MAGENTA}📈 История:{Style.RESET_ALL}    {rec_hist} свечей  "
              f"→ {Fore.MAGENTA}{period}{Style.RESET_ALL}")
        print(f"{Fore.CYAN}{'─'*70}{Style.RESET_ALL}\n")
        
        return info['max']

    def load_candle_data(self):
        """Загрузка свечных данных"""
        if not self.cex:
            print(f"{Fore.RED}✗ Сначала подключитесь к CEX{Style.RESET_ALL}")
            return
        
        print(f"\n{Fore.CYAN}{'─'*70}")
        print(f"{Fore.CYAN}ЗАГРУЗКА СВЕЧНЫХ ДАННЫХ")
        print(f"{Fore.CYAN}{'─'*70}{Style.RESET_ALL}")
        
        symbol    = input(f"{Fore.WHITE}Введите символ (например, BTC/USDT): {Style.RESET_ALL}").upper()
        timeframe = input(f"{Fore.WHITE}Введите таймфрейм (1m, 5m, 1h, 1d): {Style.RESET_ALL}")
        
        # Показываем информацию о таймфрейме
        max_candles = self.show_timeframe_info(timeframe)
        
        if max_candles:
            limit = input(f"{Fore.WHITE}Количество свечей (макс {Fore.GREEN}{max_candles}{Fore.WHITE}, Enter = 100): {Style.RESET_ALL}")
            limit = int(limit) if limit else 100
            if limit > max_candles:
                print(f"{Fore.YELLOW}⚠ Превышен максимум! Установлено {max_candles}{Style.RESET_ALL}")
                limit = max_candles
        else:
            limit = input(f"{Fore.WHITE}Количество свечей (по умолчанию 100): {Style.RESET_ALL}")
            limit = int(limit) if limit else 100
        
        print(f"\n{Fore.YELLOW}⏳ Загрузка данных...{Style.RESET_ALL}")
        
        candles = self.cex.fetch_ohlcv(symbol, timeframe, limit)
        
        if candles:
            print(f"{Fore.GREEN}✓ Загружено {len(candles)} свечей{Style.RESET_ALL}")
            save = input(f"{Fore.WHITE}Сохранить в базу данных? (y/n): {Style.RESET_ALL}")
            if save.lower() == 'y':
                self.save_to_db(symbol, timeframe, candles)
        else:
            print(f"{Fore.RED}✗ Не удалось загрузить данные{Style.RESET_ALL}")
    
    def save_to_db(self, symbol, timeframe, candles):
        """Сохранение данных в PostgreSQL"""
        if not self.conn:
            print(f"{Fore.RED}✗ Нет подключения к БД{Style.RESET_ALL}")
            return
        
        try:
            cursor = self.conn.cursor()
            saved_count = 0
            
            for candle in candles:
                timestamp, open_price, high, low, close_price, volume = candle
                # Используем UTC вместо локального времени
                dt = datetime.utcfromtimestamp(timestamp / 1000)
                
                cursor.execute("""
                    INSERT INTO candles (symbol, timeframe, timestamp, datetime, high, low, open, close, volume)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (symbol, timeframe, timestamp) DO UPDATE
                    SET high = EXCLUDED.high, low = EXCLUDED.low, 
                        open = EXCLUDED.open, close = EXCLUDED.close, volume = EXCLUDED.volume
                """, (symbol, timeframe, timestamp, dt, high, low, open_price, close_price, volume))
                saved_count += 1
            
            self.conn.commit()
            cursor.close()
            print(f"{Fore.GREEN}✓ Сохранено {saved_count} записей в БД{Style.RESET_ALL}")
            
        except Exception as e:
            print(f"{Fore.RED}✗ Ошибка сохранения: {e}{Style.RESET_ALL}")
            self.conn.rollback()
    
    def show_data(self):
        """Показать сохраненные данные"""
        if not self.conn:
            print(f"{Fore.RED}✗ Нет подключения к БД{Style.RESET_ALL}")
            return
        
        print(f"\n{Fore.CYAN}{'─'*70}")
        print(f"{Fore.CYAN}СОХРАНЕННЫЕ ДАННЫЕ")
        print(f"{Fore.CYAN}{'─'*70}{Style.RESET_ALL}")
        
        symbol = input(f"{Fore.WHITE}Введите символ (или Enter для всех): {Style.RESET_ALL}").upper()
        limit = input(f"{Fore.WHITE}Количество записей (по умолчанию 10): {Style.RESET_ALL}")
        limit = int(limit) if limit else 10
        
        try:
            cursor = self.conn.cursor()
            
            if symbol:
                cursor.execute("""
                    SELECT datetime, symbol, timeframe, high, low, (high - low) as range
                    FROM candles
                    WHERE symbol = %s
                    ORDER BY timestamp DESC
                    LIMIT %s
                """, (symbol, limit))
            else:
                cursor.execute("""
                    SELECT datetime, symbol, timeframe, high, low, (high - low) as range
                    FROM candles
                    ORDER BY timestamp DESC
                    LIMIT %s
                """, (limit,))
            
            rows = cursor.fetchall()
            
            if rows:
                print(f"\n{Fore.YELLOW}{'─'*100}")
                print(f"{Fore.YELLOW}{'Дата/Время':<20} {'Символ':<12} {'TF':<6} {'High':<15} {'Low':<15} {'Range':<15}")
                print(f"{Fore.YELLOW}{'─'*100}{Style.RESET_ALL}")
                
                for row in rows:
                    dt, sym, tf, high, low, rng = row
                    print(f"{Fore.WHITE}{str(dt):<20} {sym:<12} {tf:<6} "
                          f"{Fore.GREEN}{high:<15.8f} {Fore.RED}{low:<15.8f} "
                          f"{Fore.CYAN}{rng:<15.8f}{Style.RESET_ALL}")
                
                print(f"{Fore.YELLOW}{'─'*100}{Style.RESET_ALL}")
            else:
                print(f"{Fore.YELLOW}⚠ Нет данных{Style.RESET_ALL}")
            
            cursor.close()
            
        except Exception as e:
            print(f"{Fore.RED}✗ Ошибка: {e}{Style.RESET_ALL}")
    
    def run_analysis(self):
        """Запуск анализа RB Formula"""
        if not self.conn:
            print(f"{Fore.RED}✗ Нет подключения к БД{Style.RESET_ALL}")
            return
        
        print(f"\n{Fore.CYAN}{'─'*70}")
        print(f"{Fore.CYAN}АНАЛИЗ RB FORMULA")
        print(f"{Fore.CYAN}{'─'*70}{Style.RESET_ALL}")
        
        symbol = input(f"{Fore.WHITE}Введите символ: {Style.RESET_ALL}").upper()
        timeframe = input(f"{Fore.WHITE}Введите таймфрейм: {Style.RESET_ALL}")
        
        results = self.rb_formula.calculate(self.conn, symbol, timeframe)
        
        if results:
            self.rb_formula.display_results(results)
        else:
            print(f"{Fore.RED}✗ Нет данных для анализа{Style.RESET_ALL}")
    
    def show_statistics(self):
        """Показать статистику по монете"""
        if not self.conn:
            print(f"{Fore.RED}✗ Нет подключения к БД{Style.RESET_ALL}")
            return
        
        print(f"\n{Fore.CYAN}{'─'*70}")
        print(f"{Fore.CYAN}СТАТИСТИКА")
        print(f"{Fore.CYAN}{'─'*70}{Style.RESET_ALL}")
        
        symbol = input(f"{Fore.WHITE}Введите символ: {Style.RESET_ALL}").upper()
        
        try:
            cursor = self.conn.cursor()
            
            cursor.execute("""
                SELECT 
                    COUNT(*) as count,
                    MAX(high) as max_high,
                    MIN(low) as min_low,
                    AVG(high - low) as avg_range,
                    MIN(datetime) as first_date,
                    MAX(datetime) as last_date
                FROM candles
                WHERE symbol = %s
            """, (symbol,))
            
            row = cursor.fetchone()
            
            if row and row[0] > 0:
                count, max_high, min_low, avg_range, first_date, last_date = row
                
                # Конвертируем Decimal в float
                max_high = float(max_high) if max_high else 0
                min_low = float(min_low) if min_low else 0
                avg_range = float(avg_range) if avg_range else 0
                
                print(f"\n{Fore.YELLOW}{'─'*70}")
                print(f"{Fore.YELLOW}Статистика для {Fore.WHITE}{symbol}")
                print(f"{Fore.YELLOW}{'─'*70}{Style.RESET_ALL}")
                print(f"{Fore.WHITE}Всего свечей:{Style.RESET_ALL} {Fore.CYAN}{count}{Style.RESET_ALL}")
                print(f"{Fore.WHITE}Максимальный High:{Style.RESET_ALL} {Fore.GREEN}{max_high:.8f}{Style.RESET_ALL}")
                print(f"{Fore.WHITE}Минимальный Low:{Style.RESET_ALL} {Fore.RED}{min_low:.8f}{Style.RESET_ALL}")
                print(f"{Fore.WHITE}Средний Range:{Style.RESET_ALL} {Fore.CYAN}{avg_range:.8f}{Style.RESET_ALL}")
                print(f"{Fore.WHITE}Первая дата:{Style.RESET_ALL} {Fore.MAGENTA}{first_date}{Style.RESET_ALL}")
                print(f"{Fore.WHITE}Последняя дата:{Style.RESET_ALL} {Fore.MAGENTA}{last_date}{Style.RESET_ALL}")
                print(f"{Fore.YELLOW}{'─'*70}{Style.RESET_ALL}")
            else:
                print(f"{Fore.YELLOW}⚠ Нет данных для символа {symbol}{Style.RESET_ALL}")
            
            cursor.close()
            
        except Exception as e:
            print(f"{Fore.RED}✗ Ошибка: {e}{Style.RESET_ALL}")
    
    def run_roger_formula(self):
        """Запуск авторской формулы Roger's"""
        if not self.conn:
            print(f"{Fore.RED}✗ Нет подключения к БД{Style.RESET_ALL}")
            return
        
        print(f"\n{Fore.CYAN}{'─'*70}")
        print(f"{Fore.CYAN}🔥 ROGER'S FORMULA - АВТОРСКИЙ АНАЛИЗ")
        print(f"{Fore.CYAN}{'─'*70}{Style.RESET_ALL}")
        
        symbol = input(f"{Fore.WHITE}Введите символ: {Style.RESET_ALL}").upper()
        timeframe = input(f"{Fore.WHITE}Введите таймфрейм: {Style.RESET_ALL}")
        
        results = self.roger_formula.calculate(self.conn, symbol, timeframe)
        
        if results:
            self.roger_formula.display_results(results)
        else:
            print(f"{Fore.RED}✗ Нет данных для анализа{Style.RESET_ALL}")
    
    def run(self):
        """Главный цикл программы"""
        self.print_header()
        
        if not self.connect_to_db():
            print(f"{Fore.RED}Программа завершена из-за ошибки подключения к БД{Style.RESET_ALL}")
            return
        
        while True:
            self.print_menu()
            choice = input(f"\n{Fore.CYAN}Выберите опцию: {Style.RESET_ALL}")
            
            if choice == '1':
                self.connect_cex()
            elif choice == '2':
                self.load_candle_data()
            elif choice == '3':
                self.show_data()
            elif choice == '4':
                self.run_analysis()
            elif choice == '5':
                self.show_statistics()
            elif choice == '6':
                self.run_roger_formula()
            elif choice == '0':
                print(f"\n{Fore.CYAN}До свидания!{Style.RESET_ALL}\n")
                break
            else:
                print(f"{Fore.RED}✗ Неверная опция{Style.RESET_ALL}")
        
        if self.conn:
            self.conn.close()


if __name__ == "__main__":
    try:
        program = TradingProgram()
        program.run()
    except KeyboardInterrupt:
        print(f"\n\n{Fore.YELLOW}⚠ Программа прервана пользователем{Style.RESET_ALL}\n")
        sys.exit(0)
    except Exception as e:
        print(f"\n{Fore.RED}✗ Критическая ошибка: {e}{Style.RESET_ALL}\n")
        sys.exit(1)
