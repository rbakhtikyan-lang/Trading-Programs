use colored::*;
use std::io::{self, Write};
use chrono::Local;

mod exchange;
mod indicators;
mod patterns;
mod signal;
mod divergence;
mod levels;
mod backtest;
mod history;

use exchange::{Exchange, ExchangeType, MarketType, Candle};
use indicators::Indicators;
use patterns::{detect_patterns, PatternDirection};
use divergence::detect_divergence;
use levels::find_levels;
use signal::{generate_signal_full, Direction, SignalResult};
use backtest::run_backtest;
use history::{save_signal, save_mtf_summary, HistoryEntry};

pub struct Config {
    pub rsi_period: usize, pub ma_fast: usize, pub ma_slow: usize,
    pub macd_fast: usize, pub macd_slow: usize, pub macd_signal: usize,
    pub rsi_overbought: f64, pub rsi_oversold: f64, pub candle_limit: usize,
}
impl Default for Config {
    fn default() -> Self {
        Config { rsi_period:14, ma_fast:20, ma_slow:50, macd_fast:12,
                 macd_slow:26, macd_signal:9, rsi_overbought:70.0, rsi_oversold:30.0, candle_limit:300 }
    }
}

fn input(prompt: &str) -> String {
    print!("{}", prompt); io::stdout().flush().unwrap();
    let mut buf = String::new(); io::stdin().read_line(&mut buf).unwrap();
    buf.trim().to_string()
}

fn choose_exchange() -> (ExchangeType, String, String, String) {
    println!("\n{}", "═".repeat(60).cyan());
    println!("  {}  TRADING SIGNAL BOT  v4.0", "📊".white());
    println!("{}", "═".repeat(60).cyan());
    println!("\n{}", "Выберите биржу:".yellow());
    println!("  {} Binance  {} Bybit  {} OKX", "[1]".white(), "[2]".white(), "[3]".white());
    let et = loop {
        let c = input(&format!("\n{}", "Выбор (1-3): ".green()));
        match c.as_str() { "1"=>break ExchangeType::Binance, "2"=>break ExchangeType::Bybit, "3"=>break ExchangeType::OKX, _=>println!("{}", "Неверный выбор.".red()) }
    };
    let name = match et { ExchangeType::Binance=>"Binance", ExchangeType::Bybit=>"Bybit", ExchangeType::OKX=>"OKX" };
    println!("\n{}", format!("[API] Ключи для {} (Enter = пропустить):", name).cyan());
    let k = input("  API Key:    "); let s = input("  API Secret: ");
    (et, name.to_string(), k, s)
}

fn choose_market() -> MarketType {
    println!("\n{}", "Тип рынка:".yellow());
    println!("  {} Спот  {} Фьючерсы", "[1]".white(), "[2]".white());
    match input(&format!("\n{}", "Выбор (1-2): ".green())).as_str() { "2"=>MarketType::Futures, _=>MarketType::Spot }
}

fn choose_symbol() -> String {
    let popular = ["BTC/USDT","ETH/USDT","SOL/USDT","BNB/USDT","XRP/USDT"];
    println!("\n{}", "Популярные пары:".yellow());
    for (i,s) in popular.iter().enumerate() { println!("  {} {}", format!("[{}]",i+1).white(), s); }
    println!("  {} Ввести вручную", "[0]".white());
    let c = input(&format!("\n{}", format!("Выбор (0-{}) или пара напрямую: ", popular.len()).green()));
    if c.contains('/') { c.to_uppercase() }
    else { match c.as_str() {
        "0" => input("  Символ: ").to_uppercase(),
        x if x.parse::<usize>().map(|n| n>=1&&n<=popular.len()).unwrap_or(false) => popular[x.parse::<usize>().unwrap()-1].to_string(),
        _ => if !c.is_empty() { format!("{}/USDT", c.to_uppercase()) } else { "BTC/USDT".to_string() }
    }}
}

