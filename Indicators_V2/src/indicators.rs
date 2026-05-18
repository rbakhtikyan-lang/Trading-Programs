use crate::Config;

pub struct Indicators {
    pub rsi: Vec<f64>,
    pub stoch_rsi_k: Vec<f64>,
    pub stoch_rsi_d: Vec<f64>,
    pub ma_fast: Vec<f64>,
    pub ma_slow: Vec<f64>,
    pub macd_line: Vec<f64>,
    pub macd_signal: Vec<f64>,
    pub macd_hist: Vec<f64>,
    pub bb_upper: Vec<f64>,
    pub bb_middle: Vec<f64>,
    pub bb_lower: Vec<f64>,
    pub atr: Vec<f64>,
    pub volume_ma: Vec<f64>,
}

impl Indicators {
    pub fn calculate(closes: &[f64], highs: &[f64], lows: &[f64], volumes: &[f64], config: &Config) -> Self {
        let rsi = calc_rsi(closes, config.rsi_period);
        let (stoch_k, stoch_d) = calc_stoch_rsi(&rsi, 14, 3, 3);
        let ma_fast = calc_sma(closes, config.ma_fast);
        let ma_slow = calc_sma(closes, config.ma_slow);
        let (macd_line, macd_signal, macd_hist) = calc_macd(closes, config.macd_fast, config.macd_slow, config.macd_signal);
        let (bb_upper, bb_middle, bb_lower) = calc_bollinger(closes, 20, 2.0);
        let atr = calc_atr(highs, lows, closes, 14);
        let volume_ma = calc_sma(volumes, 20);

        Indicators { rsi, stoch_rsi_k: stoch_k, stoch_rsi_d: stoch_d, ma_fast, ma_slow, macd_line, macd_signal, macd_hist, bb_upper, bb_middle, bb_lower, atr, volume_ma }
    }
}

pub fn calc_rsi(closes: &[f64], period: usize) -> Vec<f64> {
    let n = closes.len();
    let mut rsi = vec![f64::NAN; n];
    if n < period + 1 { return rsi; }
    let mut avg_gain = 0.0f64;
    let mut avg_loss = 0.0f64;
    for i in 1..=period {
        let d = closes[i] - closes[i - 1];
        if d > 0.0 { avg_gain += d; } else { avg_loss += -d; }
    }
    avg_gain /= period as f64;
    avg_loss /= period as f64;
    rsi[period] = if avg_loss == 0.0 { 100.0 } else { 100.0 - 100.0 / (1.0 + avg_gain / avg_loss) };
    let k = 1.0 / period as f64;
    for i in (period + 1)..n {
        let d = closes[i] - closes[i - 1];
        let gain = if d > 0.0 { d } else { 0.0 };
        let loss = if d < 0.0 { -d } else { 0.0 };
        avg_gain = avg_gain * (1.0 - k) + gain * k;
        avg_loss = avg_loss * (1.0 - k) + loss * k;
        rsi[i] = if avg_loss == 0.0 { 100.0 } else { 100.0 - 100.0 / (1.0 + avg_gain / avg_loss) };
    }
    rsi
}

fn calc_stoch_rsi(rsi: &[f64], period: usize, k_period: usize, d_period: usize) -> (Vec<f64>, Vec<f64>) {
    let n = rsi.len();
    let mut raw_k = vec![f64::NAN; n];
    for i in (period - 1)..n {
        let slice: Vec<f64> = rsi[(i + 1 - period)..=i].iter().filter(|v| !v.is_nan()).copied().collect();
        if slice.is_empty() { continue; }
        let min = slice.iter().cloned().fold(f64::INFINITY, f64::min);
        let max = slice.iter().cloned().fold(f64::NEG_INFINITY, f64::max);
        if !rsi[i].is_nan() && (max - min).abs() > 1e-10 {
            raw_k[i] = (rsi[i] - min) / (max - min) * 100.0;
        }
    }
    let smooth_k = calc_sma(&raw_k, k_period);
    let stoch_d  = calc_sma(&smooth_k, d_period);
    (smooth_k, stoch_d)
}

