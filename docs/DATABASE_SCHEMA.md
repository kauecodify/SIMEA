# SIMEA Database Schema Documentation

## Overview

This document describes the database schema for the **Sistema Inteligente de Macroeconomia e Estabilidade Ambiental (SIMEA)**. The schema is designed to support:

- **Pool Soberano**: Management of 500+ companies with bankruptcy simulation
- **SIMEA-Port**: Port control and management
- **Trading Operations**: HFT engine data
- **Quantum Analytics**: Quantum computing results and insights
- **B2G Auditing**: Audit trails and compliance

---

## Database Technologies

| Component | Technology | Purpose |
|-----------|------------|---------|
| Primary DB | PostgreSQL 14+ | Transactional data, ACID compliance |
| Time Series | TimescaleDB | Time-series data (yields, prices, metrics) |
| Cache | Redis Cluster | Real-time data caching |
| Messaging | Apache Kafka | Event streaming |
| Search | Elasticsearch | Full-text search and analytics |

---

## 1. Pool Soberano Schema

### 1.1 Companies Table

```sql
CREATE TABLE pool_companies (
    id VARCHAR(20) PRIMARY KEY,           -- e.g., #123456
    name VARCHAR(255) NOT NULL,
    segment VARCHAR(100) NOT NULL,        -- e.g., "Agro Sustentável"
    region VARCHAR(50) NOT NULL,           -- Norte, Nordeste, Centro-Oeste, Sudeste, Sul
    contribution NUMERIC(20, 2) NOT NULL,  -- Initial contribution in BRL
    current_balance NUMERIC(20, 2) NOT NULL,
    base_yield DECIMAL(5, 2) NOT NULL,     -- Base yield percentage
    yield_pct DECIMAL(5, 2) NOT NULL,      -- Current yield percentage
    last_yield DECIMAL(5, 2),             -- Last recorded yield
    earnings NUMERIC(20, 2) DEFAULT 0,     -- Total earnings
    total_withdrawn NUMERIC(20, 2) DEFAULT 0,
    rating VARCHAR(10) NOT NULL,           -- A+, A, A-, B+, B, B-, C+, C
    audit_status VARCHAR(20) NOT NULL,     -- B2G-OK, B2G-PEND, B2G-REJECTED
    is_falencia BOOLEAN DEFAULT FALSE,     -- Bankruptcy flag
    falencia_contribution NUMERIC(20, 2) DEFAULT 0, -- 20% of contribution to sovereign fund
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    -- Constraints
    CONSTRAINT chk_contribution CHECK (contribution > 0),
    CONSTRAINT chk_yield CHECK (base_yield > 0 AND base_yield <= 50),
    CONSTRAINT chk_balance CHECK (current_balance >= 0),
    CONSTRAINT chk_rating CHECK (rating IN ('A+', 'A', 'A-', 'B+', 'B', 'B-', 'C+', 'C'))
);

CREATE INDEX idx_pool_companies_segment ON pool_companies(segment);
CREATE INDEX idx_pool_companies_region ON pool_companies(region);
CREATE INDEX idx_pool_companies_audit ON pool_companies(audit_status);
CREATE INDEX idx_pool_companies_falencia ON pool_companies(is_falencia);
```

### 1.2 Yield History Table (TimescaleDB Hypertable)

```sql
-- Create as hypertable for time-series optimization
CREATE TABLE pool_yield_history (
    id BIGSERIAL PRIMARY KEY,
    company_id VARCHAR(20) NOT NULL REFERENCES pool_companies(id),
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
    value NUMERIC(20, 2) NOT NULL,        -- Yield value in BRL
    yield_pct DECIMAL(5, 2) NOT NULL,     -- Yield percentage at this point
    
    -- Time-series partitioning
    CONSTRAINT chk_timestamp CHECK (timestamp > '2020-01-01')
);

-- Convert to hypertable
SELECT create_hypertable('pool_yield_history', 'timestamp');

-- Create indexes
CREATE INDEX idx_yield_history_company ON pool_yield_history(company_id);
CREATE INDEX idx_yield_history_timestamp ON pool_yield_history(timestamp);
```

### 1.3 Withdrawal History Table

