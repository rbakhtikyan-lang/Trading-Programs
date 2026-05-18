use crate::indicators::Indicators;
use crate::patterns::{PatternResult, PatternDirection};
use crate::divergence::{Divergence, DivergenceType};
use crate::levels::SRLevels;
use crate::Config;

#[derive(Debug)]
pub enum Direction { Long, Short, Neutral }

pub enum SignalStrength { Weak, Medium, Strong }
impl SignalStrength {
    pub fn label(&self) -> &str {
        match self { SignalStrength::Weak=>"СЛАБЫЙ ⚪", SignalStrength::Medium=>"СРЕДНИЙ 🟡", SignalStrength::Strong=>"СИЛЬНЫЙ 🟢" }
    }
}

pub struct SignalResult {
    pub direction: Direction,
    pub confidence: f64,
    pub strength: SignalStrength,
    pub long_signals: Vec<String>,
    pub short_signals: Vec<String>,
    pub stop_loss: f64,
    pub take_profit: f64,
}

pub fn generate_signal(ind: &Indicators, patterns: &[PatternResult], config: &Config, last_price: f64, last_volume: f64) -> SignalResult {
    generate_signal_full(ind, patterns, &[], &SRLevels { supports: vec![], resistances: vec![], nearest_support: None, nearest_resistance: None }, config, last_price, last_volume)
}

