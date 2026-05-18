use crate::exchange::Candle;

#[derive(Debug, Clone)]
pub struct PatternResult {
    pub name: String,
    pub direction: PatternDirection,
    pub description: String,
}

#[derive(Debug, Clone, PartialEq)]
pub enum PatternDirection {
    Bullish,
    Bearish,
    Neutral,
}

pub fn detect_patterns(candles: &[Candle]) -> Vec<PatternResult> {
    let mut results = Vec::new();
    let n = candles.len();
    if n < 3 { return results; }

    let c  = &candles[n - 1]; // последняя свеча
    let p1 = &candles[n - 2]; // предпоследняя
    let p2 = &candles[n - 3]; // 3-я с конца

    // Размеры тел и теней
    let body    = |c: &Candle| (c.close - c.open).abs();
    let upper_shadow = |c: &Candle| c.high - c.open.max(c.close);
    let lower_shadow = |c: &Candle| c.open.min(c.close) - c.low;
    let is_bull = |c: &Candle| c.close > c.open;
    let is_bear = |c: &Candle| c.close < c.open;
    let range   = |c: &Candle| c.high - c.low;

    // ── DOJI ─────────────────────────────────
    {
        let b = body(c);
        let r = range(c);
        if r > 0.0 && b / r < 0.1 {
            results.push(PatternResult {
                name: "Doji".to_string(),
                direction: PatternDirection::Neutral,
                description: "Нерешительность рынка — возможный разворот".to_string(),
            });
        }
    }

    // ── HAMMER (Молот) ─────────────────────────
    {
        let b = body(c);
        let ls = lower_shadow(c);
        let us = upper_shadow(c);
        if b > 0.0 && ls >= 2.0 * b && us <= 0.3 * b {
            results.push(PatternResult {
                name: "Hammer 🔨".to_string(),
                direction: PatternDirection::Bullish,
                description: "Бычий молот — сигнал разворота вверх".to_string(),
            });
        }
    }

    // ── SHOOTING STAR (Падающая звезда) ──────
    {
        let b = body(c);
        let us = upper_shadow(c);
        let ls = lower_shadow(c);
        if b > 0.0 && us >= 2.0 * b && ls <= 0.3 * b {
            results.push(PatternResult {
                name: "Shooting Star ⭐".to_string(),
                direction: PatternDirection::Bearish,
                description: "Падающая звезда — сигнал разворота вниз".to_string(),
            });
        }
    }

    // ── HANGING MAN (Висельник) ───────────────
    {
        let b = body(c);
        let ls = lower_shadow(c);
        let us = upper_shadow(c);
        // Похож на молот но на вершине тренда
        if is_bear(p1) && is_bear(p2) && b > 0.0 && ls >= 2.0 * b && us <= 0.3 * b {
            results.push(PatternResult {
                name: "Hanging Man 🪢".to_string(),
                direction: PatternDirection::Bearish,
                description: "Висельник — медвежий сигнал на вершине".to_string(),
            });
        }
    }

    // ── BULLISH ENGULFING (Бычье поглощение) ──
    {
        if is_bear(p1) && is_bull(c)
            && c.open  <= p1.close
            && c.close >= p1.open
            && body(c) > body(p1)
        {
            results.push(PatternResult {
                name: "Bullish Engulfing 🟢".to_string(),
                direction: PatternDirection::Bullish,
                description: "Бычье поглощение — сильный сигнал роста".to_string(),
            });
        }
    }

    // ── BEARISH ENGULFING (Медвежье поглощение) ─
    {
        if is_bull(p1) && is_bear(c)
            && c.open  >= p1.close
            && c.close <= p1.open
            && body(c) > body(p1)
        {
            results.push(PatternResult {
                name: "Bearish Engulfing 🔴".to_string(),
                direction: PatternDirection::Bearish,
                description: "Медвежье поглощение — сильный сигнал падения".to_string(),
            });
        }
    }

    // ── MORNING STAR (Утренняя звезда) ────────
    {
        if is_bear(p2)
            && body(p1) < body(p2) * 0.3   // маленькая средняя свеча
            && is_bull(c)
            && c.close > (p2.open + p2.close) / 2.0
        {
            results.push(PatternResult {
                name: "Morning Star 🌅".to_string(),
                direction: PatternDirection::Bullish,
                description: "Утренняя звезда — сильный бычий разворот".to_string(),
            });
        }
    }

    // ── EVENING STAR (Вечерняя звезда) ────────
    {
        if is_bull(p2)
            && body(p1) < body(p2) * 0.3
            && is_bear(c)
            && c.close < (p2.open + p2.close) / 2.0
        {
            results.push(PatternResult {
                name: "Evening Star 🌆".to_string(),
                direction: PatternDirection::Bearish,
                description: "Вечерняя звезда — сильный медвежий разворот".to_string(),
            });
        }
    }

    // ── THREE WHITE SOLDIERS (Три белых солдата) ─
    {
        if is_bull(p2) && is_bull(p1) && is_bull(c)
            && p1.open > p2.open && p1.close > p2.close
            && c.open  > p1.open && c.close  > p1.close
            && upper_shadow(c)  < body(c) * 0.3
            && upper_shadow(p1) < body(p1) * 0.3
        {
            results.push(PatternResult {
                name: "Three White Soldiers 🪖🪖🪖".to_string(),
                direction: PatternDirection::Bullish,
                description: "Три белых солдата — сильный восходящий тренд".to_string(),
            });
        }
    }

    // ── THREE BLACK CROWS (Три чёрные вороны) ──
    {
        if is_bear(p2) && is_bear(p1) && is_bear(c)
            && p1.open < p2.open && p1.close < p2.close
            && c.open  < p1.open && c.close  < p1.close
            && lower_shadow(c)  < body(c) * 0.3
            && lower_shadow(p1) < body(p1) * 0.3
        {
            results.push(PatternResult {
                name: "Three Black Crows 🐦🐦🐦".to_string(),
                direction: PatternDirection::Bearish,
                description: "Три чёрные вороны — сильный нисходящий тренд".to_string(),
            });
        }
    }

    results
}