```sql
CREATE TABLE pool_withdrawals (
    id BIGSERIAL PRIMARY KEY,
    company_id VARCHAR(20) NOT NULL REFERENCES pool_companies(id),
    user_id VARCHAR(100) NOT NULL,        -- User who requested withdrawal
    amount NUMERIC(20, 2) NOT NULL,
    method VARCHAR(20) NOT NULL,          -- PIX, CNPJ, BANK_TRANSFER
    pix_key VARCHAR(255),                  -- PIX key (if applicable)
    cnpj VARCHAR(20),                      -- CNPJ (if applicable)
    audit_code VARCHAR(100),               -- B2G audit code for CNPJ withdrawals
    status VARCHAR(20) NOT NULL,           -- PENDING, APPROVED, REJECTED, COMPLETED
    daily_yield NUMERIC(20, 2),            -- Daily yield at time of withdrawal
    max_withdrawal NUMERIC(20, 2),         -- Max allowed withdrawal (20% of daily yield)
    fee NUMERIC(10, 2) DEFAULT 0,          -- Withdrawal fee
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP WITH TIME ZONE,
    
    -- Constraints
    CONSTRAINT chk_amount CHECK (amount > 0),
    CONSTRAINT chk_method CHECK (method IN ('PIX', 'CNPJ', 'BANK_TRANSFER')),
    CONSTRAINT chk_status CHECK (status IN ('PENDING', 'APPROVED', 'REJECTED', 'COMPLETED'))
);

CREATE INDEX idx_withdrawals_company ON pool_withdrawals(company_id);
CREATE INDEX idx_withdrawals_user ON pool_withdrawals(user_id);
CREATE INDEX idx_withdrawals_status ON pool_withdrawals(status);
CREATE INDEX idx_withdrawals_timestamp ON pool_withdrawals(created_at);
```

### 1.4 Segments Table

```sql
CREATE TABLE pool_segments (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE,
    description TEXT,
    category VARCHAR(100),
    risk_level VARCHAR(20),               -- LOW, MEDIUM, HIGH
    avg_yield DECIMAL(5, 2),
    total_investment NUMERIC(20, 2) DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

INSERT INTO pool_segments (name, description, category, risk_level) VALUES
    ('Agro Sustentável', 'Agricultura sustentável e orgânica', 'Agricultura', 'MEDIUM'),
    ('Biodiversidade', 'Conservação da biodiversidade', 'Ambiental', 'LOW'),
    ('Energia Renovável', 'Energias limpas e renováveis', 'Energia', 'LOW'),
    ('Logística', 'Logística verde e eficiente', 'Infraestrutura', 'MEDIUM'),
    ('Captura de Carbono', 'Tecnologias de captura de CO2', 'Ambiental', 'MEDIUM'),
    ('Conservação', 'Áreas de conservação ambiental', 'Ambiental', 'LOW'),
    ('Saneamento', 'Saneamento básico e tratamento de água', 'Infraestrutura', 'MEDIUM'),
    ('Mineração Verde', 'Mineração com práticas sustentáveis', 'Industrial', 'HIGH'),
    ('Energia Solar', 'Geração de energia solar', 'Energia', 'LOW'),
    ('Varejo Sustentável', 'Comércio varejista com práticas ESG', 'Comércio', 'MEDIUM'),
    ('Agrofloresta', 'Sistemas agroflorestais', 'Agricultura', 'LOW'),
    ('Reflorestamento', 'Projetos de reflorestamento', 'Ambiental', 'LOW'),
    ('Reciclagem', 'Reciclagem de resíduos', 'Ambiental', 'MEDIUM'),
    ('Bioenergia', 'Produção de bioenergia', 'Energia', 'MEDIUM'),
    ('Aquicultura', 'Cultivo sustentável de peixes', 'Agricultura', 'MEDIUM'),
    ('Turismo Ecológico', 'Turismo com foco ambiental', 'Serviços', 'LOW'),
    ('Construção Verde', 'Construção civil sustentável', 'Infraestrutura', 'MEDIUM'),
    ('Mobilidade Elétrica', 'Veículos e infraestrutura elétrica', 'Transporte', 'MEDIUM'),
    ('Saúde Ambiental', 'Saúde com foco ambiental', 'Saúde', 'LOW'),
    ('Tecnologia Limpa', 'Tecnologias limpas e inovadoras', 'Tecnologia', 'MEDIUM');
```

---

## 2. SIMEA-Port Schema

### 2.1 Ports Table

