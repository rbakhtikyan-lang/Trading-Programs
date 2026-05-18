#![allow(dead_code)]
use crate::indicators::calc_rsi;

#[derive(Debug, Clone)]
pub enum DivergenceType {
    BullishRegular,   // Цена ↓ RSI ↑ — разворот вверх
    BearishRegular,   // Цена ↑ RSI ↓ — разворот вниз
    BullishHidden,    // Цена ↑ RSI ↓ при апренде — продолжение роста
    BearishHidden,    // Цена ↓ RSI ↑ при даунтренде — продолжение падения
}

#[derive(Debug, Clone)]
pub struct Divergence {
    pub div_type: DivergenceType,
    pub description: String,
    pub strength: f64, // 0.0 - 1.0
}

pub fn detect_divergence(closes: &[f64], lookback: usize) -> Vec<Divergence> {
    let mut results = Vec::new();
    let n = closes.len();
    if n < lookback + 5 { return results; }

    let rsi = calc_rsi(closes, 14);

    // Берём последние lookback свечей для анализа
    let start = n.saturating_sub(lookback);
    let price_slice = &closes[start..];
    let rsi_slice: Vec<f64> = rsi[start..].iter().copied().filter(|v| !v.is_nan()).collect();
    if rsi_slice.len() < 4 { return results; }

    // Находим локальные минимумы и максимумы цены
    let price_lows  = find_local_extrema(price_slice, false);
    let price_highs = find_local_extrema(price_slice, true);
    let rsi_lows    = find_local_extrema(&rsi_slice, false);
    let rsi_highs   = find_local_extrema(&rsi_slice, true);

    // ── Бычья дивергенция (Regular) ──────────────
    // Цена делает более низкий минимум, RSI — более высокий минимум
    if price_lows.len() >= 2 && rsi_lows.len() >= 2 {
        let (pi1, pv1) = price_lows[price_lows.len() - 2];
        let (pi2, pv2) = price_lows[price_lows.len() - 1];
        let (ri1, rv1) = rsi_lows[rsi_lows.len() - 2];
        let (ri2, rv2) = rsi_lows[rsi_lows.len() - 1];

        if pi2 > pi1 && ri2 > ri1 && pv2 < pv1 && rv2 > rv1 {
            let strength = ((rv2 - rv1) / rv1).abs().min(1.0);
            results.push(Divergence {
                div_type: DivergenceType::BullishRegular,
                description: format!(
                    "Бычья дивергенция RSI: цена ↓ ({:.5}→{:.5}), RSI ↑ ({:.1}→{:.1}) — сигнал разворота ВВЕРХ",
                    pv1, pv2, rv1, rv2
                ),
                strength,
            });
        }
    }

    // ── Медвежья дивергенция (Regular) ───────────
    // Цена делает более высокий максимум, RSI — более низкий максимум
    if price_highs.len() >= 2 && rsi_highs.len() >= 2 {
        let (pi1, pv1) = price_highs[price_highs.len() - 2];
        let (pi2, pv2) = price_highs[price_highs.len() - 1];
        let (ri1, rv1) = rsi_highs[rsi_highs.len() - 2];
        let (ri2, rv2) = rsi_highs[rsi_highs.len() - 1];

        if pi2 > pi1 && ri2 > ri1 && pv2 > pv1 && rv2 < rv1 {
            let strength = ((rv1 - rv2) / rv1).abs().min(1.0);
            results.push(Divergence {
                div_type: DivergenceType::BearishRegular,
                description: format!(
                    "Медвежья дивергенция RSI: цена ↑ ({:.5}→{:.5}), RSI ↓ ({:.1}→{:.1}) — сигнал разворота ВНИЗ",
                    pv1, pv2, rv1, rv2
                ),
                strength,
            });
        }
    }

    // ── Скрытая бычья дивергенция ─────────────────
    // Цена ↑ минимумы, RSI ↓ минимумы — продолжение тренда вверх
    if price_lows.len() >= 2 && rsi_lows.len() >= 2 {
        let (pi1, pv1) = price_lows[price_lows.len() - 2];
        let (pi2, pv2) = price_lows[price_lows.len() - 1];
        let (ri1, rv1) = rsi_lows[rsi_lows.len() - 2];
        let (ri2, rv2) = rsi_lows[rsi_lows.len() - 1];

        if pi2 > pi1 && ri2 > ri1 && pv2 > pv1 && rv2 < rv1 && rv2 > 40.0 {
            results.push(Divergence {
                div_type: DivergenceType::BullishHidden,
                description: format!(
                    "Скрытая бычья дивергенция: цена ↑ ({:.5}→{:.5}), RSI ↓ ({:.1}→{:.1}) — продолжение роста",
                    pv1, pv2, rv1, rv2
                ),
                strength: 0.6,
            });
        }
    }

    // ── Скрытая медвежья дивергенция ─────────────
    // Цена ↓ максимумы, RSI ↑ максимумы — продолжение тренда вниз
    if price_highs.len() >= 2 && rsi_highs.len() >= 2 {
        let (pi1, pv1) = price_highs[price_highs.len() - 2];
        let (pi2, pv2) = price_highs[price_highs.len() - 1];
        let (ri1, rv1) = rsi_highs[rsi_highs.len() - 2];
        let (ri2, rv2) = rsi_highs[rsi_highs.len() - 1];

        if pi2 > pi1 && ri2 > ri1 && pv2 < pv1 && rv2 > rv1 && rv2 < 60.0 {
            results.push(Divergence {
                div_type: DivergenceType::BearishHidden,
                description: format!(
                    "Скрытая медвежья дивергенция: цена ↓ ({:.5}→{:.5}), RSI ↑ ({:.1}→{:.1}) — продолжение падения",
                    pv1, pv2, rv1, rv2
                ),
                strength: 0.6,
            });
        }
    }

    results
}

// Находит локальные экстремумы (минимумы или максимумы)
fn find_local_extrema(data: &[f64], find_max: bool) -> Vec<(usize, f64)> {
    let mut extrema = Vec::new();
    let n = data.len();
    if n < 3 { return extrema; }

    for i in 1..(n - 1) {
        if data[i].is_nan() { continue; }
        let is_extremum = if find_max {
            data[i] > data[i - 1] && data[i] > data[i + 1]
        } else {
            data[i] < data[i - 1] && data[i] < data[i + 1]
        };
        if is_extremum { extrema.push((i, data[i])); }
    }
    extrema
}