fn choose_timeframes() -> Vec<String> {
    println!("\n{}", "Таймфрейм:".yellow());
    println!("  {} Один  {} 15m+1h+4h  {} Свой набор", "[1]".white(), "[2]".white(), "[3]".white());
    match input(&format!("\n{}", "Выбор (1-3): ".green())).as_str() {
        "2" => vec!["15m","1h","4h"].into_iter().map(String::from).collect(),
        "3" => {
            let raw = input("  Введите через запятую (1m,5m,15m,30m,1h,4h): ");
            raw.split(',').map(|s| s.trim().to_lowercase()).filter(|s| ["1m","5m","15m","30m","1h","4h"].contains(&s.as_str())).collect()
        }
        _ => {
            println!("  {} 1m  {} 5m  {} 15m  {} 30m  {} 1h  {} 4h",
                "[1]".white(),"[2]".white(),"[3]".white(),"[4]".white(),"[5]".white(),"[6]".white());
            let tf = input(&format!("\n{}", "Таймфрейм (1-6 или 1m/5m/15m/1h/4h): ".green()));
            vec![match tf.to_lowercase().as_str() {
                "1"|"1m"  => "1m",
                "2"|"5m"  => "5m",
                "3"|"15m" => "15m",
                "4"|"30m" => "30m",
                "6"|"4h"  => "4h",
                _          => "1h",
            }.to_string()]
        }
    }
}

struct TfAnalysis {
    timeframe: String, direction: String, confidence: f64,
    result: SignalResult, candles: Vec<Candle>,
    ind: Indicators, pats: Vec<patterns::PatternResult>,
    divs: Vec<divergence::Divergence>, sr: levels::SRLevels,
}

async fn analyze_tf(exchange: &Exchange, symbol: &str, timeframe: &str, config: &Config) -> Option<TfAnalysis> {
    match exchange.fetch_candles(symbol, timeframe, config.candle_limit).await {
        Ok(candles) if candles.len() >= (config.ma_slow + 5) => {
            let closes:  Vec<f64> = candles.iter().map(|c| c.close).collect();
            let highs:   Vec<f64> = candles.iter().map(|c| c.high).collect();
            let lows:    Vec<f64> = candles.iter().map(|c| c.low).collect();
            let volumes: Vec<f64> = candles.iter().map(|c| c.volume).collect();
            let lp = *closes.last().unwrap(); let lv = *volumes.last().unwrap();
            let ind  = Indicators::calculate(&closes, &highs, &lows, &volumes, config);
            let pats = detect_patterns(&candles);
            let divs = detect_divergence(&closes, 50);
            let sr   = find_levels(&candles, 0.3);
            let result = generate_signal_full(&ind, &pats, &divs, &sr, config, lp, lv);
            let dir = match result.direction { Direction::Long=>"LONG", Direction::Short=>"SHORT", Direction::Neutral=>"НЕЙТРАЛЬНО" }.to_string();
            let conf = result.confidence;
            Some(TfAnalysis { timeframe: timeframe.to_string(), direction: dir, confidence: conf, result, candles, ind, pats, divs, sr })
        }
        Ok(_)  => { println!("{}", format!("  [{}] Недостаточно данных", timeframe).red()); None }
        Err(e) => { println!("{}", format!("  [{}] Ошибка: {}", timeframe, e).red()); None }
    }
}

