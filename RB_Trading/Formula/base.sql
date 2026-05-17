-- =====================================================
-- SQL скрипт для создания базы данных Trading Program
-- =====================================================

-- Создание базы данных
-- Выполнить вручную из psql: CREATE DATABASE trading_db;

-- Подключение к БД
\c trading_db;

-- =====================================================
-- Таблица для хранения свечных данных
-- =====================================================

DROP TABLE IF EXISTS candles CASCADE;

CREATE TABLE candles (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(20) NOT NULL,              -- Торговая пара (например, BTC/USDT)
    timeframe VARCHAR(10) NOT NULL,           -- Таймфрейм (1m, 5m, 1h, 1d и т.д.)
    timestamp BIGINT NOT NULL,                -- Unix timestamp в миллисекундах
    datetime TIMESTAMP NOT NULL,              -- Дата и время
    high DECIMAL(20, 8) NOT NULL,             -- Максимальная цена
    low DECIMAL(20, 8) NOT NULL,              -- Минимальная цена
    open DECIMAL(20, 8) NOT NULL,             -- Цена открытия
    close DECIMAL(20, 8) NOT NULL,            -- Цена закрытия
    volume DECIMAL(20, 8) NOT NULL,           -- Объем торгов
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Уникальный индекс для предотвращения дубликатов
    CONSTRAINT unique_candle UNIQUE (symbol, timeframe, timestamp)
);

-- =====================================================
-- Индексы для улучшения производительности
-- =====================================================

-- Индекс для быстрого поиска по символу и времени
CREATE INDEX idx_candles_symbol_timestamp ON candles(symbol, timestamp DESC);

-- Индекс для поиска по символу и таймфрейму
CREATE INDEX idx_candles_symbol_timeframe ON candles(symbol, timeframe);

-- Индекс для поиска по дате
CREATE INDEX idx_candles_datetime ON candles(datetime);

-- Индекс для поиска по символу, таймфрейму и времени (составной)
CREATE INDEX idx_candles_composite ON candles(symbol, timeframe, timestamp DESC);

-- =====================================================
-- Таблица для хранения результатов анализа
-- =====================================================

DROP TABLE IF EXISTS analysis_results CASCADE;

CREATE TABLE analysis_results (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(20) NOT NULL,
    timeframe VARCHAR(10) NOT NULL,
    analysis_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Результаты анализа High/Low
    max_high DECIMAL(20, 8),
    min_low DECIMAL(20, 8),
    avg_high DECIMAL(20, 8),
    avg_low DECIMAL(20, 8),
    total_range DECIMAL(20, 8),
    
    -- Результаты анализа диапазонов
    avg_range DECIMAL(20, 8),
    max_range DECIMAL(20, 8),
    min_range DECIMAL(20, 8),
    median_range DECIMAL(20, 8),
    
    -- Волатильность
    atr DECIMAL(20, 8),
    volatility_level VARCHAR(50),
    
    -- Движение цены
    bullish_percentage DECIMAL(5, 2),
    bearish_percentage DECIMAL(5, 2),
    
    -- Объем
    total_volume DECIMAL(20, 8),
    avg_volume DECIMAL(20, 8),
    
    candles_analyzed INTEGER,
    
    CONSTRAINT unique_analysis UNIQUE (symbol, timeframe, analysis_date)
);

-- Индекс для поиска результатов анализа
CREATE INDEX idx_analysis_symbol_date ON analysis_results(symbol, analysis_date DESC);

-- =====================================================
-- Таблица для хранения уровней поддержки/сопротивления
-- =====================================================

DROP TABLE IF EXISTS support_resistance_levels CASCADE;

CREATE TABLE support_resistance_levels (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(20) NOT NULL,
    timeframe VARCHAR(10) NOT NULL,
    level_type VARCHAR(20) NOT NULL,          -- 'support' или 'resistance'
    price_level DECIMAL(20, 8) NOT NULL,
    strength INTEGER DEFAULT 1,               -- Сила уровня (количество касаний)
    identified_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE,
    
    CONSTRAINT check_level_type CHECK (level_type IN ('support', 'resistance'))
);

-- Индекс для поиска уровней
CREATE INDEX idx_sr_symbol_active ON support_resistance_levels(symbol, is_active);
CREATE INDEX idx_sr_symbol_type ON support_resistance_levels(symbol, level_type);

-- =====================================================
-- Таблица для логирования событий
-- =====================================================

DROP TABLE IF EXISTS event_log CASCADE;

