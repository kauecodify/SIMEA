// SIMEA HFT Engine
// Sistema Inteligente de Macroeconomia e Estabilidade Ambiental
// High-Frequency Trading Engine
//
// This service provides:
// - Real-time market data processing
// - Algorithmic trading strategies
// - Risk management
// - Integration with Pool Soberano

use actix_web::{web, App, HttpResponse, HttpServer, Responder, middleware::Logger};
use serde::{Serialize, Deserialize};
use std::sync::{Arc, Mutex};
use std::time::{SystemTime, UNIX_EPOCH};
use tokio::time::{interval, Duration};
use rand::Rng;

// ============================================================================
// DATA STRUCTURES
// ============================================================================

#[derive(Debug, Clone, Serialize, Deserialize)]
struct MarketData {
    symbol: String,
    price: f64,
    volume: f64,
    timestamp: u64,
    bid: f64,
    ask: f64,
    spread: f64,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
struct Trade {
    id: String,
    symbol: String,
    side: String, // "buy" or "sell"
    quantity: f64,
    price: f64,
    timestamp: u64,
    status: String, // "pending", "filled", "cancelled", "rejected"
    strategy: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
struct Portfolio {
    id: String,
    company_id: String,
    balance: f64,
    positions: Vec<Position>,
    pnl: f64,
    daily_pnl: f64,
    risk_level: String,
    max_drawdown: f64,
    sharpe_ratio: f64,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
struct Position {
    symbol: String,
    quantity: f64,
    avg_price: f64,
    current_price: f64,
    pnl: f64,
    pnl_pct: f64,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
struct StrategyConfig {
    name: String,
    description: String,
    parameters: serde_json::Value,
    enabled: bool,
    risk_per_trade: f64,
    max_positions: usize,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
struct RiskMetrics {
    var_1d: f64,
    var_7d: f64,
    var_30d: f64,
    max_loss: f64,
    liquidation_risk: f64,
    leverage: f64,
}

// ============================================================================
// APP STATE
// ============================================================================

struct AppState {
    market_data: Arc<Mutex<Vec<MarketData>>>,
    trades: Arc<Mutex<Vec<Trade>>>,
    portfolios: Arc<Mutex<Vec<Portfolio>>>,
    strategies: Arc<Mutex<Vec<StrategyConfig>>>,
    risk_metrics: Arc<Mutex<RiskMetrics>>,
    last_update: Arc<Mutex<u64>>,
}

// ============================================================================
// SERVICE IMPLEMENTATION
// ============================================================================

/// Generate mock market data
fn generate_mock_market_data(count: usize) -> Vec<MarketData> {
    let mut rng = rand::thread_rng();
    let symbols = vec![
        "PETR4.SA", "VALE3.SA", "ITUB4.SA", "BBDC4.SA", "ABEV3.SA",
        "ELET3.SA", "ELET6.SA", "BBAS3.SA", "SANB11.SA", "CSNA3.SA",
        "B3SA3.SA", "MGLU3.SA", "LREN3.SA", "AMER3.SA", "ALPA4.SA",
        "BRAP4.SA", "BRFS3.SA", "BRML3.SA", "BTOW3.SA", "CCRO3.SA",
    ];
    
    let now = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .unwrap()
        .as_secs();
    
    (0..count)
        .map(|i| {
            let symbol = symbols[i % symbols.len()].clone();
            let base_price = rng.gen_range(10.0..1000.0);
            let price_variation = (rng.gen_range(-2.0..2.0) / 100.0) * base_price;
            let price = (base_price + price_variation).max(0.01);
            let volume = rng.gen_range(1000.0..1000000.0);
            let spread = price * rng.gen_range(0.001..0.01);
            
            MarketData {
                symbol,
                price: (price * 100.0).round() / 100.0,
                volume: (volume * 100.0).round() / 100.0,
                timestamp: now - (i as u64 * 60),
                bid: ((price - spread/2.0) * 100.0).round() / 100.0,
                ask: ((price + spread/2.0) * 100.0).round() / 100.0,
                spread: (spread * 10000.0).round() / 10000.0,
            }
        })
        .collect()
}

/// Generate mock portfolio data
fn generate_mock_portfolios(company_ids: Vec<String>) -> Vec<Portfolio> {
    let mut rng = rand::thread_rng();
    let symbols = vec![
        "PETR4.SA", "VALE3.SA", "ITUB4.SA", "BBDC4.SA", "ABEV3.SA",
    ];
    
    company_ids
        .into_iter()
        .enumerate()
        .map(|(i, company_id)| {
            let balance = rng.gen_range(1_000_000.0..100_000_000.0);
            let num_positions = rng.gen_range(1..5);
            
            let positions: Vec<Position> = (0..num_positions)
                .map(|j| {
                    let symbol = symbols[j % symbols.len()].clone();
                    let quantity = rng.gen_range(100.0..10000.0);
                    let avg_price = rng.gen_range(10.0..100.0);
                    let current_price = avg_price * (1.0 + (rng.gen_range(-0.2..0.2)));
                    let pnl = (current_price - avg_price) * quantity;
                    let pnl_pct = (pnl / (avg_price * quantity)) * 100.0;
                    
                    Position {
                        symbol,
                        quantity: (quantity * 100.0).round() / 100.0,
                        avg_price: (avg_price * 100.0).round() / 100.0,
                        current_price: (current_price * 100.0).round() / 100.0,
                        pnl: (pnl * 100.0).round() / 100.0,
                        pnl_pct: (pnl_pct * 100.0).round() / 100.0,
                    }
                })
                .collect();
            
            let total_pnl: f64 = positions.iter().map(|p| p.pnl).sum();
            let daily_pnl = total_pnl * rng.gen_range(0.0..0.1);
            
            Portfolio {
                id: format!("portfolio-{}", i + 1),
                company_id,
                balance: (balance * 100.0).round() / 100.0,
                positions,
                pnl: (total_pnl * 100.0).round() / 100.0,
                daily_pnl: (daily_pnl * 100.0).round() / 100.0,
                risk_level: match rng.gen_range(0..3) {
                    0 => "low".to_string(),
                    1 => "medium".to_string(),
                    _ => "high".to_string(),
                },
                max_drawdown: (rng.gen_range(0.0..15.0) * 100.0).round() / 100.0,
                sharpe_ratio: (rng.gen_range(0.5..3.0) * 100.0).round() / 100.0,
            }
        })
        .collect()
}

/// Generate mock strategies
fn generate_mock_strategies() -> Vec<StrategyConfig> {
    vec![
        StrategyConfig {
            name: "mean_reversion".to_string(),
            description: "Mean reversion strategy for liquid stocks".to_string(),
            parameters: serde_json::json!({
                "window": 20,
                "threshold": 2.0,
                "stop_loss": 0.02,
                "take_profit": 0.05
            }),
            enabled: true,
            risk_per_trade: 0.01,
            max_positions: 10,
        },
        StrategyConfig {
            name: "momentum".to_string(),
            description: "Momentum strategy based on price trends".to_string(),
            parameters: serde_json::json!({
                "window": 50,
                "threshold": 0.1,
                "stop_loss": 0.03,
                "take_profit": 0.08
            }),
            enabled: true,
            risk_per_trade: 0.015,
            max_positions: 8,
        },
        StrategyConfig {
            name: "arbitrage".to_string(),
            description: "Arbitrage strategy for mispriced assets".to_string(),
            parameters: serde_json::json!({
                "min_spread": 0.005,
                "max_spread": 0.02,
                "execution_time": 100
            }),
            enabled: true,
            risk_per_trade: 0.005,
            max_positions: 5,
        },
        StrategyConfig {
            name: "market_making".to_string(),
            description: "Market making strategy for liquidity provision".to_string(),
            parameters: serde_json::json!({
                "spread": 0.002,
                "order_size": 1000.0,
                "inventory_limit": 10000.0
            }),
            enabled: true,
            risk_per_trade: 0.002,
            max_positions: 20,
        },
    ]
}

/// Initialize application state
fn init_state() -> AppState {
    // Generate mock company IDs (matching frontend pool companies)
    let company_ids: Vec<String> = (0..50)
        .map(|i| format!("#{:06}", 100000 + i))
        .collect();
    
    AppState {
        market_data: Arc::new(Mutex::new(generate_mock_market_data(50))),
        trades: Arc::new(Mutex::new(Vec::new())),
        portfolios: Arc::new(Mutex::new(generate_mock_portfolios(company_ids))),
        strategies: Arc::new(Mutex::new(generate_mock_strategies())),
        risk_metrics: Arc::new(Mutex::new(RiskMetrics {
            var_1d: 0.5,
            var_7d: 1.2,
            var_30d: 2.5,
            max_loss: 5.0,
            liquidation_risk: 0.1,
            leverage: 2.0,
        })),
        last_update: Arc::new(Mutex::new(
            SystemTime::now()
                .duration_since(UNIX_EPOCH)
                .unwrap()
                .as_secs()
        )),
    }
}

// ============================================================================
// API HANDLERS
// ============================================================================

/// Health check endpoint
async fn health_check(data: web::Data<AppState>) -> impl Responder {
    let market_data = data.market_data.lock().unwrap();
    let trades = data.trades.lock().unwrap();
    let portfolios = data.portfolios.lock().unwrap();
    let strategies = data.strategies.lock().unwrap();
    let risk_metrics = data.risk_metrics.lock().unwrap();
    
    HttpResponse::Ok().json(serde_json::json!({
        "status": "healthy",
        "service": "SIMEA HFT Engine",
        "version": "1.0.0",
        "timestamp": SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .unwrap()
            .as_secs(),
        "stats": {
            "market_data_count": market_data.len(),
            "trades_count": trades.len(),
            "portfolios_count": portfolios.len(),
            "strategies_count": strategies.len(),
            "var_1d": risk_metrics.var_1d,
            "var_7d": risk_metrics.var_7d,
        }
    }))
}

/// Get all market data
async fn get_market_data(data: web::Data<AppState>) -> impl Responder {
    let market_data = data.market_data.lock().unwrap();
    HttpResponse::Ok().json(serde_json::json!({
        "status": "success",
        "data": market_data.clone(),
        "count": market_data.len(),
        "timestamp": *data.last_update.lock().unwrap()
    }))
}

/// Get market data for a specific symbol
async fn get_market_data_symbol(
    data: web::Data<AppState>,
    symbol: web::Path<String>
) -> impl Responder {
    let market_data = data.market_data.lock().unwrap();
    
    if let Some(md) = market_data.iter().find(|md| md.symbol == *symbol) {
        HttpResponse::Ok().json(serde_json::json!({
            "status": "success",
            "data": md.clone()
        }))
    } else {
        HttpResponse::NotFound().json(serde_json::json!({
            "status": "error",
            "message": format!("Symbol {} not found", symbol)
        }))
    }
}

/// Get all portfolios
async fn get_portfolios(data: web::Data<AppState>) -> impl Responder {
    let portfolios = data.portfolios.lock().unwrap();
    HttpResponse::Ok().json(serde_json::json!({
        "status": "success",
        "data": portfolios.clone(),
        "count": portfolios.len()
    }))
}

/// Get portfolio by ID
async fn get_portfolio(
    data: web::Data<AppState>,
    id: web::Path<String>
) -> impl Responder {
    let portfolios = data.portfolios.lock().unwrap();
    
    if let Some(portfolio) = portfolios.iter().find(|p| p.id == *id || p.company_id == *id) {
        HttpResponse::Ok().json(serde_json::json!({
            "status": "success",
            "data": portfolio.clone()
        }))
    } else {
        HttpResponse::NotFound().json(serde_json::json!({
            "status": "error",
            "message": format!("Portfolio {} not found", id)
        }))
    }
}

/// Get portfolio by company ID
async fn get_portfolio_by_company(
    data: web::Data<AppState>,
    company_id: web::Path<String>
) -> impl Responder {
    let portfolios = data.portfolios.lock().unwrap();
    
    let portfolio = portfolios.iter()
        .find(|p| p.company_id == *company_id)
        .cloned();
    
    match portfolio {
        Some(p) => HttpResponse::Ok().json(serde_json::json!({
            "status": "success",
            "data": p
        })),
        None => HttpResponse::NotFound().json(serde_json::json!({
            "status": "error",
            "message": format!("No portfolio found for company {}", company_id)
        }))
    }
}

/// Get all trades
async fn get_trades(data: web::Data<AppState>) -> impl Responder {
    let trades = data.trades.lock().unwrap();
    HttpResponse::Ok().json(serde_json::json!({
        "status": "success",
        "data": trades.clone(),
        "count": trades.len()
    }))
}

/// Execute a trade
async fn execute_trade(
    data: web::Data<AppState>,
    trade_req: web::Json<TradeRequest>
) -> impl Responder {
    let mut trades = data.trades.lock().unwrap();
    let mut portfolios = data.portfolios.lock().unwrap();
    let market_data = data.market_data.lock().unwrap();
    
    // Find the symbol price
    let symbol_price = market_data.iter()
        .find(|md| md.symbol == trade_req.symbol)
        .map(|md| md.price);
    
    match symbol_price {
        Some(price) => {
            let trade_value = trade_req.quantity * price;
            
            // Find portfolio
            let portfolio = portfolios.iter_mut()
                .find(|p| p.id == trade_req.portfolio_id || p.company_id == trade_req.portfolio_id);
            
            match portfolio {
                Some(p) => {
                    if trade_req.side == "buy" && trade_value > p.balance {
                        return HttpResponse::BadRequest().json(serde_json::json!({
                            "status": "error",
                            "message": "Insufficient balance for buy order"
                        }));
                    }
                    
                    // Update portfolio balance
                    if trade_req.side == "buy" {
                        p.balance -= trade_value;
                    } else {
                        p.balance += trade_value;
                    }
                    
                    // Create trade
                    let trade = Trade {
                        id: format!("trade-{}", trades.len() + 1),
                        symbol: trade_req.symbol.clone(),
                        side: trade_req.side.clone(),
                        quantity: trade_req.quantity,
                        price,
                        timestamp: SystemTime::now()
                            .duration_since(UNIX_EPOCH)
                            .unwrap()
                            .as_secs(),
                        status: "filled".to_string(),
                        strategy: trade_req.strategy.clone(),
                    };
                    
                    trades.push(trade.clone());
                    
                    HttpResponse::Ok().json(serde_json::json!({
                        "status": "success",
                        "message": "Trade executed successfully",
                        "data": trade,
                        "portfolio": {
                            "id": p.id.clone(),
                            "new_balance": p.balance
                        }
                    }))
                }
                None => HttpResponse::NotFound().json(serde_json::json!({
                    "status": "error",
                    "message": format!("Portfolio {} not found", trade_req.portfolio_id)
                }))
            }
        }
        None => HttpResponse::NotFound().json(serde_json::json!({
            "status": "error",
            "message": format!("Symbol {} not found", trade_req.symbol)
        }))
    }
}

/// Get all strategies
async fn get_strategies(data: web::Data<AppState>) -> impl Responder {
    let strategies = data.strategies.lock().unwrap();
    HttpResponse::Ok().json(serde_json::json!({
        "status": "success",
        "data": strategies.clone(),
        "count": strategies.len()
    }))
}

/// Get risk metrics
async fn get_risk_metrics(data: web::Data<AppState>) -> impl Responder {
    let risk_metrics = data.risk_metrics.lock().unwrap();
    HttpResponse::Ok().json(serde_json::json!({
        "status": "success",
        "data": risk_metrics.clone()
    }))
}

/// Update market data (simulate real-time updates)
async fn update_market_data(data: web::Data<AppState>) -> impl Responder {
    let mut market_data = data.market_data.lock().unwrap();
    let mut last_update = data.last_update.lock().unwrap();
    
    let mut rng = rand::thread_rng();
    let now = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .unwrap()
        .as_secs();
    
    for md in market_data.iter_mut() {
        let price_change = (rng.gen_range(-2.0..2.0) / 100.0) * md.price;
        md.price = (md.price + price_change).max(0.01);
        md.bid = md.price - md.spread / 2.0;
        md.ask = md.price + md.spread / 2.0;
        md.timestamp = now;
    }
    
    *last_update = now;
    
    HttpResponse::Ok().json(serde_json::json!({
        "status": "success",
        "message": "Market data updated",
        "count": market_data.len(),
        "timestamp": now
    }))
}

// ============================================================================
// REQUEST/RESPONSE TYPES
// ============================================================================

#[derive(Debug, Serialize, Deserialize)]
struct TradeRequest {
    portfolio_id: String,
    symbol: String,
    side: String,
    quantity: f64,
    strategy: String,
}

// ============================================================================
// BACKGROUND TASKS
// ============================================================================

/// Background task to simulate real-time market updates
async fn market_data_simulator(data: web::Data<AppState>) {
    let mut interval = interval(Duration::from_secs(5));
    
    loop {
        interval.tick().await;
        
        let mut market_data = data.market_data.lock().unwrap();
        let mut last_update = data.last_update.lock().unwrap();
        let mut rng = rand::thread_rng();
        
        let now = SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .unwrap()
            .as_secs();
        
        for md in market_data.iter_mut() {
            let price_change = (rng.gen_range(-1.0..1.0) / 100.0) * md.price;
            md.price = (md.price + price_change).max(0.01);
            md.bid = md.price - md.spread / 2.0;
            md.ask = md.price + md.spread / 2.0;
            md.timestamp = now;
            
            // Random volume changes
            md.volume *= 1.0 + (rng.gen_range(-0.1..0.1));
            md.volume = md.volume.max(0.0);
        }
        
        *last_update = now;
    }
}

/// Background task to simulate trading
async fn trading_simulator(data: web::Data<AppState>) {
    let mut interval = interval(Duration::from_secs(10));
    
    loop {
        interval.tick().await;
        
        let market_data = data.market_data.lock().unwrap();
        let mut trades = data.trades.lock().unwrap();
        let mut portfolios = data.portfolios.lock().unwrap();
        let strategies = data.strategies.lock().unwrap();
        let mut rng = rand::thread_rng();
        
        let now = SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .unwrap()
            .as_secs();
        
        // Randomly execute trades based on strategies
        if !market_data.is_empty() && !portfolios.is_empty() && !strategies.is_empty() {
            let strategy = &strategies[rng.gen_range(0..strategies.len())];
            let portfolio = &mut portfolios[rng.gen_range(0..portfolios.len())];
            let symbol = &market_data[rng.gen_range(0..market_data.len())].symbol;
            let price = market_data.iter().find(|md| md.symbol == *symbol).map(|md| md.price);
            
            if let Some(price) = price {
                let side = if rng.gen_bool(0.5) { "buy" } else { "sell" };
                let quantity = rng.gen_range(100.0..10000.0);
                let trade_value = quantity * price;
                
                // Check if portfolio can afford the trade
                if side == "buy" && trade_value > portfolio.balance {
                    continue;
                }
                
                // Update portfolio
                if side == "buy" {
                    portfolio.balance -= trade_value;
                } else {
                    portfolio.balance += trade_value;
                }
                
                // Create trade
                let trade = Trade {
                    id: format!("trade-{}", trades.len() + 1),
                    symbol: symbol.clone(),
                    side: side.to_string(),
                    quantity,
                    price,
                    timestamp: now,
                    status: "filled".to_string(),
                    strategy: strategy.name.clone(),
                };
                
                trades.push(trade);
            }
        }
    }
}

// ============================================================================
// MAIN FUNCTION
// ============================================================================

#[actix_web::main]
async fn main() -> std::io::Result<()> {
    // Initialize logging
    env_logger::init_from_env(env_logger::Env::new().default_filter_or("info"));
    
    // Initialize application state
    let state = web::Data::new(init_state());
    
    // Start background tasks
    tokio::spawn(market_data_simulator(state.clone()));
    tokio::spawn(trading_simulator(state.clone()));
    
    println!("✓ SIMEA HFT Engine starting...");
    
    // Start HTTP server
    HttpServer::new(move || {
        App::new()
            .app_data(state.clone())
            .wrap(Logger::default())
            .route("/health", web::get().to(health_check))
            .route("/market-data", web::get().to(get_market_data))
            .route("/market-data/{symbol}", web::get().to(get_market_data_symbol))
            .route("/market-data/update", web::post().to(update_market_data))
            .route("/portfolios", web::get().to(get_portfolios))
            .route("/portfolios/{id}", web::get().to(get_portfolio))
            .route("/portfolios/company/{company_id}", web::get().to(get_portfolio_by_company))
            .route("/trades", web::get().to(get_trades))
            .route("/trades/execute", web::post().to(execute_trade))
            .route("/strategies", web::get().to(get_strategies))
            .route("/risk-metrics", web::get().to(get_risk_metrics))
    })
    .bind(("0.0.0.0", 4000))?
    .run()
    .await
}