fn print_tf_result(a: &TfAnalysis, exchange_name: &str, symbol: &str, market: &MarketType) {
    let last = a.candles.last().unwrap();
    let lf   = |v: &Vec<f64>| v.iter().rev().find(|x| !x.is_nan()).copied().unwrap_or(f64::NAN);
    let rsi  = lf(&a.ind.rsi);
    let rsi_s = if rsi>70.0{format!("{:.2}",rsi).red().to_string()} else if rsi<30.0{format!("{:.2}",rsi).green().to_string()} else {format!("{:.2}",rsi).white().to_string()};
    let sk = lf(&a.ind.stoch_rsi_k);
    let sk_s = if sk>80.0{format!("{:.1}",sk).red().to_string()} else if sk<20.0{format!("{:.1}",sk).green().to_string()} else {format!("{:.1}",sk).white().to_string()};

    println!("\n{}", "═".repeat(60).cyan());
    println!("  🏦  {} | {} | {} | TF: {}", exchange_name, symbol, market.label(), a.timeframe);
    println!("  🕐  {}", Local::now().format("%Y-%m-%d %H:%M:%S"));
    println!("  💲  Цена: {}", format!("{:.6}", last.close).white().bold());
    println!("{}", "─".repeat(60).cyan());

    println!("\n  📈 RSI (14):      {}", rsi_s);
    println!("  📊 Stoch RSI K:   {}  D: {:.1}", sk_s, lf(&a.ind.stoch_rsi_d));
    println!("  📉 MA 20/50:      {:.6} / {:.6}", lf(&a.ind.ma_fast), lf(&a.ind.ma_slow));
    println!("  📊 MACD/Signal:   {:.6} / {:.6}", lf(&a.ind.macd_line), lf(&a.ind.macd_signal));
    println!("  📐 BB Up/Lo:      {:.6} / {:.6}", lf(&a.ind.bb_upper), lf(&a.ind.bb_lower));
    println!("  📏 ATR:           {:.6}", lf(&a.ind.atr));
    println!("  📦 Vol/MA20:      {:.2} / {:.2}", last.volume, lf(&a.ind.volume_ma));

    // Уровни S/R
    if a.sr.nearest_support.is_some() || a.sr.nearest_resistance.is_some() {
        println!("\n{}", "─".repeat(60).cyan());
        println!("  {}", "📍 УРОВНИ ПОДДЕРЖКИ/СОПРОТИВЛЕНИЯ:".yellow().bold());
        if let Some(s) = a.sr.nearest_support {
            let dist = (last.close - s) / last.close * 100.0;
            println!("    {} Поддержка: {:.6}  ({:.2}% ниже)", "🟢".green(), s, dist);
        }
        if let Some(r) = a.sr.nearest_resistance {
            let dist = (r - last.close) / last.close * 100.0;
            println!("    {} Сопротивление: {:.6}  ({:.2}% выше)", "🔴".red(), r, dist);
        }
        // Все найденные уровни
        for l in a.sr.supports.iter().take(3) {
            println!("    {} {}", "▼".green(), l.description);
        }
        for l in a.sr.resistances.iter().take(3) {
            println!("    {} {}", "▲".red(), l.description);
        }
    }

    // Дивергенции
    if !a.divs.is_empty() {
        println!("\n{}", "─".repeat(60).cyan());
        println!("  {}", "🔀 ДИВЕРГЕНЦИИ RSI:".yellow().bold());
        for d in &a.divs {
            let icon = match d.div_type {
                divergence::DivergenceType::BullishRegular => "🟢 ▲".green().to_string(),
                divergence::DivergenceType::BearishRegular => "🔴 ▼".red().to_string(),
                divergence::DivergenceType::BullishHidden  => "🔵 ▲".cyan().to_string(),
                divergence::DivergenceType::BearishHidden  => "🟠 ▼".yellow().to_string(),
            };
            println!("    {} {}", icon, d.description);
        }
    }

    // Паттерны
    if !a.pats.is_empty() {
        println!("\n{}", "─".repeat(60).cyan());
        println!("  {}", "🕯️  СВЕЧНЫЕ ПАТТЕРНЫ:".yellow().bold());
        for p in &a.pats {
            let d = match p.direction { PatternDirection::Bullish=>"▲".green().to_string(), PatternDirection::Bearish=>"▼".red().to_string(), PatternDirection::Neutral=>"◆".yellow().to_string() };
            println!("    {} {}", d, p.name);
        }
    }

    println!("\n{}", "─".repeat(60).cyan());
    if !a.result.long_signals.is_empty() {
        println!("\n  {}", "▲ СИГНАЛЫ ЛОНГ:".green().bold());
        for s in &a.result.long_signals { println!("    {} {}", "✓".green(), s); }
    }
    if !a.result.short_signals.is_empty() {
        println!("\n  {}", "▼ СИГНАЛЫ ШОРТ:".red().bold());
        for s in &a.result.short_signals { println!("    {} {}", "✓".red(), s); }
    }

    println!("\n{}", "─".repeat(60).cyan());
    let sl = match a.result.direction {
        Direction::Long    => format!("  🚀  LONG  | {:.0}%  | {}", a.result.confidence, a.result.strength.label()).black().on_green().bold().to_string(),
        Direction::Short   => format!("  📉  SHORT | {:.0}%  | {}", a.result.confidence, a.result.strength.label()).white().on_red().bold().to_string(),
        Direction::Neutral => format!("  ⚠️   НЕЙТРАЛЬНО | {:.0}%", a.result.confidence).black().on_yellow().bold().to_string(),
    };
    println!("{}", sl);
    if a.result.stop_loss > 0.0 {
        println!("\n  🛑 Stop-Loss:   {}", format!("{:.6}", a.result.stop_loss).red().bold());
        println!("  🎯 Take-Profit: {}", format!("{:.6}", a.result.take_profit).green().bold());
    }
}

