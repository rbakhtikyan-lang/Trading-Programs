use std::fs::{OpenOptions, create_dir_all};
use std::io::Write;
use chrono::Local;


pub struct HistoryEntry {
    pub symbol: String,
    pub exchange: String,
    pub market: String,
    pub timeframe: String,
    pub price: f64,
    pub direction: String,
    pub confidence: f64,
    pub strength: String,
    pub stop_loss: f64,
    pub take_profit: f64,
    pub signals_long: Vec<String>,
    pub signals_short: Vec<String>,
    pub patterns: Vec<String>,
}

pub fn save_signal(entry: &HistoryEntry) -> std::io::Result<()> {
    create_dir_all("signals")?;

    let date_str = Local::now().format("%Y-%m-%d").to_string();
    let datetime_str = Local::now().format("%Y-%m-%d %H:%M:%S").to_string();
    let filename = format!("signals/signals_{}.log", date_str);

    let mut file = OpenOptions::new()
        .create(true)
        .append(true)
        .open(&filename)?;

    let separator = "═".repeat(60);
    writeln!(file, "\n{}", separator)?;
    writeln!(file, "  📅 {}", datetime_str)?;
    writeln!(file, "  🏦 {} | {} | {} | TF: {}",
        entry.exchange, entry.symbol, entry.market, entry.timeframe)?;
    writeln!(file, "  💲 Цена: {:.6}", entry.price)?;
    writeln!(file, "{}", "─".repeat(60))?;

    // Сигнал
    let dir_icon = match entry.direction.as_str() {
        "LONG"  => "🚀",
        "SHORT" => "📉",
        _       => "⚠️ ",
    };
    writeln!(file, "  {} {} | Уверенность: {:.0}% | {}",
        dir_icon, entry.direction, entry.confidence, entry.strength)?;

    if entry.stop_loss > 0.0 {
        writeln!(file, "  🛑 Stop-Loss:   {:.6}", entry.stop_loss)?;
        writeln!(file, "  🎯 Take-Profit: {:.6}", entry.take_profit)?;
    }

    // Паттерны
    if !entry.patterns.is_empty() {
        writeln!(file, "{}", "─".repeat(60))?;
        writeln!(file, "  🕯️  Паттерны: {}", entry.patterns.join(", "))?;
    }

    // Сигналы LONG
    if !entry.signals_long.is_empty() {
        writeln!(file, "{}", "─".repeat(60))?;
        writeln!(file, "  ▲ ЛОНГ сигналы:")?;
        for s in &entry.signals_long { writeln!(file, "    ✓ {}", s)?; }
    }

    // Сигналы SHORT
    if !entry.signals_short.is_empty() {
        writeln!(file, "  ▼ ШОРТ сигналы:")?;
        for s in &entry.signals_short { writeln!(file, "    ✓ {}", s)?; }
    }

    writeln!(file, "{}", separator)?;
    Ok(())
}

pub fn save_mtf_summary(
    symbol: &str,
    exchange: &str,
    market: &str,
    tf_results: &[(&str, &str, f64)], // (timeframe, direction, confidence)
    final_direction: &str,
    final_confidence: f64,
) -> std::io::Result<()> {
    create_dir_all("signals")?;
    let date_str = Local::now().format("%Y-%m-%d").to_string();
    let datetime_str = Local::now().format("%Y-%m-%d %H:%M:%S").to_string();
    let filename = format!("signals/signals_{}.log", date_str);

    let mut file = OpenOptions::new().create(true).append(true).open(&filename)?;

    writeln!(file, "\n{}", "▓".repeat(60))?;
    writeln!(file, "  📊 МУЛЬТИ-ТАЙМФРЕЙМ АНАЛИЗ")?;
    writeln!(file, "  📅 {} | {} | {} | {}", datetime_str, exchange, symbol, market)?;
    writeln!(file, "{}", "─".repeat(60))?;
    for (tf, dir, conf) in tf_results {
        writeln!(file, "  {} → {} ({:.0}%)", tf, dir, conf)?;
    }
    writeln!(file, "{}", "─".repeat(60))?;
    writeln!(file, "  🏆 ИТОГ: {} | Уверенность: {:.0}%", final_direction, final_confidence)?;
    writeln!(file, "{}", "▓".repeat(60))?;
    Ok(())
}
