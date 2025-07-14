# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a sophisticated Solana grid trading bot designed for small capital investors ($250-$500). It's built for maximum profitability and security with enterprise-grade features, advanced risk management, and real-time performance tracking.

## Common Development Commands

### Environment Setup
```bash
# Create and activate virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run automated setup
python setup.py
```

### Configuration
```bash
# Copy configuration template
cp env.example .env
# Edit with your API credentials and settings
nano .env
```

### Running the Bot
```bash
# Test mode (no real trades)
python main.py --dry-run

# Live trading
python main.py

# With custom config
python main.py --config custom.env

# Debug mode
python main.py --log-level DEBUG
```

### Testing
```bash
# Run all tests
python test_bot.py

# Run with verbose output
python test_bot.py -v

# Test micro-grid strategy
python test_micro_grid.py
```

### Development Workflow
```bash
# Check logs
tail -f logs/trading_bot.log

# Monitor performance
watch -n 5 'tail -20 logs/trading_bot.log | grep "Performance"'
```

## Architecture Overview

### Core Components
- **main.py**: Main execution script with CLI interface and signal handling
- **grid_trading_bot.py**: Core grid trading logic with dynamic grid management
- **dex_grid_bot.py**: DEX-specific trading implementation for Solana
- **config.py**: Configuration management with validation
- **security.py**: Enterprise-grade security with HMAC-SHA256 and encryption
- **risk_manager.py**: Advanced risk management with exposure tracking
- **api_client.py**: Robust API interaction with retry logic
- **utils.py**: Utility functions for display and system monitoring
- **solana_wallet.py**: Solana wallet integration for DEX trading

### Trading Strategy
The bot implements an advanced micro-grid trading strategy with dynamic position sizing:

#### Micro-Grid Strategy (P1)
- 5-20 adaptive grid levels based on capital size (buy and sell)
- 10% price range around current price (configurable)
- Micro-grid optimization for small capital ($250-$500)
- Volatility-responsive spacing (0.5%-3% range)
- 2-3x more trading opportunities for small accounts

#### Dynamic Position Sizing (P2)
- Performance-based risk scaling (1-5% per trade range)
- Automatic profit compounding up to 2x original capital
- Small account boost: 20% larger positions for accounts under $1000
- Micro account boost: Up to 50% larger positions for accounts under $500
- Win rate-based position adjustments (0.5x-2.0x scaling)
- Dynamic exposure limits (80-90%) based on account size

### Security Features
- HMAC-SHA256 authentication for all API requests
- Fernet encryption for sensitive data storage
- IP whitelisting support
- Response validation to prevent security breaches
- Log sanitization to protect sensitive information

### Risk Management
- Daily loss limits (5% default) with automatic shutdown
- Stop-loss protection (5% default)
- Maximum exposure tracking (80% of capital)
- Win rate analysis and performance metrics
- Position size optimization for small capital

## Configuration

### Required Environment Variables
```bash
# Trading parameters
TRADING_PAIR=SOL/USDC
CAPITAL=250.0
GRID_LEVELS=5
PRICE_RANGE_PERCENT=0.10
RISK_PER_TRADE=0.02

# Micro-grid strategy
MICRO_GRID_MODE=True
ADAPTIVE_SPACING=True
MIN_GRID_SPACING=0.005
MAX_GRID_SPACING=0.03
SMALL_CAPITAL_THRESHOLD=1000
MICRO_CAPITAL_THRESHOLD=500
GRID_DENSITY_MULTIPLIER=2.0

# Dynamic position sizing (P2)
DYNAMIC_SIZING=True
MIN_RISK_PER_TRADE=0.01
MAX_RISK_PER_TRADE=0.05
PERFORMANCE_SCALING=True
COMPOUND_PROFITS=True
WIN_RATE_THRESHOLD_HIGH=0.7
WIN_RATE_THRESHOLD_LOW=0.5
RISK_SCALING_FACTOR=1.5
SMALL_ACCOUNT_BOOST=1.2

# Risk management
MAX_DAILY_LOSS=0.05
STOP_LOSS_PERCENT=0.05
PROFIT_TARGET_PERCENT=0.02

# API credentials (for centralized exchanges)
API_KEY=your_api_key_here
API_SECRET=your_api_secret_here
BASE_URL=https://api.goodcrypto.app

# Solana wallet (for DEX trading)
PRIVATE_KEY=your_private_key_here
RPC_URL=https://api.mainnet-beta.solana.com
```

### Directory Structure
```
├── main.py                 # Main execution script
├── grid_trading_bot.py     # Core trading logic
├── dex_grid_bot.py        # DEX-specific implementation
├── config.py              # Configuration management
├── security.py            # Security and authentication
├── risk_manager.py        # Risk management system
├── api_client.py          # API interaction layer
├── solana_wallet.py       # Solana wallet integration
├── utils.py               # Utility functions
├── test_bot.py            # Test suite
├── setup.py               # Automated setup script
├── requirements.txt       # Dependencies
├── env.example            # Configuration template
├── logs/                  # Log files
├── data/                  # Historical data
└── backups/               # Configuration backups
```

## Key Implementation Details

### Grid Trading Logic
- Uses dynamic grid spacing based on market volatility
- Implements adaptive position sizing for small capital optimization
- Maintains 5 grid levels with 10% price range by default
- Automatically rebalances grid when filled orders occur

### Performance Optimization
- Real-time P&L tracking with detailed analytics
- Win rate analysis for strategy adjustment
- Performance-based grid spacing modifications
- Historical data persistence for backtesting

### Error Handling
- Comprehensive error handling for API failures
- Retry logic with exponential backoff
- Graceful degradation on network issues
- System resource monitoring

## Dependencies

Core libraries used:
- **requests**: HTTP client with retry logic
- **cryptography**: Encryption and security
- **python-dotenv**: Environment variable management
- **solana**: Solana blockchain interaction
- **solders**: Solana SDK for Python
- **anchorpy**: Anchor framework integration
- **colorama**: Colored console output
- **tabulate**: Formatted table display
- **schedule**: Task scheduling

## Security Considerations

- Never commit `.env` files to version control
- Use dedicated API keys with limited permissions
- Enable IP restrictions on exchange accounts
- Regularly rotate API keys
- Monitor logs for unusual activity
- Start with small amounts ($100-$200) for testing

## Troubleshooting

### Common Issues
1. **API Connection Failed**: Check credentials and network connectivity
2. **Insufficient Balance**: Verify account balance and minimum order requirements  
3. **Rate Limiting**: Increase CHECK_INTERVAL or reduce API call frequency
4. **Test Failures**: Ensure .env file is configured before running tests

### Debug Commands
```bash
# Enable debug logging
python main.py --log-level DEBUG

# Check system resources
python -c "from utils import check_system_resources; check_system_resources()"

# Validate configuration
python -c "from config import Config; c = Config(); print('Config valid')"
```

## Performance Monitoring

The bot provides real-time performance tracking through:
- Colored console output with performance summaries
- Detailed logging with trade execution history
- Grid status visualization
- System resource monitoring
- Session performance metrics