```sql
CREATE TABLE port_ports (
    id VARCHAR(50) PRIMARY KEY,            -- e.g., port-001
    name VARCHAR(255) NOT NULL,
    code VARCHAR(20) NOT NULL UNIQUE,     -- IATA/UN code
    region VARCHAR(50) NOT NULL,           -- Norte, Nordeste, Centro-Oeste, Sudeste, Sul
    city VARCHAR(100) NOT NULL,
    state VARCHAR(50) NOT NULL,
    latitude DECIMAL(10, 8) NOT NULL,
    longitude DECIMAL(11, 8) NOT NULL,
    status VARCHAR(20) NOT NULL,           -- operational, maintenance, closed
    
    -- Capacity metrics
    max_cargo_ton NUMERIC(15, 2),
    max_ships INTEGER,
    current_utilization DECIMAL(5, 2),    -- Percentage
    
    -- Operational metrics
    total_cargo_ton NUMERIC(15, 2) DEFAULT 0,
    operations_per_day INTEGER DEFAULT 0,
    efficiency DECIMAL(5, 2) DEFAULT 0,   -- Percentage
    
    -- Environmental metrics
    co2_emissions NUMERIC(15, 2) DEFAULT 0,
    energy_consumption NUMERIC(15, 2) DEFAULT 0,
    renewable_energy_pct DECIMAL(5, 2) DEFAULT 0,
    waste_recycling_pct DECIMAL(5, 2) DEFAULT 0,
    water_usage NUMERIC(15, 2) DEFAULT 0,
    
    -- Financial metrics
    revenue NUMERIC(15, 2) DEFAULT 0,
    cost NUMERIC(15, 2) DEFAULT 0,
    profit_margin DECIMAL(5, 2) DEFAULT 0,
    investments NUMERIC(15, 2) DEFAULT 0,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT chk_utilization CHECK (current_utilization >= 0 AND current_utilization <= 100),
    CONSTRAINT chk_efficiency CHECK (efficiency >= 0 AND efficiency <= 100),
    CONSTRAINT chk_renewable CHECK (renewable_energy_pct >= 0 AND renewable_energy_pct <= 100)
);

CREATE INDEX idx_ports_region ON port_ports(region);
CREATE INDEX idx_ports_status ON port_ports(status);
CREATE INDEX idx_ports_code ON port_ports(code);
```

### 2.2 Cargo Operations Table

```sql
CREATE TABLE port_cargo_operations (
    id VARCHAR(100) PRIMARY KEY,          -- e.g., cargo-port-001-001
    port_id VARCHAR(50) NOT NULL REFERENCES port_ports(id),
    ship_id VARCHAR(100) NOT NULL,
    type VARCHAR(20) NOT NULL,             -- import, export, transshipment
    cargo_type VARCHAR(50) NOT NULL,        -- container, bulk, liquid, etc.
    weight_ton NUMERIC(12, 2) NOT NULL,
    value NUMERIC(15, 2) NOT NULL,
    origin VARCHAR(100),
    destination VARCHAR(100),
    status VARCHAR(20) NOT NULL,           -- pending, in_progress, completed, cancelled
    start_time TIMESTAMP WITH TIME ZONE,
    end_time TIMESTAMP WITH TIME ZONE,
    
    -- Environmental impact
    co2_emission NUMERIC(12, 2) DEFAULT 0,
    energy_used NUMERIC(12, 2) DEFAULT 0,
    waste_generated NUMERIC(12, 2) DEFAULT 0,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT chk_weight CHECK (weight_ton > 0),
    CONSTRAINT chk_value CHECK (value >= 0),
    CONSTRAINT chk_status CHECK (status IN ('pending', 'in_progress', 'completed', 'cancelled'))
);

CREATE INDEX idx_cargo_port ON port_cargo_operations(port_id);
CREATE INDEX idx_cargo_status ON port_cargo_operations(status);
CREATE INDEX idx_cargo_type ON port_cargo_operations(cargo_type);
CREATE INDEX idx_cargo_timestamp ON port_cargo_operations(created_at);
```

### 2.3 Environmental Metrics Table (TimescaleDB)