pub fn generate_signal_full(
    ind: &Indicators,
    patterns: &[PatternResult],
    divergences: &[Divergence],
    sr: &SRLevels,
    config: &Config,
    last_price: f64,
    last_volume: f64,
) -> SignalResult {
    let mut long_signals:  Vec<(String, f64)> = Vec::new();
    let mut short_signals: Vec<(String, f64)> = Vec::new();

    let last = |v: &Vec<f64>| v.iter().rev().find(|x| !x.is_nan()).copied().unwrap_or(f64::NAN);
    let prev = |v: &Vec<f64>| v.iter().rev().filter(|x| !x.is_nan()).nth(1).copied().unwrap_or(f64::NAN);

    // ── RSI ──────────────────────────────────────
    let rsi = last(&ind.rsi);
    if !rsi.is_nan() {
        if rsi < config.rsi_oversold      { long_signals.push((format!("RSI={:.1} перепродан (<{})", rsi, config.rsi_oversold), 1.5)); }
        else if rsi > config.rsi_overbought { short_signals.push((format!("RSI={:.1} перекуплен (>{})", rsi, config.rsi_overbought), 1.5)); }
    }

    // ── Stochastic RSI ────────────────────────────
    let sk = last(&ind.stoch_rsi_k); let sd = last(&ind.stoch_rsi_d);
    let sk_p = prev(&ind.stoch_rsi_k); let sd_p = prev(&ind.stoch_rsi_d);
    if !sk.is_nan() && !sd.is_nan() {
        if sk < 20.0 && sd < 20.0 { long_signals.push(("Stoch RSI перепродан (<20)".to_string(), 1.2)); }
        else if sk > 80.0 && sd > 80.0 { short_signals.push(("Stoch RSI перекуплен (>80)".to_string(), 1.2)); }
        if sk_p <= sd_p && sk > sd && sk < 50.0 { long_signals.push(("Stoch RSI: K пересёк D вверх".to_string(), 1.2)); }
        else if sk_p >= sd_p && sk < sd && sk > 50.0 { short_signals.push(("Stoch RSI: K пересёк D вниз".to_string(), 1.2)); }
    }

    // ── MA ────────────────────────────────────────
    let maf = last(&ind.ma_fast); let mas = last(&ind.ma_slow);
    let maf_p = prev(&ind.ma_fast); let mas_p = prev(&ind.ma_slow);
    if !maf.is_nan() && !mas.is_nan() {
        if maf_p <= mas_p && maf > mas { long_signals.push((format!("MA{} пересёк MA{} вверх ↑", config.ma_fast, config.ma_slow), 1.5)); }
        else if maf_p >= mas_p && maf < mas { short_signals.push((format!("MA{} пересёк MA{} вниз ↓", config.ma_fast, config.ma_slow), 1.5)); }
        if maf > mas { long_signals.push((format!("MA тренд ВВЕРХ ({:.5}>{:.5})", maf, mas), 1.0)); }
        else { short_signals.push((format!("MA тренд ВНИЗ ({:.5}<{:.5})", maf, mas), 1.0)); }
    }

    // ── MACD ─────────────────────────────────────
    let ml = last(&ind.macd_line); let mls = last(&ind.macd_signal);
    let ml_p = prev(&ind.macd_line); let mls_p = prev(&ind.macd_signal);
    let mh = last(&ind.macd_hist);
    if !ml.is_nan() && !mls.is_nan() {
        if ml_p <= mls_p && ml > mls { long_signals.push(("MACD кроссовер ↑".to_string(), 1.5)); }
        else if ml_p >= mls_p && ml < mls { short_signals.push(("MACD кроссовер ↓".to_string(), 1.5)); }
    }
    if !mh.is_nan() {
        if mh > 0.0 { long_signals.push((format!("MACD гистограмма+ ({:.6})", mh), 1.0)); }
        else { short_signals.push((format!("MACD гистограмма- ({:.6})", mh), 1.0)); }
    }

    // ── Bollinger Bands ───────────────────────────
    let bb_up = last(&ind.bb_upper); let bb_lo = last(&ind.bb_lower); let bb_mid = last(&ind.bb_middle);
    if !bb_up.is_nan() && !bb_lo.is_nan() {
        if last_price <= bb_lo { long_signals.push((format!("Цена у нижней BB ({:.5})", bb_lo), 1.3)); }
        else if last_price >= bb_up { short_signals.push((format!("Цена у верхней BB ({:.5})", bb_up), 1.3)); }
        if !bb_mid.is_nan() {
            let bw = (bb_up - bb_lo) / bb_mid;
            if bw < 0.02 { long_signals.push(("BB сужение — готовится движение".to_string(), 0.5)); short_signals.push(("BB сужение — готовится движение".to_string(), 0.5)); }
        }
    }

    // ── Volume ────────────────────────────────────
    let vol_ma = last(&ind.volume_ma);
    if !vol_ma.is_nan() && vol_ma > 0.0 {
        let vr = last_volume / vol_ma;
        if vr > 1.5 {
            if maf > mas { long_signals.push((format!("Высокий объём {:.1}x — подтверждает рост", vr), 1.2)); }
            else { short_signals.push((format!("Высокий объём {:.1}x — подтверждает падение", vr), 1.2)); }
        }
    }

    // ── Свечные паттерны (вес 2.0) ───────────────
    for p in patterns {
        match p.direction {
            PatternDirection::Bullish => long_signals.push((format!("{}: {}", p.name, p.description), 2.0)),
            PatternDirection::Bearish => short_signals.push((format!("{}: {}", p.name, p.description), 2.0)),
            PatternDirection::Neutral => { long_signals.push((p.name.clone(), 0.3)); short_signals.push((p.name.clone(), 0.3)); }
        }
    }

    // ── Дивергенции RSI (вес 2.5 — очень сильный) ─
    for d in divergences {
        match d.div_type {
            DivergenceType::BullishRegular => long_signals.push((d.description.clone(), 2.5)),
            DivergenceType::BearishRegular => short_signals.push((d.description.clone(), 2.5)),
            DivergenceType::BullishHidden  => long_signals.push((d.description.clone(), 1.5)),
            DivergenceType::BearishHidden  => short_signals.push((d.description.clone(), 1.5)),
        }
    }

    // ── Уровни поддержки/сопротивления (вес 1.5) ──
    let tolerance = 0.5; // 0.5% от цены
    if let Some(sup) = sr.nearest_support {
        let dist_pct = (last_price - sup) / last_price * 100.0;
        if dist_pct < tolerance {
            long_signals.push((format!("Цена у поддержки {:.5} ({:.2}%)", sup, dist_pct), 1.5));
        }
    }
    if let Some(res) = sr.nearest_resistance {
        let dist_pct = (res - last_price) / last_price * 100.0;
        if dist_pct < tolerance {
            short_signals.push((format!("Цена у сопротивления {:.5} ({:.2}%)", res, dist_pct), 1.5));
        }
    }

    // ── Итог ─────────────────────────────────────
    let ls: f64 = long_signals.iter().map(|(_, w)| w).sum();
    let ss: f64 = short_signals.iter().map(|(_, w)| w).sum();
    let total = ls + ss;
    let trend_up = maf > mas;
    let (adj_l, adj_s) = if trend_up { (ls * 1.1, ss * 0.9) } else { (ls * 0.9, ss * 1.1) };

    let (direction, confidence) = if adj_l > adj_s {
        (Direction::Long,  adj_l / total * 100.0)
    } else if adj_s > adj_l {
        (Direction::Short, adj_s / total * 100.0)
    } else {
        (Direction::Neutral, 50.0)
    };

    let strength = if confidence >= 75.0 { SignalStrength::Strong }
                   else if confidence >= 60.0 { SignalStrength::Medium }
                   else { SignalStrength::Weak };

    // SL/TP через ATR
    let atr = last(&ind.atr);
    let (stop_loss, take_profit) = if !atr.is_nan() && last_price > 0.0 {
        match direction {
            Direction::Long  => (last_price - 1.5 * atr, last_price + 3.0 * atr),
            Direction::Short => (last_price + 1.5 * atr, last_price - 3.0 * atr),
            Direction::Neutral => (0.0, 0.0),
        }
    } else { (0.0, 0.0) };

    SignalResult {
        direction, confidence, strength,
        long_signals:  long_signals.into_iter().map(|(s, _)| s).collect(),
        short_signals: short_signals.into_iter().map(|(s, _)| s).collect(),
        stop_loss, take_profit,
    }
}
