#![allow(dead_code)]
use crate::exchange::Candle;

#[derive(Debug, Clone)]
pub struct Level {
    pub price: f64,
    pub level_type: LevelType,
    pub strength: usize,   // сколько раз цена отбивалась
    pub description: String,
}

#[derive(Debug, Clone, PartialEq)]
pub enum LevelType {
    Support,
    Resistance,
}

pub struct SRLevels {
    pub supports: Vec<Level>,
    pub resistances: Vec<Level>,
    pub nearest_support: Option<f64>,
    pub nearest_resistance: Option<f64>,
}

pub fn find_levels(candles: &[Candle], tolerance_pct: f64) -> SRLevels {
    let n = candles.len();
    if n < 10 {
        return SRLevels { supports: vec![], resistances: vec![], nearest_support: None, nearest_resistance: None };
    }

    let current_price = candles.last().unwrap().close;

    // Собираем все локальные минимумы и максимумы
    let mut raw_supports: Vec<f64>    = Vec::new();
    let mut raw_resistances: Vec<f64> = Vec::new();

    for i in 2..(n - 2) {
        let c = &candles[i];
        // Локальный минимум (поддержка)
        if c.low < candles[i-1].low && c.low < candles[i-2].low
        && c.low < candles[i+1].low && c.low < candles[i+2].low {
            raw_supports.push(c.low);
        }
        // Локальный максимум (сопротивление)
        if c.high > candles[i-1].high && c.high > candles[i-2].high
        && c.high > candles[i+1].high && c.high > candles[i+2].high {
            raw_resistances.push(c.high);
        }
    }

    // Кластеризуем близкие уровни
    let supports    = cluster_levels(&raw_supports, tolerance_pct, LevelType::Support, current_price);
    let resistances = cluster_levels(&raw_resistances, tolerance_pct, LevelType::Resistance, current_price);

    // Ближайший уровень поддержки (ниже цены)
    let nearest_support = supports.iter()
        .filter(|l| l.price < current_price)
        .max_by(|a, b| a.price.partial_cmp(&b.price).unwrap())
        .map(|l| l.price);

    // Ближайший уровень сопротивления (выше цены)
    let nearest_resistance = resistances.iter()
        .filter(|l| l.price > current_price)
        .min_by(|a, b| a.price.partial_cmp(&b.price).unwrap())
        .map(|l| l.price);

    SRLevels { supports, resistances, nearest_support, nearest_resistance }
}

fn cluster_levels(prices: &[f64], tolerance_pct: f64, level_type: LevelType, current_price: f64) -> Vec<Level> {
    if prices.is_empty() { return vec![]; }

    let mut sorted = prices.to_vec();
    sorted.sort_by(|a, b| a.partial_cmp(b).unwrap());

    let mut clusters: Vec<Vec<f64>> = Vec::new();

    for &price in &sorted {
        let mut added = false;
        for cluster in &mut clusters {
            let cluster_avg = cluster.iter().sum::<f64>() / cluster.len() as f64;
            if (price - cluster_avg).abs() / cluster_avg < tolerance_pct / 100.0 {
                cluster.push(price);
                added = true;
                break;
            }
        }
        if !added { clusters.push(vec![price]); }
    }

    // Превращаем кластеры в уровни, берём только сильные (2+ касания)
    let mut levels: Vec<Level> = clusters.iter()
        .filter(|c| c.len() >= 2)
        .map(|c| {
            let avg = c.iter().sum::<f64>() / c.len() as f64;
            let strength = c.len();
            let dist_pct = ((avg - current_price) / current_price * 100.0).abs();
            let type_str = match level_type { LevelType::Support => "Поддержка", LevelType::Resistance => "Сопротивление" };
            Level {
                price: avg,
                level_type: level_type.clone(),
                strength,
                description: format!("{} {:.6} (касаний: {}, расстояние: {:.2}%)", type_str, avg, strength, dist_pct),
            }
        })
        .collect();

    // Сортируем по близости к текущей цене
    levels.sort_by(|a, b| {
        let da = (a.price - current_price).abs();
        let db = (b.price - current_price).abs();
        da.partial_cmp(&db).unwrap()
    });

    // Берём топ-5 ближайших
    levels.truncate(5);
    levels
}

// Проверяет близко ли цена к уровню (для сигналов)
pub fn price_near_level(price: f64, level: f64, tolerance_pct: f64) -> bool {
    (price - level).abs() / level * 100.0 < tolerance_pct
}