```sql
CREATE TABLE port_environmental_metrics (
    id BIGSERIAL PRIMARY KEY,
    port_id VARCHAR(50) NOT NULL REFERENCES port_ports(id),
    date DATE NOT NULL,
    co2_emissions NUMERIC(12, 2) NOT NULL,
    no2_emissions NUMERIC(12, 2) NOT NULL,
    so2_emissions NUMERIC(12, 2) NOT NULL,
    particulate_matter NUMERIC(12, 2) NOT NULL,
    water_quality DECIMAL(4, 2) NOT NULL,    -- pH level
    noise_levels DECIMAL(5, 2) NOT NULL,     -- dB
    biodiversity_index DECIMAL(5, 4) NOT NULL, -- 0 to 1
    compliance_score DECIMAL(5, 2) NOT NULL, -- 0 to 100
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT chk_date CHECK (date >= '2020-01-01'),
    CONSTRAINT chk_ph CHECK (water_quality >= 0 AND water_quality <= 14),
    CONSTRAINT chk_compliance CHECK (compliance_score >= 0 AND compliance_score <= 100),
    CONSTRAINT chk_biodiversity CHECK (biodiversity_index >= 0 AND biodiversity_index <= 1)
);

SELECT create_hypertable('port_environmental_metrics', 'date');
CREATE INDEX idx_env_port ON port_environmental_metrics(port_id);
CREATE INDEX idx_env_date ON port_environmental_metrics(date);
```

### 2.4 Port Insights Table

```sql
CREATE TABLE port_insights (
    id BIGSERIAL PRIMARY KEY,
    port_id VARCHAR(50) NOT NULL REFERENCES port_ports(id),
    metric_type VARCHAR(50) NOT NULL,     -- efficiency, capacity, environmental, financial
    value NUMERIC(15, 4) NOT NULL,
    trend VARCHAR(20) NOT NULL,           -- up, down, stable
    trend_pct NUMERIC(10, 4) NOT NULL,
    benchmark NUMERIC(15, 4),
    recommendations TEXT[],
    generated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    valid_until TIMESTAMP WITH TIME ZONE NOT NULL,
    
    CONSTRAINT chk_trend CHECK (trend IN ('up', 'down', 'stable'))
);

CREATE INDEX idx_insights_port ON port_insights(port_id);
CREATE INDEX idx_insights_type ON port_insights(metric_type);
CREATE INDEX idx_insights_timestamp ON port_insights(generated_at);
```

### 2.5 Pool-Port Integration Table

```sql
CREATE TABLE port_pool_integration (
    id BIGSERIAL PRIMARY KEY,
    port_id VARCHAR(50) NOT NULL REFERENCES port_ports(id),
    company_id VARCHAR(20) NOT NULL REFERENCES pool_companies(id),
    integration_type VARCHAR(50) NOT NULL, -- logistics, financial, environmental
    status VARCHAR(20) NOT NULL,           -- active, pending, inactive
    data_shared TEXT[],                     -- List of data types shared
    sync_frequency VARCHAR(20) NOT NULL,   -- real-time, hourly, daily
    last_sync TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT chk_integration_type CHECK (integration_type IN ('logistics', 'financial', 'environmental', 'all')),
    CONSTRAINT chk_status CHECK (status IN ('active', 'pending', 'inactive')),
    CONSTRAINT chk_sync_freq CHECK (sync_frequency IN ('real-time', 'hourly', 'daily', 'weekly', 'manual'))
);

CREATE INDEX idx_integration_port ON port_pool_integration(port_id);
CREATE INDEX idx_integration_company ON port_pool_integration(company_id);
CREATE INDEX idx_integration_status ON port_pool_integration(status);
```

---

## 3. HFT Engine Schema

### 3.1 Market Data Table (TimescaleDB)

```sql
CREATE TABLE hft_market_data (
    id BIGSERIAL PRIMARY KEY,
    symbol VARCHAR(20) NOT NULL,
    price NUMERIC(15, 4) NOT NULL,
    volume NUMERIC(15, 2) NOT NULL,
    bid NUMERIC(15, 4) NOT NULL,
    ask NUMERIC(15, 4) NOT NULL,
    spread NUMERIC(10, 6) NOT NULL,
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
    
    CONSTRAINT chk_price CHECK (price > 0),
    CONSTRAINT chk_volume CHECK (volume >= 0),
    CONSTRAINT chk_spread CHECK (spread >= 0)
);

SELECT create_hypertable('hft_market_data', 'timestamp');
CREATE INDEX idx_market_symbol ON hft_market_data(symbol);
CREATE INDEX idx_market_timestamp ON hft_market_data(timestamp);
```

### 3.2 Trades Table

