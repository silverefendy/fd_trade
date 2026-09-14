# FD-Trade

Personal stock trading journal, risk management, and broker-flow screening system for Indonesian stock market (IDX) swing and fast trading.

## Overview

FD-Trade is a discretionary trading journal system that enforces a strict risk management "constitution" with position sizing based on fixed risk percentage, daily/weekly/monthly loss limits, no margin usage, and mandatory logging of psychological factors (FOMO, revenge trading) alongside every trade. The system also screens informal trading tips (from Telegram/Discord) and broker transaction data ("bandarmologi") as separate confirmation layers.

## Features

### Core DocTypes

- **Trading Account Settings**: Single DocType storing account-wide constants and Telegram credentials
- **Trade Journal**: Core logging doctype with risk management validation and psychology tracking
- **Signal Source**: Screening layer for informal tips from Telegram/Discord groups
- **Broker Summary**: Daily broker transaction summary with Excel import from Stockbit
- **Broker Summary Detail**: Child table for individual broker transaction details
- **Watchlist**: Stock watchlist with tier classification (A/B/C)

### Risk Management

- Position sizing based on fixed risk percentage
- Daily, weekly, and monthly loss limits
- Maximum portfolio exposure limits
- Per-stock exposure limits
- Consecutive loss circuit breaker
- Automatic validation before trade entry

### Telegram Integration

- Trade closure notifications
- Daily/weekly/monthly review summaries
- Intraday condition checks
- Configurable via Trading Account Settings

### Scheduled Jobs

- Intraday condition checks (every 30 min during trading hours)
- Daily review notification (16:00)
- Weekly review notification (Friday 17:00)
- Monthly circuit breaker check (1st of month 08:00)

## Installation

### Prerequisites

- Frappe Framework installed (bench)
- Python 3.8+
- MySQL/MariaDB

### Install on a Frappe Site

```bash
# Get the app
bench get-app https://github.com/silverefendy/fd_trade

# Install on your site
bench install-app fd_trade

# Build assets
bench build

# Restart bench
bench restart
```

## Configuration

### Telegram Bot Setup

1. Create a Telegram bot via @BotFather
2. Get the bot token
3. Get your chat ID (use @userinfobot)
4. Navigate to "Trading Account Settings" in FD-Trade
5. Enter the bot token (password field, masked)
6. Enter your chat ID
7. Enable Telegram notifications

### Trading Account Settings

Configure your trading parameters in "Trading Account Settings":
- Modal Total: Your total trading capital
- Risk Per Trade Percent: Risk percentage per trade (default 0.5%)
- Daily/Weekly/Monthly Loss Limits: Circuit breaker thresholds
- Max Exposure: Maximum portfolio exposure percentage
- Max Per Stock: Maximum exposure per single stock
- Max Consecutive Losses: Stop trading after N consecutive losses

## Usage

### Trade Journal

1. Create a new Trade Journal entry
2. Fill in basic information (date, ticker, setup, market regime)
3. Enter entry price and stop loss (system calculates suggested lot)
4. System validates against risk management rules
5. When trade closes, enter exit price and result
6. Mark "Followed System" to track discipline
7. Log psychological factors (FOMO, revenge, emotion, mistake, lesson)

### Broker Summary Import

1. Copy broker summary table from Stockbit web interface
2. Paste into Excel (preserves table structure)
3. Attach Excel file to Broker Summary doc
4. Click "Import from Excel" button
5. System parses fixed cell positions and imports data
6. Auto-generated insight notes based on broker flow

### Signal Source Screening

1. Create Signal Source entry for tips from Telegram/Discord
2. Fill in source details and raw message
3. Add screening notes (liquidity, technical confirmation, volume, R:R)
4. Update status (New -> Screening -> Rejected/Promoted to Watchlist)
5. Never use Signal Source directly as entry signal - always validate independently

## Dependencies

- `requests`: For Telegram Bot API
- `openpyxl`: For Excel file parsing
- `yfinance`: For stock price data (best-effort, 15-20 min delayed)

## Important Notes

- This is a personal project for IDX (Indonesia Stock Exchange) trading discipline
- This app is designed for a NEW, SEPARATE Frappe site - do not connect to existing ERPNext instances
- This is a journal/logging system only - no actual buy/sell order execution
- All data entry is manual upload or manual form input by design
- No auto-scraping of Stockbit or any broker/data websites

## License

MIT

## Author

Efendy (silverefendy)