CREATE TABLE event_log (
    id SERIAL PRIMARY KEY,
    event_type VARCHAR(50) NOT NULL,          -- Тип события
    event_description TEXT,
    symbol VARCHAR(20),
    severity VARCHAR(20) DEFAULT 'INFO',      -- INFO, WARNING, ERROR
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT check_severity CHECK (severity IN ('INFO', 'WARNING', 'ERROR', 'CRITICAL'))
);

-- Индекс для поиска логов
CREATE INDEX idx_log_date ON event_log(created_at DESC);
CREATE INDEX idx_log_severity ON event_log(severity);

-- =====================================================
-- Представления (Views) для удобного доступа к данным
-- =====================================================

-- Представление последних свечей по каждому символу
CREATE OR REPLACE VIEW latest_candles AS
SELECT DISTINCT ON (symbol, timeframe)
    symbol,
    timeframe,
    datetime,
    high,
    low,
    open,
    close,
    volume,
    (high - low) as range
FROM candles
ORDER BY symbol, timeframe, timestamp DESC;

-- Представление статистики по символам
CREATE OR REPLACE VIEW symbol_statistics AS
SELECT 
    symbol,
    timeframe,
    COUNT(*) as total_candles,
    MAX(high) as max_high,
    MIN(low) as min_low,
    AVG(high - low) as avg_range,
    MIN(datetime) as first_date,
    MAX(datetime) as last_date
FROM candles
GROUP BY symbol, timeframe;

-- =====================================================
-- Функции для работы с данными
-- =====================================================

-- Функция для очистки старых данных
CREATE OR REPLACE FUNCTION cleanup_old_candles(days_to_keep INTEGER DEFAULT 365)
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    DELETE FROM candles
    WHERE datetime < CURRENT_TIMESTAMP - (days_to_keep || ' days')::INTERVAL;
    
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    
    INSERT INTO event_log (event_type, event_description, severity)
    VALUES ('CLEANUP', 'Удалено ' || deleted_count || ' старых записей', 'INFO');
    
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

-- Функция для подсчета свечей по символу
CREATE OR REPLACE FUNCTION count_candles(p_symbol VARCHAR, p_timeframe VARCHAR DEFAULT NULL)
RETURNS INTEGER AS $$
DECLARE
    candle_count INTEGER;
BEGIN
    IF p_timeframe IS NULL THEN
        SELECT COUNT(*) INTO candle_count FROM candles WHERE symbol = p_symbol;
    ELSE
        SELECT COUNT(*) INTO candle_count FROM candles 
        WHERE symbol = p_symbol AND timeframe = p_timeframe;
    END IF;
    
    RETURN candle_count;
END;
$$ LANGUAGE plpgsql;

-- =====================================================
-- Триггеры
-- =====================================================

-- Функция триггера для логирования вставки новых свечей
CREATE OR REPLACE FUNCTION log_candle_insert()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO event_log (event_type, event_description, symbol, severity)
    VALUES ('CANDLE_INSERT', 
            'Добавлена новая свеча для ' || NEW.symbol || ' ' || NEW.timeframe,
            NEW.symbol,
            'INFO');
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Создание триггера (опционально, можно закомментировать если не нужен)
-- CREATE TRIGGER trigger_log_candle_insert
--     AFTER INSERT ON candles
--     FOR EACH ROW
--     EXECUTE FUNCTION log_candle_insert();

-- =====================================================
-- Предустановленные данные (опционально)
-- =====================================================

-- Добавление записи в лог о создании БД
INSERT INTO event_log (event_type, event_description, severity)
VALUES ('DB_INIT', 'База данных успешно инициализирована', 'INFO');

-- =====================================================
-- Комментарии к таблицам
-- =====================================================

COMMENT ON TABLE candles IS 'Таблица для хранения свечных данных (OHLCV)';
COMMENT ON TABLE analysis_results IS 'Таблица для хранения результатов анализа';
COMMENT ON TABLE support_resistance_levels IS 'Таблица для хранения уровней поддержки и сопротивления';
COMMENT ON TABLE event_log IS 'Таблица для логирования событий системы';

-- =====================================================
-- Права доступа (настроить при необходимости)
-- =====================================================

-- GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO trading_user;
-- GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO trading_user;

-- =====================================================
-- Информация о схеме
-- =====================================================

SELECT 'База данных успешно создана!' as status;
SELECT 'Таблицы созданы:' as info;
SELECT table_name FROM information_schema.tables 
WHERE table_schema = 'public' AND table_type = 'BASE TABLE';
