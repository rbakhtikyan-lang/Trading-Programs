#![allow(dead_code)]
use crate::exchange::Candle;
use crate::indicators::Indicators;
use crate::patterns::detect_patterns;
use crate::signal::{generate_signal, Direction};
use crate::Config;

#[derive(Debug)]
pub struct Trade {
    pub entry_price: f64,
    pub exit_price: f64,
    pub direction: String,
    pub pnl_pct: f64,
    pub result: TradeResult,
    pub bars_held: usize,
    pub entry_bar: usize,
}

#[derive(Debug)]
pub enum TradeResult { Win, Loss, BreakEven }

#[derive(Debug)]
pub struct BacktestStats {
    pub total_trades: usize,
    pub wins: usize,
    pub losses: usize,
    pub win_rate: f64,
    pub total_pnl_pct: f64,
    pub avg_win_pct: f64,
    pub avg_loss_pct: f64,
    pub profit_factor: f64,
    pub max_drawdown_pct: f64,
    pub best_trade_pct: f64,
    pub worst_trade_pct: f64,
    pub trades: Vec<Trade>,
}

pub fn run_backtest(candles: &[Candle], config: &Config, lookback: usize) -> BacktestStats {
    let n = candles.len();
    let min_candles = lookback + config.ma_slow + 5;

    let mut trades: Vec<Trade> = Vec::new();
    let mut i = min_candles;

    while i < n - 1 {
        // Берём срез для анализа
        let slice = &candles[i.saturating_sub(lookback)..=i];
        let closes:  Vec<f64> = slice.iter().map(|c| c.close).collect();
        let highs:   Vec<f64> = slice.iter().map(|c| c.high).collect();
        let lows:    Vec<f64> = slice.iter().map(|c| c.low).collect();
        let volumes: Vec<f64> = slice.iter().map(|c| c.volume).collect();

        if closes.len() < config.ma_slow + 1 { i += 1; continue; }

        let last_price  = *closes.last().unwrap();
        let last_volume = *volumes.last().unwrap();
        let ind    = Indicators::calculate(&closes, &highs, &lows, &volumes, config);
        let pats   = detect_patterns(slice);
        let result = generate_signal(&ind, &pats, config, last_price, last_volume);

        // Пропускаем слабые сигналы
        if result.confidence < 60.0 { i += 1; continue; }

        let direction = match result.direction {
            Direction::Long    => "LONG",
            Direction::Short   => "SHORT",
            Direction::Neutral => { i += 1; continue; }
        };

        let entry_price = candles[i + 1].open; // Входим на открытии следующей свечи
        let sl = result.stop_loss;
        let tp = result.take_profit;

        if sl == 0.0 || tp == 0.0 { i += 1; continue; }

        // Симулируем выход: ищем SL или TP
        let mut exit_price = candles[n - 1].close;
        let mut bars_held  = 0;
        let mut j = i + 2;

        while j < n {
            let bar = &candles[j];
            bars_held = j - i;

            let hit_tp = match direction {
                "LONG"  => bar.high >= tp,
                "SHORT" => bar.low  <= tp,
                _       => false,
            };
            let hit_sl = match direction {
                "LONG"  => bar.low  <= sl,
                "SHORT" => bar.high >= sl,
                _       => false,
            };

            if hit_tp {
                exit_price = tp;
                break;
            }
            if hit_sl {
                exit_price = sl;
                break;
            }

            // Максимум держим 20 баров
            if bars_held >= 20 {
                exit_price = bar.close;
                break;
            }
            j += 1;
        }

        let pnl_pct = match direction {
            "LONG"  => (exit_price - entry_price) / entry_price * 100.0,
            "SHORT" => (entry_price - exit_price) / entry_price * 100.0,
            _       => 0.0,
        };

        let trade_result = if pnl_pct > 0.1 { TradeResult::Win }
                           else if pnl_pct < -0.1 { TradeResult::Loss }
                           else { TradeResult::BreakEven };

        trades.push(Trade {
            entry_price, exit_price,
            direction: direction.to_string(),
            pnl_pct, result: trade_result,
            bars_held, entry_bar: i,
        });

        // Прыгаем вперёд чтобы не открывать сделки внутри текущей
        i += bars_held.max(1) + 1;
    }

    compute_stats(trades)
}

fn compute_stats(trades: Vec<Trade>) -> BacktestStats {
    if trades.is_empty() {
        return BacktestStats {
            total_trades: 0, wins: 0, losses: 0, win_rate: 0.0,
            total_pnl_pct: 0.0, avg_win_pct: 0.0, avg_loss_pct: 0.0,
            profit_factor: 0.0, max_drawdown_pct: 0.0,
            best_trade_pct: 0.0, worst_trade_pct: 0.0, trades,
        };
    }

    let wins:   Vec<f64> = trades.iter().filter(|t| matches!(t.result, TradeResult::Win)).map(|t| t.pnl_pct).collect();
    let losses: Vec<f64> = trades.iter().filter(|t| matches!(t.result, TradeResult::Loss)).map(|t| t.pnl_pct).collect();

    let total_trades = trades.len();
    let win_count    = wins.len();
    let loss_count   = losses.len();
    let win_rate     = win_count as f64 / total_trades as f64 * 100.0;
    let total_pnl    = trades.iter().map(|t| t.pnl_pct).sum::<f64>();
    let avg_win      = if win_count  > 0 { wins.iter().sum::<f64>()   / win_count  as f64 } else { 0.0 };
    let avg_loss     = if loss_count > 0 { losses.iter().sum::<f64>() / loss_count as f64 } else { 0.0 };
    let gross_profit = wins.iter().sum::<f64>();
    let gross_loss   = losses.iter().map(|x| x.abs()).sum::<f64>();
    let profit_factor = if gross_loss > 0.0 { gross_profit / gross_loss } else { gross_profit };

    // Max drawdown
    let mut peak = 0.0f64;
    let mut equity = 0.0f64;
    let mut max_dd = 0.0f64;
    for t in &trades {
        equity += t.pnl_pct;
        if equity > peak { peak = equity; }
        let dd = peak - equity;
        if dd > max_dd { max_dd = dd; }
    }

    let best  = trades.iter().map(|t| t.pnl_pct).fold(f64::NEG_INFINITY, f64::max);
    let worst = trades.iter().map(|t| t.pnl_pct).fold(f64::INFINITY, f64::min);

    BacktestStats {
        total_trades, wins: win_count, losses: loss_count,
        win_rate, total_pnl_pct: total_pnl,
        avg_win_pct: avg_win, avg_loss_pct: avg_loss,
        profit_factor, max_drawdown_pct: max_dd,
        best_trade_pct: best, worst_trade_pct: worst,
        trades,
    }
}
