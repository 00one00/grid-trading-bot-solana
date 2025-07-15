# Network Switching Guide
## Comprehensive Documentation for Devnet/Mainnet Testing

### Overview

The Solana Grid Trading Bot includes a sophisticated network switching system that makes it easy to test on devnet (safe, free) before deploying to mainnet (real money). This guide covers everything you need to know about using this system effectively.

### Quick Start

1. **Switch to devnet for testing**:
   ```bash
   python network_switch.py  # Select option 1
   python test_devnet.py     # Run safe tests
   ```

2. **Switch to mainnet when ready**:
   ```bash
   python network_switch.py  # Select option 2 (with safety prompts)
   python test_mainnet.py    # Run with real money (caution!)
   ```

### Network Switching Utility (`network_switch.py`)

This interactive utility provides a safe way to switch between networks with appropriate safety checks.

#### Features
- **Interactive Menu**: Easy-to-use command-line interface
- **Safety Confirmations**: Multiple prompts for mainnet switching
- **Configuration Validation**: Tests configuration after changes
- **Automatic Defaults**: Sets appropriate defaults for each network

#### Usage Example
```bash
$ python network_switch.py

🔄 SOLANA GRID BOT - NETWORK SWITCH UTILITY
============================================================
This utility helps you switch between devnet and mainnet
============================================================

📋 CURRENT CONFIGURATION
========================================
Network: devnet
RPC URL: https://api.devnet.solana.com (auto)
Capital: 0.1 SOL (auto)

OPTIONS:
1. Switch to devnet (safe testing)
2. Switch to mainnet (real trading)
3. Test current configuration
4. Exit

Select option (1-4): 
```

#### Configuration Changes Made

When switching networks, the utility updates your `.env` file:

**Devnet Switch**:
- Sets `NETWORK=devnet`
- Clears `RPC_URL` (uses auto-selection)
- Clears `CAPITAL` (uses auto-selection: 0.1 SOL)

**Mainnet Switch**:
- Sets `NETWORK=mainnet`
- Clears `RPC_URL` (uses auto-selection)
- Optionally sets custom `CAPITAL` amount
- Requires multiple safety confirmations

### Network-Specific Test Scripts

#### Devnet Testing (`test_devnet.py`)

**Purpose**: Safe testing with free devnet SOL
**Risk Level**: None (devnet SOL has no value)

**Features**:
- Automatic devnet environment setup
- Free SOL faucet reminders
- Comprehensive system validation
- Optional real transaction testing

**Test Sequence**:
1. Environment setup validation
2. Configuration loading test
3. Wallet connection verification
4. Jupiter API integration test
5. Optional live transaction test

**Example Output**:
```bash
$ python test_devnet.py

🧪 SOLANA GRID BOT - DEVNET TESTING
============================================================
This script tests all functionality on Solana devnet
Safe for testing - uses devnet SOL (no real value)
============================================================

🏗️  SETTING UP DEVNET ENVIRONMENT
==================================================
  ✅ Network: devnet
  ✅ Capital: 0.05 SOL
  ✅ RPC URL: https://api.devnet.solana.com

⚙️  TESTING DEVNET CONFIGURATION
==================================================
  ✅ Network: devnet
  ✅ Is Devnet: True
  ✅ RPC URL: https://api.devnet.solana.com
  ✅ Capital: 10.0 SOL
  ✅ Explorer: https://explorer.solana.com/tx/{signature}?cluster=devnet

💰 TESTING DEVNET WALLET CONNECTION
==================================================
  ✅ Wallet: AcoVbiro...
  ✅ Balance: 0.5 SOL

🔄 TESTING JUPITER DEVNET INTEGRATION
==================================================
  ✅ Quote successful
  ✅ Input: 5000000 lamports
  ✅ Output: 812584 USDC units

🎯 ALL DEVNET TESTS PASSED!
==================================================
Ready for devnet trading tests.

❓ Run devnet trade test? (y/N): 
```

#### Mainnet Testing (`test_mainnet.py`)

**Purpose**: Pre-production validation with real money
**Risk Level**: HIGH (uses real SOL and real money)

**Safety Features**:
- **Multiple Confirmations**: Several safety prompts required
- **Capital Validation**: Warnings for high amounts
- **Balance Checks**: Ensures sufficient funds for trading
- **Price Validation**: Sanity checks on market prices
- **Final Confirmation**: Requires typing "EXECUTE MAINNET"

**Safety Checklist**:
The script enforces completion of these items:
- ✅ Devnet testing completed successfully
- ✅ Private key is secure and backed up
- ✅ Starting with small test amount ($50-$100)
- ✅ Hardware wallet recommended for large amounts
- ✅ Emergency stop procedure understood
- ✅ Risk management limits configured

**Example Safety Prompts**:
```bash
🚨 MAINNET TRADE CONFIRMATION
============================================================
⚠️  You are about to execute REAL trades on Solana mainnet
⚠️  This involves REAL money and REAL risk
============================================================

1. I understand this executes real trades with real money
   Confirm (y/N): y

2. I have tested thoroughly on devnet first
   Confirm (y/N): y

3. I am starting with a small amount I can afford to lose
   Confirm (y/N): y

4. I understand the risks of automated trading
   Confirm (y/N): y

🔴 FINAL CONFIRMATION
Type 'EXECUTE MAINNET' to proceed: EXECUTE MAINNET
```

### Configuration System

#### Network-Aware Configuration

The `config.py` file automatically adjusts settings based on the `NETWORK` environment variable:

```python
class Config:
    # Network Configuration
    NETWORK = os.getenv('NETWORK', 'devnet').lower()
    
    @property
    def RPC_URL(self):
        """Get RPC URL based on network selection."""
        custom_rpc = os.getenv('RPC_URL')
        if custom_rpc:
            return custom_rpc
        return self.DEVNET_RPC_URL if self.NETWORK == 'devnet' else self.MAINNET_RPC_URL
    
    @property
    def CAPITAL(self):
        """Get capital based on network selection."""
        custom_capital = os.getenv('CAPITAL')
        if custom_capital:
            return float(custom_capital)
        return self.DEVNET_CAPITAL if self.NETWORK == 'devnet' else self.MAINNET_CAPITAL
```

#### Environment File (`.env`) Structure

Your `.env` file should include these network settings:

```bash
# Network Configuration
NETWORK=devnet  # or 'mainnet'

# RPC URLs (automatically selected based on NETWORK)
DEVNET_RPC_URL=https://api.devnet.solana.com
MAINNET_RPC_URL=https://api.mainnet-beta.solana.com
# Custom RPC override (optional)
# RPC_URL=https://your-custom-rpc-url.com

# Capital Configuration (network-specific)
DEVNET_CAPITAL=0.1
MAINNET_CAPITAL=250.0
# Capital override (optional)
# CAPITAL=100.0

# Other settings...
WALLET_TYPE=software
PRIVATE_KEY=your_private_key_here
```

### Diagnostic Tools

#### Signature Verification Diagnostic (`diagnose_signature_issue.py`)

**Purpose**: Troubleshoot transaction signing issues
**Usage**: Run when experiencing transaction failures

**Test Sequence**:
1. Environment setup validation
2. Wallet initialization test
3. RPC connection verification
4. Jupiter API quote test
5. Transaction creation test
6. Transaction parsing test
7. Transaction signing test
8. Transaction simulation test

**Example Output**:
```bash
$ python diagnose_signature_issue.py

🚀 SIGNATURE VERIFICATION DIAGNOSTIC
============================================================
✅ Environment setup
✅ Wallet initialization
✅ RPC connection
✅ Jupiter quote
✅ Transaction creation
✅ Transaction parsing
✅ Transaction signing
⚠️  Simulation error: IncorrectProgramId (devnet limitation)
```

### Common Issues and Solutions

#### Issue: "TransactionSignatureVerificationFailure"
**Solution**: 
1. Run diagnostic: `python diagnose_signature_issue.py`
2. Check network setting matches wallet funding
3. Verify sufficient SOL for transaction fees

#### Issue: "IncorrectProgramId" in simulation
**Solution**: This is normal on devnet - some program IDs don't exist on devnet
- Expected behavior for devnet testing
- Transaction will work on mainnet

#### Issue: "Custom RPC URL showing as custom"
**Solution**: Clear custom RPC to use network-based selection:
```bash
# In .env file, comment out or remove:
# RPC_URL=https://custom-url.com
```

#### Issue: "Capital not switching correctly"
**Solution**: Clear custom capital override:
```bash
# In .env file, comment out or remove:
# CAPITAL=100.0
```

### Best Practices

#### Testing Workflow
1. **Start with devnet**: Always test thoroughly on devnet first
2. **Get devnet SOL**: Use faucet at https://faucet.solana.com/
3. **Test all features**: Run complete test suite on devnet
4. **Start small on mainnet**: Begin with $50-$100 for initial mainnet testing
5. **Monitor closely**: Watch logs and transactions carefully

#### Security Recommendations
1. **Hardware wallets**: Use for production mainnet trading
2. **Backup keys**: Secure backup of all private keys
3. **Start small**: Never risk more than you can afford to lose
4. **Emergency stops**: Know how to halt trading immediately
5. **Regular monitoring**: Check bot performance frequently

#### Configuration Management
1. **Use network switching utility**: Safer than manual .env editing
2. **Test configuration**: Always run test scripts after switching
3. **Keep backups**: Backup working .env configurations
4. **Document changes**: Note any custom settings you use

### Integration with Main Bot

The network switching system integrates seamlessly with the main trading bot:

```bash
# The bot automatically uses current network setting
python main.py

# Override specific settings if needed
python main.py --capital 50  # Custom capital
python main.py --dry-run     # Simulation mode
```

### Advanced Usage

#### Custom RPC Endpoints
```bash
# Set custom RPC in .env
RPC_URL=https://your-premium-rpc.com

# Or use environment variable
export RPC_URL=https://your-premium-rpc.com
python main.py
```

#### Network-Specific Scripts
```bash
# Force devnet regardless of .env setting
NETWORK=devnet python main.py

# Force mainnet regardless of .env setting  
NETWORK=mainnet python main.py
```

#### Batch Testing
```bash
# Test both networks sequentially
python network_switch.py  # Switch to devnet
python test_devnet.py

python network_switch.py  # Switch to mainnet  
python test_mainnet.py
```

### Troubleshooting Commands

```bash
# Check current configuration
python network_switch.py  # Select option 3

# Comprehensive diagnostic
python diagnose_signature_issue.py

# Test specific network
python test_devnet.py    # Devnet testing
python test_mainnet.py   # Mainnet testing

# View current settings
python -c "from config import Config; c=Config(); print(f'Network: {c.NETWORK}, RPC: {c.RPC_URL}, Capital: {c.CAPITAL}')"
```

This network switching system provides a safe, comprehensive way to test and deploy your Solana trading bot across different networks while maintaining appropriate safety measures for each environment.