pub fn calc_sma(data: &[f64], period: usize) -> Vec<f64> {
    let n = data.len();
    let mut sma = vec![f64::NAN; n];
    if n < period { return sma; }
    for i in (period - 1)..n {
        let vals: Vec<f64> = data[(i + 1 - period)..=i].iter().filter(|v| !v.is_nan()).copied().collect();
        if vals.len() == period { sma[i] = vals.iter().sum::<f64>() / period as f64; }
    }
    sma
}

pub fn calc_ema(data: &[f64], period: usize) -> Vec<f64> {
    let n = data.len();
    let mut ema = vec![f64::NAN; n];
    if n < period { return ema; }
    let k = 2.0 / (period as f64 + 1.0);
    ema[period - 1] = data[..period].iter().sum::<f64>() / period as f64;
    for i in period..n { ema[i] = data[i] * k + ema[i - 1] * (1.0 - k); }
    ema
}

fn calc_macd(closes: &[f64], fast: usize, slow: usize, signal: usize) -> (Vec<f64>, Vec<f64>, Vec<f64>) {
    let n = closes.len();
    let ema_fast = calc_ema(closes, fast);
    let ema_slow = calc_ema(closes, slow);
    let mut macd_line = vec![f64::NAN; n];
    for i in 0..n {
        if !ema_fast[i].is_nan() && !ema_slow[i].is_nan() { macd_line[i] = ema_fast[i] - ema_slow[i]; }
    }
    let vs = macd_line.iter().position(|v| !v.is_nan()).unwrap_or(n);
    let sig = calc_ema(&macd_line[vs..], signal);
    let mut msf = vec![f64::NAN; n];
    let mut mhf = vec![f64::NAN; n];
    for (i, &sv) in sig.iter().enumerate() {
        let idx = vs + i;
        if !sv.is_nan() && !macd_line[idx].is_nan() { msf[idx] = sv; mhf[idx] = macd_line[idx] - sv; }
    }
    (macd_line, msf, mhf)
}

fn calc_bollinger(closes: &[f64], period: usize, mult: f64) -> (Vec<f64>, Vec<f64>, Vec<f64>) {
    let n = closes.len();
    let mut upper = vec![f64::NAN; n];
    let mut middle = vec![f64::NAN; n];
    let mut lower = vec![f64::NAN; n];
    if n < period { return (upper, middle, lower); }
    for i in (period - 1)..n {
        let slice = &closes[(i + 1 - period)..=i];
        let mean = slice.iter().sum::<f64>() / period as f64;
        let std = (slice.iter().map(|x| (x - mean).powi(2)).sum::<f64>() / period as f64).sqrt();
        middle[i] = mean;
        upper[i]  = mean + mult * std;
        lower[i]  = mean - mult * std;
    }
    (upper, middle, lower)
}

pub fn calc_atr(highs: &[f64], lows: &[f64], closes: &[f64], period: usize) -> Vec<f64> {
    let n = closes.len();
    let mut atr = vec![f64::NAN; n];
    if n < period + 1 { return atr; }
    let mut tr_sum = 0.0;
    for i in 1..=period {
        let tr = (highs[i] - lows[i]).max((highs[i] - closes[i-1]).abs()).max((lows[i] - closes[i-1]).abs());
        tr_sum += tr;
    }
    atr[period] = tr_sum / period as f64;
    let k = 1.0 / period as f64;
    for i in (period + 1)..n {
        let tr = (highs[i] - lows[i]).max((highs[i] - closes[i-1]).abs()).max((lows[i] - closes[i-1]).abs());
        atr[i] = atr[i-1] * (1.0 - k) + tr * k;
    }
    atr
}
