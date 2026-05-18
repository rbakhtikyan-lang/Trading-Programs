#![allow(unused_imports, dead_code)]
use std::fmt;

#[derive(Debug, Clone, PartialEq)]
pub enum ExchangeType { Binance, Bybit, OKX }

#[derive(Debug, Clone, PartialEq)]
pub enum MarketType { Spot, Futures }

impl MarketType {
    pub fn label(&self) -> &str {
        match self { MarketType::Spot => "SPOT", MarketType::Futures => "FUTURES" }
    }
}

#[derive(Debug, Clone)]
pub struct Candle {
    pub timestamp: u64,
    pub open: f64,
    pub high: f64,
    pub low: f64,
    pub close: f64,
    pub volume: f64,
}

#[derive(Debug)]
pub struct ExchangeError(pub String);
impl fmt::Display for ExchangeError {
    fn fmt(&self, f: &mut fmt::Formatter) -> fmt::Result { write!(f, "{}", self.0) }
}

pub struct Exchange {
    pub exchange_type: ExchangeType,
    pub market_type: MarketType,
    pub api_key: String,
    pub api_secret: String,
    client: reqwest::Client,
}

impl Exchange {
    pub fn new(exchange_type: ExchangeType, market_type: MarketType, api_key: String, api_secret: String) -> Self {
        Exchange { exchange_type, market_type, api_key, api_secret, client: reqwest::Client::new() }
    }

    pub async fn fetch_candles(&self, symbol: &str, timeframe: &str, limit: usize) -> Result<Vec<Candle>, ExchangeError> {
        match self.exchange_type {
            ExchangeType::Binance => self.fetch_binance(symbol, timeframe, limit).await,
            ExchangeType::Bybit   => self.fetch_bybit(symbol, timeframe, limit).await,
            ExchangeType::OKX     => self.fetch_okx(symbol, timeframe, limit).await,
        }
    }

    async fn fetch_binance(&self, symbol: &str, timeframe: &str, limit: usize) -> Result<Vec<Candle>, ExchangeError> {
        let sym = symbol.replace("/", "");
        // Futures используют другой endpoint
        let base = if self.market_type == MarketType::Futures {
            "https://fapi.binance.com/fapi/v1/klines"
        } else {
            "https://api.binance.com/api/v3/klines"
        };
        let url = format!("{}?symbol={}&interval={}&limit={}", base, sym, timeframe, limit);
        let resp = self.client.get(&url).send().await.map_err(|e| ExchangeError(e.to_string()))?;
        let raw: Vec<serde_json::Value> = resp.json().await.map_err(|e| ExchangeError(e.to_string()))?;
        Ok(raw.iter().map(|c| Candle {
            timestamp: c[0].as_u64().unwrap_or(0),
            open:   c[1].as_str().unwrap_or("0").parse().unwrap_or(0.0),
            high:   c[2].as_str().unwrap_or("0").parse().unwrap_or(0.0),
            low:    c[3].as_str().unwrap_or("0").parse().unwrap_or(0.0),
            close:  c[4].as_str().unwrap_or("0").parse().unwrap_or(0.0),
            volume: c[5].as_str().unwrap_or("0").parse().unwrap_or(0.0),
        }).collect())
    }

    async fn fetch_bybit(&self, symbol: &str, timeframe: &str, limit: usize) -> Result<Vec<Candle>, ExchangeError> {
        let sym = symbol.replace("/", "");
        let tf = match timeframe { "1m"=>"1","5m"=>"5","15m"=>"15","30m"=>"30","1h"=>"60","4h"=>"240",_=>"60" };
        let category = if self.market_type == MarketType::Futures { "linear" } else { "spot" };
        let url = format!("https://api.bybit.com/v5/market/kline?category={}&symbol={}&interval={}&limit={}", category, sym, tf, limit);
        let resp = self.client.get(&url).send().await.map_err(|e| ExchangeError(e.to_string()))?;
        let raw: serde_json::Value = resp.json().await.map_err(|e| ExchangeError(e.to_string()))?;
        let list = raw["result"]["list"].as_array().ok_or_else(|| ExchangeError("Неверный формат Bybit".to_string()))?;
        let mut candles: Vec<Candle> = list.iter().map(|c| {
            let a = c.as_array().unwrap();
            Candle {
                timestamp: a[0].as_str().unwrap_or("0").parse().unwrap_or(0),
                open:   a[1].as_str().unwrap_or("0").parse().unwrap_or(0.0),
                high:   a[2].as_str().unwrap_or("0").parse().unwrap_or(0.0),
                low:    a[3].as_str().unwrap_or("0").parse().unwrap_or(0.0),
                close:  a[4].as_str().unwrap_or("0").parse().unwrap_or(0.0),
                volume: a[5].as_str().unwrap_or("0").parse().unwrap_or(0.0),
            }
        }).collect();
        candles.reverse();
        Ok(candles)
    }

    async fn fetch_okx(&self, symbol: &str, timeframe: &str, limit: usize) -> Result<Vec<Candle>, ExchangeError> {
        let sym = symbol.replace("/", "-");
        let tf = match timeframe { "1m"=>"1m","5m"=>"5m","15m"=>"15m","30m"=>"30m","1h"=>"1H","4h"=>"4H",_=>"1H" };
        // OKX: для фьючерсов добавляем -SWAP к символу
        let inst_id = if self.market_type == MarketType::Futures {
            format!("{}-SWAP", sym)
        } else {
            sym.to_string()
        };
        let url = format!("https://www.okx.com/api/v5/market/candles?instId={}&bar={}&limit={}", inst_id, tf, limit);
        let resp = self.client.get(&url).send().await.map_err(|e| ExchangeError(e.to_string()))?;
        let raw: serde_json::Value = resp.json().await.map_err(|e| ExchangeError(e.to_string()))?;
        let list = raw["data"].as_array().ok_or_else(|| ExchangeError("Неверный формат OKX".to_string()))?;
        let mut candles: Vec<Candle> = list.iter().map(|c| {
            let a = c.as_array().unwrap();
            Candle {
                timestamp: a[0].as_str().unwrap_or("0").parse().unwrap_or(0),
                open:   a[1].as_str().unwrap_or("0").parse().unwrap_or(0.0),
                high:   a[2].as_str().unwrap_or("0").parse().unwrap_or(0.0),
                low:    a[3].as_str().unwrap_or("0").parse().unwrap_or(0.0),
                close:  a[4].as_str().unwrap_or("0").parse().unwrap_or(0.0),
                volume: a[5].as_str().unwrap_or("0").parse().unwrap_or(0.0),
            }
        }).collect();
        candles.reverse();
        Ok(candles)
    }
}