```sql
CREATE TABLE hft_trades (
    id VARCHAR(100) PRIMARY KEY,
    portfolio_id VARCHAR(100) NOT NULL,
    symbol VARCHAR(20) NOT NULL,
    side VARCHAR(10) NOT NULL,             -- buy, sell
    quantity NUMERIC(15, 4) NOT NULL,
    price NUMERIC(15, 4) NOT NULL,
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
    status VARCHAR(20) NOT NULL,           -- pending, filled, cancelled, rejected
    strategy VARCHAR(50) NOT NULL,
    fee NUMERIC(10, 4) DEFAULT 0,
    pnl NUMERIC(15, 4),
    
    CONSTRAINT chk_side CHECK (side IN ('buy', 'sell')),
    CONSTRAINT chk_quantity CHECK (quantity > 0),
    CONSTRAINT chk_price CHECK (price > 0),
    CONSTRAINT chk_status CHECK (status IN ('pending', 'filled', 'cancelled', 'rejected'))
);

CREATE INDEX idx_trades_portfolio ON hft_trades(portfolio_id);
CREATE INDEX idx_trades_symbol ON hft_trades(symbol);
CREATE INDEX idx_trades_status ON hft_trades(status);
CREATE INDEX idx_trades_timestamp ON hft_trades(timestamp);
```

### 3.3 Portfolios Table

```sql
CREATE TABLE hft_portfolios (
    id VARCHAR(100) PRIMARY KEY,
    company_id VARCHAR(20) REFERENCES pool_companies(id),
    name VARCHAR(255),
    balance NUMERIC(15, 2) NOT NULL,
    pnl NUMERIC(15, 2) DEFAULT 0,
    daily_pnl NUMERIC(15, 2) DEFAULT 0,
    risk_level VARCHAR(20) NOT NULL,      -- low, medium, high
    max_drawdown DECIMAL(5, 2) DEFAULT 0,
    sharpe_ratio DECIMAL(5, 4) DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT chk_balance CHECK (balance >= 0),
    CONSTRAINT chk_risk CHECK (risk_level IN ('low', 'medium', 'high', 'very_high'))
);

CREATE INDEX idx_portfolios_company ON hft_portfolios(company_id);
CREATE INDEX idx_portfolios_risk ON hft_portfolios(risk_level);
```

### 3.4 Positions Table

```sql
CREATE TABLE hft_positions (
    id BIGSERIAL PRIMARY KEY,
    portfolio_id VARCHAR(100) NOT NULL REFERENCES hft_portfolios(id),
    symbol VARCHAR(20) NOT NULL,
    quantity NUMERIC(15, 4) NOT NULL,
    avg_price NUMERIC(15, 4) NOT NULL,
    current_price NUMERIC(15, 4),
    pnl NUMERIC(15, 4) DEFAULT 0,
    pnl_pct DECIMAL(8, 4) DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT chk_quantity CHECK (quantity != 0),
    CONSTRAINT chk_avg_price CHECK (avg_price > 0)
);

CREATE INDEX idx_positions_portfolio ON hft_positions(portfolio_id);
CREATE INDEX idx_positions_symbol ON hft_positions(symbol);
```

### 3.5 Strategies Table

```sql
CREATE TABLE hft_strategies (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE,
    description TEXT,
    parameters JSONB NOT NULL,
    enabled BOOLEAN DEFAULT TRUE,
    risk_per_trade DECIMAL(5, 4) NOT NULL,
    max_positions INTEGER NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT chk_risk CHECK (risk_per_trade > 0 AND risk_per_trade <= 1),
    CONSTRAINT chk_max_positions CHECK (max_positions > 0)
);
```

### 3.6 Risk Metrics Table

```sql
CREATE TABLE hft_risk_metrics (
    id BIGSERIAL PRIMARY KEY,
    portfolio_id VARCHAR(100) REFERENCES hft_portfolios(id),
    var_1d NUMERIC(15, 2) NOT NULL,
    var_7d NUMERIC(15, 2) NOT NULL,
    var_30d NUMERIC(15, 2) NOT NULL,
    max_loss NUMERIC(15, 2) NOT NULL,
    liquidation_risk DECIMAL(5, 4) NOT NULL,
    leverage DECIMAL(5, 2) NOT NULL,
    calculated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT chk_liquidation CHECK (liquidation_risk >= 0 AND liquidation_risk <= 1),
    CONSTRAINT chk_leverage CHECK (leverage >= 0)
);

CREATE INDEX idx_risk_portfolio ON hft_risk_metrics(portfolio_id);
CREATE INDEX idx_risk_timestamp ON hft_risk_metrics(calculated_at);
```

