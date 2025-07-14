# Solana Grid Trading Bot - Testing & Trading Guide

## 📋 Table of Contents
1. [Quick Start](#quick-start)
2. [Pre-Testing Checklist](#pre-testing-checklist)
3. [Testing with Fake Money (Devnet)](#testing-with-fake-money-devnet)
4. [Testing with Real Money (Mainnet)](#testing-with-real-money-mainnet)
5. [Configuration Guide](#configuration-guide)
6. [Safety Features](#safety-features)
7. [Troubleshooting](#troubleshooting)
8. [Performance Monitoring](#performance-monitoring)

---

## 🚀 Quick Start

### Prerequisites
- Python 3.8+
- Virtual environment activated
- Dependencies installed

### Initial Setup
```bash
# Activate virtual environment
source venv/bin/activate

# Verify installation
python -c "from config import Config; print('✅ Ready to go!')"
```

---

## ✅ Pre-Testing Checklist

### 1. Environment Verification
```bash
# Check Python version
python --version  # Should be 3.8+

# Check dependencies
pip list | grep -E "(solana|solders|requests|cryptography)"

# Verify configuration
python -c "from config import Config; c = Config(); print(f'Capital: ${c.CAPITAL}, RPC: {c.RPC_URL}')"
```

### 2. Current Safe Configuration
- **Capital**: $250 (devnet testing)
- **Network**: Solana Devnet
- **Grid Levels**: 5 (automatically increases to 15 for small capital)
- **Daily Loss Limit**: 5%
- **Stop Loss**: 5%
- **Risk Per Trade**: 2%

---

## 🧪 Testing with Fake Money (Devnet)

### Phase 1: Component Testing
```bash
# Test micro-grid strategy
python test_micro_grid.py

# Test volume-weighted grids
python test_volume_weighted_grids.py

# Test core bot components
python -c "
from config import Config
from grid_trading_bot import GridTradingBot
from solana_wallet import SolanaWallet

config = Config()
wallet = SolanaWallet(config.PRIVATE_KEY, config.RPC_URL, config.WALLET_TYPE)
bot = GridTradingBot(config)
print('✅ All components working!')
"
```

### Phase 2: Strategy Testing
```bash
# Test different capital scenarios
python -c "
from config import Config
from risk_manager import RiskManager

for capital in [200, 500, 1000]:
    config = Config.get_trading_config()
    config['capital'] = capital
    rm = RiskManager(config)
    buy_prices, sell_prices = rm.get_optimal_grid_levels(100.0)
    print(f'Capital \${capital}: {len(buy_prices)} buy orders, {len(sell_prices)} sell orders')
"
```

### Phase 3: Wallet Testing
```bash
# Test wallet connection
python -c "
from solana_wallet import SolanaWallet
from config import Config

config = Config()
wallet = SolanaWallet(config.PRIVATE_KEY, config.RPC_URL, config.WALLET_TYPE)
print(f'✅ Connected to {config.RPC_URL}')
print(f'   Public key: {wallet.get_public_key()}')
print(f'   SOL balance: {wallet.get_balance()}')
"
```

### Phase 4: Mock Trading Simulation
```bash
# Run bot initialization test
python -c "
from grid_trading_bot import GridTradingBot
from config import Config

config = Config()
bot = GridTradingBot(config)
print('✅ Bot ready for trading simulation')
print(f'   Strategy: Micro-grid with {config.GRID_LEVELS} base levels')
print(f'   Capital: \${config.CAPITAL}')
print(f'   Risk per trade: {config.RISK_PER_TRADE*100}%')
"
```

---

## 💰 Testing with Real Money (Mainnet)

### ⚠️ IMPORTANT SAFETY STEPS

#### 1. Update Configuration for Mainnet
```bash
# Edit .env file
nano .env

# Change these values:
RPC_URL=https://api.mainnet-beta.solana.com
CAPITAL=50  # Start with very small amount
MAX_DAILY_LOSS=0.01  # 1% daily loss limit
STOP_LOSS_PERCENT=0.01  # 1% stop loss
RISK_PER_TRADE=0.005  # 0.5% risk per trade
```

#### 2. Fund Your Wallet
```bash
# Get your wallet address
python -c "
from solana_wallet import SolanaWallet
from config import Config

config = Config()
wallet = SolanaWallet(config.PRIVATE_KEY, config.RPC_URL, config.WALLET_TYPE)
print(f'Wallet address: {wallet.get_public_key()}')
"

# Send SOL to this address from your main wallet
# Start with $50-100 worth of SOL
```

#### 3. Pre-Flight Checks
```bash
# Verify mainnet connection
python -c "
from solana_wallet import SolanaWallet
from config import Config

config = Config()
wallet = SolanaWallet(config.PRIVATE_KEY, config.RPC_URL, config.WALLET_TYPE)
balance = wallet.get_balance()
print(f'✅ Connected to mainnet')
print(f'   SOL balance: {balance}')
print(f'   USD value: ~\${balance * 150}')  # Approximate
if balance < 0.1:
    print('❌ Insufficient balance for trading')
else:
    print('✅ Balance sufficient for testing')
"
```

#### 4. Final Safety Check
```bash
# Review all settings
python -c "
from config import Config

config = Config()
print('🔍 Final Configuration Review:')
print(f'   Network: {config.RPC_URL}')
print(f'   Capital: \${config.CAPITAL}')
print(f'   Daily Loss Limit: {config.MAX_DAILY_LOSS*100}%')
print(f'   Stop Loss: {config.STOP_LOSS_PERCENT*100}%')
print(f'   Risk Per Trade: {config.RISK_PER_TRADE*100}%')
print()
print('❓ Are you comfortable with these settings?')
print('   If not, edit .env file before proceeding')
"
```

### 5. Start Live Trading
```bash
# Start with minimal capital monitoring
python main.py --dry-run  # Final simulation test

# If dry-run looks good, start live trading
python main.py

# Monitor in another terminal
tail -f logs/trading_bot.log
```

---

## ⚙️ Configuration Guide

### Essential Settings (.env file)

#### Network Configuration
```bash
# For Testing (Devnet)
RPC_URL=https://api.devnet.solana.com

# For Live Trading (Mainnet)
RPC_URL=https://api.mainnet-beta.solana.com
```

#### Risk Management
```bash
# Conservative Settings (Recommended for beginners)
CAPITAL=50
MAX_DAILY_LOSS=0.01      # 1% daily loss limit
STOP_LOSS_PERCENT=0.01   # 1% stop loss
RISK_PER_TRADE=0.005     # 0.5% risk per trade

# Moderate Settings (For experienced traders)
CAPITAL=250
MAX_DAILY_LOSS=0.02      # 2% daily loss limit
STOP_LOSS_PERCENT=0.02   # 2% stop loss
RISK_PER_TRADE=0.01      # 1% risk per trade

# Aggressive Settings (For experts only)
CAPITAL=1000
MAX_DAILY_LOSS=0.05      # 5% daily loss limit
STOP_LOSS_PERCENT=0.05   # 5% stop loss
RISK_PER_TRADE=0.02      # 2% risk per trade
```

#### Strategy Settings
```bash
# Micro-Grid Strategy (Recommended for small capital)
MICRO_GRID_MODE=True
GRID_LEVELS=5                    # Base levels (auto-increases for small capital)
GRID_DENSITY_MULTIPLIER=2.0      # Increases grid density
SMALL_CAPITAL_THRESHOLD=1000     # Threshold for small capital optimizations
MICRO_CAPITAL_THRESHOLD=500      # Threshold for micro capital optimizations

# Volume-Weighted Grid Placement (Advanced)
VOLUME_WEIGHTED_GRIDS=True
MARKET_DEPTH_ANALYSIS=True
VOLUME_ADJUSTMENT_TOLERANCE=0.02  # 2% adjustment tolerance
```

---

## 🛡️ Safety Features

### Automatic Risk Management
- **Daily Loss Limits**: Bot stops trading if daily loss exceeds configured percentage
- **Stop Loss Protection**: Individual positions closed if loss exceeds threshold
- **Position Size Limits**: Calculated position sizes never exceed risk tolerance
- **Maximum Exposure**: Total exposure capped at 80% of capital

### Monitoring Commands
```bash
# Check current risk metrics
python -c "
from risk_manager import RiskManager
from config import Config

config = Config()
rm = RiskManager(config)
metrics = rm.get_risk_summary()
print('📊 Risk Metrics:')
for key, value in metrics.items():
    print(f'   {key}: {value}')
"

# Check system resources
python -c "
from utils import check_system_resources
resources = check_system_resources()
print('💻 System Resources:')
for key, value in resources.items():
    print(f'   {key}: {value}%')
"
```

### Emergency Stop
```bash
# Stop all trading immediately
pkill -f "python main.py"

# Or use Ctrl+C in the terminal running the bot
```

---

## 🔧 Troubleshooting

### Common Issues

#### 1. "Module not found" errors
```bash
# Solution: Ensure virtual environment is activated
source venv/bin/activate
pip install -r requirements.txt
```

#### 2. "Invalid private key format" errors
```bash
# Solution: Generate new keypair
python -c "
from solders.keypair import Keypair
import base58

keypair = Keypair()
print(f'Private key: {base58.b58encode(keypair.secret()).decode()}')
print(f'Public key: {keypair.pubkey()}')
"
# Update PRIVATE_KEY in .env file
```

#### 3. "Connection failed" errors
```bash
# Solution: Check RPC URL and network connectivity
python -c "
import requests
rpc_url = 'https://api.devnet.solana.com'
try:
    response = requests.post(rpc_url, json={'jsonrpc': '2.0', 'id': 1, 'method': 'getHealth'})
    print(f'✅ {rpc_url} is reachable')
except Exception as e:
    print(f'❌ Connection failed: {e}')
"
```

#### 4. "Insufficient balance" errors
```bash
# Solution: Fund your wallet
python -c "
from solana_wallet import SolanaWallet
from config import Config

config = Config()
wallet = SolanaWallet(config.PRIVATE_KEY, config.RPC_URL, config.WALLET_TYPE)
print(f'Wallet: {wallet.get_public_key()}')
print(f'Balance: {wallet.get_balance()} SOL')
print(f'Send SOL to this address')
"
```

### Debug Mode
```bash
# Run with debug logging
python main.py --log-level DEBUG

# Check logs
tail -f logs/trading_bot.log
```

---

## 📈 Performance Monitoring

### Real-time Monitoring
```bash
# Monitor bot performance
watch -n 5 'tail -20 logs/trading_bot.log | grep -E "(Performance|Grid|Order)"'

# Monitor system resources
watch -n 10 'python -c "from utils import check_system_resources; r = check_system_resources(); print(f\"CPU: {r[\"cpu_percent\"]}% | Memory: {r[\"memory_percent\"]}% | Disk: {r[\"disk_percent\"]}%\")"'
```

### Key Metrics to Watch
- **Win Rate**: Should be >50% for profitable trading
- **Daily P&L**: Monitor for daily loss limits
- **Grid Utilization**: Check if grid levels are being filled
- **System Resources**: Ensure CPU/memory usage is reasonable

### Performance Analysis
```bash
# Generate performance report
python -c "
from risk_manager import RiskManager
from config import Config

config = Config()
rm = RiskManager(config)
summary = rm.get_performance_summary()
print('📊 Performance Summary:')
for key, value in summary.items():
    if 'percent' in key:
        print(f'   {key}: {value:.2f}%')
    elif 'pnl' in key:
        print(f'   {key}: \${value:.2f}')
    else:
        print(f'   {key}: {value}')
"
```

---

## ⚠️ Important Reminders

### Before Starting
1. **Always start with small amounts** ($50-100)
2. **Test extensively on devnet** before mainnet
3. **Monitor continuously** during first few hours
4. **Keep your private key secure** - never share it
5. **Have an exit strategy** ready

### During Trading
1. **Monitor logs regularly** for errors or warnings
2. **Check performance metrics** every few hours
3. **Be prepared to stop** if something looks wrong
4. **Don't leave unattended** for long periods initially

### After Trading
1. **Review performance** and adjust settings if needed
2. **Backup your logs** for analysis
3. **Update your strategy** based on results
4. **Secure your profits** by withdrawing periodically

---

## 🎯 Success Tips

1. **Start Conservative**: Use small capital and tight risk limits
2. **Monitor Actively**: Don't set and forget initially
3. **Test Thoroughly**: Spend time on devnet before mainnet
4. **Keep Learning**: Analyze your results and improve
5. **Stay Disciplined**: Stick to your risk management rules

---

## 📞 Support

If you encounter issues:
1. Check the logs in `logs/trading_bot.log`
2. Review this guide thoroughly
3. Test individual components using the provided commands
4. Ensure your configuration is correct for your network

Remember: **Trading involves risk. Only trade with money you can afford to lose.**

---

*Last updated: 2025-07-14*