fn print_mtf_summary(analyses: &[TfAnalysis], final_dir: &str, final_conf: f64) {
    println!("\n{}", "▓".repeat(60).cyan());
    println!("  {}", "📊 МУЛЬТИ-ТАЙМФРЕЙМ ИТОГ".white().bold());
    println!("{}", "─".repeat(60).cyan());
    for a in analyses {
        let dc = match a.direction.as_str() { "LONG"=>a.direction.green().to_string(), "SHORT"=>a.direction.red().to_string(), _=>a.direction.yellow().to_string() };
        println!("  {}  →  {}  ({:.0}%)", format!("[{}]",a.timeframe).white(), dc, a.confidence);
    }
    println!("{}", "─".repeat(60).cyan());
    let fl = match final_dir {
        "LONG"  => format!("  🚀  ИТОГ: LONG  |  Уверенность: {:.0}%", final_conf).black().on_green().bold().to_string(),
        "SHORT" => format!("  📉  ИТОГ: SHORT |  Уверенность: {:.0}%", final_conf).white().on_red().bold().to_string(),
        _       => format!("  ⚠️   ИТОГ: НЕЙТРАЛЬНО | {:.0}%", final_conf).black().on_yellow().bold().to_string(),
    };
    println!("{}", fl);
    println!("{}\n", "▓".repeat(60).cyan());
}