---

## 4. Quantum Service Schema

### 4.1 Quantum Optimizations Table

```sql
CREATE TABLE quantum_optimizations (
    id VARCHAR(100) PRIMARY KEY,
    optimization_type VARCHAR(50) NOT NULL, -- portfolio, strategy, risk
    input_data JSONB NOT NULL,
    output_data JSONB NOT NULL,
    num_qubits INTEGER NOT NULL,
    num_iterations INTEGER NOT NULL,
    execution_time_ms INTEGER NOT NULL,
    status VARCHAR(20) NOT NULL,           -- pending, completed, failed
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP WITH TIME ZONE,
    
    CONSTRAINT chk_type CHECK (optimization_type IN ('portfolio', 'strategy', 'risk', 'prediction')),
    CONSTRAINT chk_status CHECK (status IN ('pending', 'completed', 'failed'))
);

CREATE INDEX idx_quantum_type ON quantum_optimizations(optimization_type);
CREATE INDEX idx_quantum_status ON quantum_optimizations(status);
```

### 4.2 Quantum Predictions Table

```sql
CREATE TABLE quantum_predictions (
    id BIGSERIAL PRIMARY KEY,
    symbol VARCHAR(20) NOT NULL,
    model VARCHAR(50) NOT NULL,            -- QSVM, QNN, etc.
    prediction_type VARCHAR(50) NOT NULL, -- price, trend, volatility
    predicted_value NUMERIC(15, 4),
    confidence DECIMAL(5, 4) NOT NULL,
    forecast_date DATE NOT NULL,
    actual_value NUMERIC(15, 4),
    error NUMERIC(15, 4),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT chk_confidence CHECK (confidence >= 0 AND confidence <= 1)
);

CREATE INDEX idx_predictions_symbol ON quantum_predictions(symbol);
CREATE INDEX idx_predictions_model ON quantum_predictions(model);
CREATE INDEX idx_predictions_date ON quantum_predictions(forecast_date);
```

### 4.3 Quantum Risk Analysis Table

```sql
CREATE TABLE quantum_risk_analysis (
    id VARCHAR(100) PRIMARY KEY,
    portfolio_id VARCHAR(100),
    analysis_type VARCHAR(50) NOT NULL,   -- var, cvar, stress_test
    parameters JSONB NOT NULL,
    results JSONB NOT NULL,
    confidence_level DECIMAL(5, 4) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT chk_analysis_type CHECK (analysis_type IN ('var', 'cvar', 'stress_test', 'monte_carlo')),
    CONSTRAINT chk_confidence CHECK (confidence_level >= 0 AND confidence_level <= 1)
);

CREATE INDEX idx_quantum_risk_portfolio ON quantum_risk_analysis(portfolio_id);
CREATE INDEX idx_quantum_risk_type ON quantum_risk_analysis(analysis_type);
```

---

## 5. B2G Audit Schema

### 5.1 Audit Log Table

```sql
CREATE TABLE b2g_audit_log (
    id BIGSERIAL PRIMARY KEY,
    transaction_id VARCHAR(100) NOT NULL,
    transaction_type VARCHAR(50) NOT NULL, -- WITHDRAWAL, DEPOSIT, TRADE, etc.
    company_id VARCHAR(20) REFERENCES pool_companies(id),
    user_id VARCHAR(100) NOT NULL,
    amount NUMERIC(20, 2),
    method VARCHAR(20),                  -- PIX, CNPJ, etc.
    audit_code VARCHAR(100),
    status VARCHAR(20) NOT NULL,           -- pending, approved, rejected
    reason TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    reviewed_at TIMESTAMP WITH TIME ZONE,
    reviewer_id VARCHAR(100),
    
    CONSTRAINT chk_transaction_type CHECK (transaction_type IN ('WITHDRAWAL', 'DEPOSIT', 'TRADE', 'TRANSFER', 'ADJUSTMENT')),
    CONSTRAINT chk_status CHECK (status IN ('pending', 'approved', 'rejected', 'cancelled'))
);

CREATE INDEX idx_audit_transaction ON b2g_audit_log(transaction_id);
CREATE INDEX idx_audit_company ON b2g_audit_log(company_id);
CREATE INDEX idx_audit_user ON b2g_audit_log(user_id);
CREATE INDEX idx_audit_status ON b2g_audit_log(status);
CREATE INDEX idx_audit_timestamp ON b2g_audit_log(created_at);
```

