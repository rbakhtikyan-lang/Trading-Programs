"""
Модуль конфигурации — загружает настройки из .env файла
"""

import os
from dotenv import load_dotenv

# Загружаем .env из папки Formula
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(BASE_DIR, '.env'))


def get_config():
    """Возвращает словарь с настройками"""
    symbols_str = os.getenv('SYMBOLS', 'BTC/USDT,ETH/USDT,SOL/USDT,BNB/USDT,AVAX/USDT')
    
    return {
        'symbols': [s.strip() for s in symbols_str.split(',') if s.strip()],
        'timeframe': os.getenv('TIMEFRAME', '5m'),
        'capital': float(os.getenv('CAPITAL', '100')),
        'leverage': int(os.getenv('LEVERAGE', '3')),
        'daily_target': float(os.getenv('DAILY_TARGET', '100')),
        
        # База данных
        'db_name': os.getenv('DB_NAME', 'trading_db'),
        'db_user': os.getenv('DB_USER', 'postgres'),
        'db_host': os.getenv('DB_HOST', '/var/run/postgresql'),
        'db_port': os.getenv('DB_PORT', '5432'),
        
        # Telegram
        'telegram_token': os.getenv('TELEGRAM_BOT_TOKEN') or None,
        'telegram_chat': os.getenv('TELEGRAM_CHAT_ID') or None,
    }