fn print_backtest(stats: &backtest::BacktestStats, symbol: &str, timeframe: &str) {
    println!("\n{}", "═".repeat(60).cyan());
    println!("  {}", "📈 РЕЗУЛЬТАТЫ BACKTESTING".white().bold());
    println!("  {} | {}", symbol, timeframe);
    println!("{}", "─".repeat(60).cyan());

    if stats.total_trades == 0 {
        println!("  {}", "Сделок не найдено (попробуйте другой таймфрейм или снизьте порог уверенности)".yellow());
        println!("{}", "═".repeat(60).cyan());
        return;
    }

    let wr_colored = if stats.win_rate >= 60.0 { format!("{:.1}%", stats.win_rate).green().to_string() }
                     else if stats.win_rate >= 45.0 { format!("{:.1}%", stats.win_rate).yellow().to_string() }
                     else { format!("{:.1}%", stats.win_rate).red().to_string() };
    let pnl_colored = if stats.total_pnl_pct >= 0.0 { format!("+{:.2}%", stats.total_pnl_pct).green().to_string() }
                      else { format!("{:.2}%", stats.total_pnl_pct).red().to_string() };
    let pf_colored = if stats.profit_factor >= 1.5 { format!("{:.2}", stats.profit_factor).green().to_string() }
                     else if stats.profit_factor >= 1.0 { format!("{:.2}", stats.profit_factor).yellow().to_string() }
                     else { format!("{:.2}", stats.profit_factor).red().to_string() };

    println!("\n  📊 Всего сделок:     {}", stats.total_trades);
    println!("  ✅ Прибыльных:       {} ({:.0}%)", stats.wins, stats.wins as f64 / stats.total_trades as f64 * 100.0);
    println!("  ❌ Убыточных:        {} ({:.0}%)", stats.losses, stats.losses as f64 / stats.total_trades as f64 * 100.0);
    println!("  🎯 Винрейт:          {}", wr_colored);
    println!("  💰 Итоговый PnL:     {}", pnl_colored);
    println!("  📈 Средний выигрыш:  +{:.2}%", stats.avg_win_pct);
    println!("  📉 Средний убыток:   {:.2}%", stats.avg_loss_pct);
    println!("  ⚖️  Profit Factor:    {}", pf_colored);
    println!("  📉 Max Drawdown:     -{:.2}%", stats.max_drawdown_pct);
    println!("  🏆 Лучшая сделка:   +{:.2}%", stats.best_trade_pct);
    println!("  💀 Худшая сделка:    {:.2}%", stats.worst_trade_pct);

    // Последние 5 сделок
    if !stats.trades.is_empty() {
        println!("\n{}", "─".repeat(60).cyan());
        println!("  {}", "Последние сделки:".yellow());
        for t in stats.trades.iter().rev().take(5) {
            let pnl_s = if t.pnl_pct >= 0.0 { format!("+{:.2}%", t.pnl_pct).green().to_string() } else { format!("{:.2}%", t.pnl_pct).red().to_string() };
            let dir_s = if t.direction == "LONG" { "🚀 LONG ".green().to_string() } else { "📉 SHORT".red().to_string() };
            println!("  {}  {:.5} → {:.5}  {}  ({} баров)", dir_s, t.entry_price, t.exit_price, pnl_s, t.bars_held);
        }
    }
    println!("{}", "═".repeat(60).cyan());
}

fn mtf_consensus(analyses: &[TfAnalysis]) -> (String, f64) {
    let weight = |tf: &str| -> f64 { match tf { "4h"=>3.0,"1h"=>2.0,"30m"=>1.5,_=>1.0 } };
    let mut lw = 0.0f64; let mut sw = 0.0f64;
    for a in analyses {
        let w = weight(&a.timeframe);
        match a.direction.as_str() { "LONG"=>lw+=w, "SHORT"=>sw+=w, _=>{lw+=w*0.5;sw+=w*0.5;} }
    }
    let total = lw + sw;
    if lw > sw { ("LONG".to_string(), lw/total*100.0) }
    else if sw > lw { ("SHORT".to_string(), sw/total*100.0) }
    else { ("НЕЙТРАЛЬНО".to_string(), 50.0) }
}