### 5.2 Users Table

```sql
CREATE TABLE b2g_users (
    id VARCHAR(100) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    email VARCHAR(255) NOT NULL UNIQUE,
    role VARCHAR(50) NOT NULL,            -- admin, auditor, user, system
    status VARCHAR(20) NOT NULL,           -- active, inactive, suspended
    permissions TEXT[],                     -- List of permissions
    last_login TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT chk_role CHECK (role IN ('admin', 'auditor', 'user', 'system')),
    CONSTRAINT chk_status CHECK (status IN ('active', 'inactive', 'suspended'))
);

CREATE INDEX idx_users_email ON b2g_users(email);
CREATE INDEX idx_users_role ON b2g_users(role);
```

---

## 6. Redis Cache Structure

### 6.1 Real-time Data Keys

```
# Market data (TTL: 1 second)
HFT:MARKET:{symbol} -> {price, volume, bid, ask, spread, timestamp}

# Portfolio balances (TTL: 5 seconds)
HFT:PORTFOLIO:{id}:BALANCE -> {balance, pnl, daily_pnl}

# Pool company data (TTL: 10 seconds)
POOL:COMPANY:{id} -> {name, segment, region, currentBalance, yieldPct, ...}

# Port metrics (TTL: 30 seconds)
PORT:{id}:METRICS -> {carga_total, eficiencia, emissao_co2, ...}
```

### 6.2 Aggregated Data Keys

```
# Pool KPIs (TTL: 1 minute)
POOL:KPIS -> {totalPooled, companiesCount, avgYield, ...}

# Port KPIs (TTL: 1 minute)
PORT:KPIS -> {totalCarga, avgEficiencia, totalEmissao, ...}

# HFT KPIs (TTL: 1 minute)
HFT:KPIS -> {totalTrades, totalVolume, totalPnL, ...}
```

### 6.3 Rate Limiting Keys

```
# API rate limiting (TTL: 1 minute)
RATE_LIMIT:API:{user_id} -> {count, reset_at}

# Withdrawal rate limiting (TTL: 24 hours)
RATE_LIMIT:WITHDRAW:{user_id} -> {count, total_amount, reset_at}
```

---

## 7. Kafka Topics

| Topic | Description | Partitions | Replication Factor | Retention |
|-------|-------------|------------|-------------------|-----------|
| `pool.yield.updates` | Real-time yield updates for companies | 10 | 3 | 7 days |
| `pool.withdrawals` | Withdrawal requests and processing | 10 | 3 | 30 days |
| `port.cargo.updates` | Cargo operation updates | 5 | 3 | 7 days |
| `port.metrics` | Port environmental and operational metrics | 5 | 3 | 30 days |
| `hft.market.data` | Market data updates | 20 | 3 | 1 day |
| `hft.trades` | Trade execution events | 20 | 3 | 30 days |
| `quantum.optimizations` | Quantum optimization results | 5 | 3 | 7 days |
| `b2g.audit.events` | B2G audit events | 5 | 3 | 90 days |
| `simea.terminal` | Terminal events for Matrix Mode | 3 | 2 | 1 day |

---

## 8. Elasticsearch Indices

### 8.1 Companies Index

```json
{
  "index": "pool_companies",
  "mappings": {
    "properties": {
      "id": { "type": "keyword" },
      "name": { "type": "text", "analyzer": "portuguese" },
      "segment": { "type": "keyword" },
      "region": { "type": "keyword" },
      "contribution": { "type": "double" },
      "currentBalance": { "type": "double" },
      "yieldPct": { "type": "double" },
      "rating": { "type": "keyword" },
      "audit": { "type": "keyword" },
      "isFalencia": { "type": "boolean" },
      "createdAt": { "type": "date" }
    }
  }
}
```

### 8.2 Ports Index

```json
{
  "index": "port_ports",
  "mappings": {
    "properties": {
      "id": { "type": "keyword" },
      "name": { "type": "text", "analyzer": "portuguese" },
      "code": { "type": "keyword" },
      "region": { "type": "keyword" },
      "city": { "type": "text" },
      "state": { "type": "keyword" },
      "status": { "type": "keyword" },
      "metrics": {
        "type": "object",
        "properties": {
          "cargaTotal": { "type": "double" },
          "eficiencia": { "type": "double" },
          "emissaoCo2": { "type": "double" }
        }
      },
      "location": {
        "type": "geo_point"
      }
    }
  }
}
```

---

## 9. Data Flow Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                        SIMEA ARCHITECTURE                            │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐        │
│  │   Frontend   │    │    API       │    │   Backend    │        │
│  │   (HTML/JS)  │◄───►│  Gateway     │◄───►│  Services    │        │
│  └──────────────┘    └──────────────┘    └──────────────┘        │
│           ▲                  ▲                  ▲                │
│           │                  │                  │                │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐        │
│  │   Redis      │    │  PostgreSQL  │    │   Kafka      │        │
│  │   (Cache)    │◄───┤  (Primary)   │◄───►│  (Streaming) │        │
│  └──────────────┘    └──────────────┘    └──────────────┘        │
│                              ▲                                        │
│                              │                                        │
│                     ┌──────────────┐                                │
│                     │ TimescaleDB  │                                │
│                     │ (Time-series)│                                │
│                     └──────────────┘                                │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 10. Backup and Recovery

### 10.1 PostgreSQL Backup

```bash
# Daily backup
pg_dump -U postgres -h localhost -F c -f /backups/simea_postgres_$(date +%Y%m%d).dump simea_db

# Restore
pg_restore -U postgres -h localhost -d simea_db /backups/simea_postgres_20241109.dump
```

### 10.2 TimescaleDB Backup

```bash
# Continuous WAL archiving
timescaledb-tune --yes
pg_dump -U postgres -h localhost -F c -f /backups/simea_timescale_$(date +%Y%m%d).dump simea_db
```

### 10.3 Redis Backup

```bash
# Save to disk (RDB)
redis-cli SAVE

# Automated daily backup
redis-cli --rdb /backups/simea_redis_$(date +%Y%m%d).rdb

# Restore
redis-server --dbfilename simea_redis_20241109.rdb
```

---

## 11. Security Considerations

### 11.1 Encryption

- **At Rest**: All databases use AES-256 encryption
- **In Transit**: TLS 1.3 for all connections
- **Sensitive Data**: PIX keys and CNPJ numbers are encrypted with additional layer

### 11.2 Access Control

- **Role-Based Access Control (RBAC)**: Different access levels for different roles
- **B2G Authorization**: Special permissions for B2G auditors
- **API Keys**: Required for external service access

### 11.3 Audit Trail

- All write operations are logged
- B2G audit codes are tracked and validated
- Withdrawal operations require audit approval for amounts > 20% of daily yield

---

## 12. Performance Optimization

### 12.1 Indexing Strategy

- All foreign keys are indexed
- Frequently queried columns have composite indexes
- Time-series data uses hypertables with time-based partitioning

### 12.2 Caching Strategy

- **L1 Cache**: In-memory (application-level)
- **L2 Cache**: Redis (distributed cache)
- **Cache Invalidation**: Event-driven (via Kafka)

### 12.3 Query Optimization

- Materialized views for complex aggregations
- Query batching for bulk operations
- Connection pooling for all database connections

---

## 13. Monitoring and Alerts

### 13.1 Key Metrics

| Metric | Description | Threshold |
|--------|-------------|-----------|
| Database latency | Query response time | > 100ms |
| Cache hit ratio | Redis cache efficiency | < 90% |
| Kafka lag | Consumer lag | > 1000 messages |
| Error rate | API error percentage | > 1% |

### 13.2 Alerts

- Database connection failures
- High query latency
- Cache memory pressure
- Kafka consumer lag
- Authentication failures

---

## 14. Migration Scripts

All database migrations are managed using **Flyway** or **Liquibase** and are stored in the `/migrations` directory.

Example migration file: `V1__Initial_Schema.sql`

---

## 15. Data Retention Policy

| Data Type | Retention Period | Storage |
|-----------|------------------|---------|
| Real-time metrics | 1 day | Redis |
| Time-series data | 1 year | TimescaleDB |
| Transactional data | 7 years | PostgreSQL |
| Audit logs | 10 years | PostgreSQL + WORM |
| Backup data | 30 days | S3 + Glacier |

---

## 16. Contact Information

For questions or issues related to the SIMEA database schema:

- **Database Team**: db-team@hackbrasil.com
- **Architecture Team**: architecture@hackbrasil.com
- **Emergency Contact**: +55 11 99999-9999

---

*Document Version: 1.0.0*  
*Last Updated: 2024-11-09*  
*Maintainer: SIMEA Development Team*