#[tokio::main]
async fn main() {
    let config = Config::default();
    let (exchange_type, exchange_name, api_key, api_secret) = choose_exchange();
    let market_type = choose_market();
    let symbol      = choose_symbol();

    // Режим: анализ или бэктест?
    println!("\n{}", "Режим:".yellow());
    println!("  {} Анализ (live сигналы)", "[1]".white());
    println!("  {} Backtesting (проверка на истории)", "[2]".white());
    let app_mode = input(&format!("\n{}", "Выбор (1-2): ".green()));

    if app_mode == "2" {
        // ── BACKTESTING ──────────────────────────
        println!("\n{}", "Таймфрейм для бэктеста:".yellow());
        println!("  {} 1m  {} 5m  {} 15m  {} 30m  {} 1h  {} 4h",
            "[1]".white(),"[2]".white(),"[3]".white(),"[4]".white(),"[5]".white(),"[6]".white());
        let tf = match input(&format!("\n{}", "Выбор: ".green())).to_lowercase().as_str() {
            "1"|"1m"  => "1m",
            "2"|"5m"  => "5m",
            "3"|"15m" => "15m",
            "4"|"30m" => "30m",
            "6"|"4h"  => "4h",
            _          => "1h",
        }.to_string();

        let exchange = Exchange::new(exchange_type, market_type.clone(), api_key, api_secret);
        println!("\n{}", "⏳ Загрузка исторических данных (1000 свечей)...".cyan());
        match exchange.fetch_candles(&symbol, &tf, 1000).await {
            Ok(candles) => {
                let candles: Vec<Candle> = candles;
                println!("{}", format!("  ✅ Загружено {} свечей", candles.len()).green());
                println!("{}", "⚙️  Запуск бэктестинга...".cyan());
                let stats = run_backtest(&candles, &config, 100);
                print_backtest(&stats, &symbol, &tf);
            }
            Err(e) => println!("{}", format!("❌ Ошибка: {}", e).red()),
        }
        return;
    }

    // ── LIVE АНАЛИЗ ──────────────────────────────
    let timeframes = choose_timeframes();
    let exchange   = Exchange::new(exchange_type, market_type.clone(), api_key, api_secret);
    let is_mtf     = timeframes.len() > 1;

    println!("\n{}", "Режим обновления:".yellow());
    println!("  {} Один анализ  {} Авто-обновление", "[1]".white(), "[2]".white());
    let mode = input(&format!("\n{}", "Выбор (1-2): ".green()));
    let interval: u64 = if mode == "2" { input("  Интервал (сек): ").parse().unwrap_or(60) } else { 0 };

    println!("\n{}", "Сохранять историю в файл? (1=Да, 2=Нет):".yellow());
    let save_history = input("  > ") != "2";
    if save_history { println!("{}", "  ✅ Сохраняется в ./signals/".green()); }

    loop {
        println!("\n{}", "⏳ Загрузка данных...".cyan());
        let mut analyses: Vec<TfAnalysis> = Vec::new();
        for tf in &timeframes {
            if let Some(a) = analyze_tf(&exchange, &symbol, tf, &config).await { analyses.push(a); }
        }

        if analyses.is_empty() {
            println!("{}", "❌ Нет данных.".red());
        } else {
            for a in &analyses {
                print_tf_result(a, &exchange_name, &symbol, &market_type);
                if save_history {
                    let entry = HistoryEntry {
                        symbol: symbol.clone(), exchange: exchange_name.clone(),
                        market: market_type.label().to_string(), timeframe: a.timeframe.clone(),
                        price: a.candles.last().map(|c| c.close).unwrap_or(0.0),
                        direction: a.direction.clone(), confidence: a.confidence,
                        strength: a.result.strength.label().to_string(),
                        stop_loss: a.result.stop_loss, take_profit: a.result.take_profit,
                        signals_long: a.result.long_signals.clone(),
                        signals_short: a.result.short_signals.clone(),
                        patterns: a.pats.iter().map(|p| p.name.clone()).collect(),
                    };
                    let _ = save_signal(&entry);
                }
            }

            if is_mtf && analyses.len() > 1 {
                let (fd, fc) = mtf_consensus(&analyses);
                print_mtf_summary(&analyses, &fd, fc);
                if save_history {
                    let tfr: Vec<(&str,&str,f64)> = analyses.iter().map(|a| (a.timeframe.as_str(), a.direction.as_str(), a.confidence)).collect();
                    let _ = save_mtf_summary(&symbol, &exchange_name, market_type.label(), &tfr, &fd, fc);
                }
            }
        }

        if mode != "2" { break; }
        println!("{}", format!("  ⏱  Следующее обновление через {} сек... (Ctrl+C для выхода)", interval).cyan());
        tokio::time::sleep(tokio::time::Duration::from_secs(interval)).await;
    }
}
