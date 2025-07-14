import os
from typing import Dict, Any
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class Config:
    """Configuration class for the grid trading bot."""
    
    # Wallet Configuration (for DEX trading)
    WALLET_TYPE = os.getenv('WALLET_TYPE', 'software')  # 'software', 'ledger', 'trezor'
    PRIVATE_KEY = os.getenv('PRIVATE_KEY', '') if os.getenv('WALLET_TYPE', 'software') == 'software' else None
    HARDWARE_DERIVATION_PATH = os.getenv('HARDWARE_DERIVATION_PATH', "44'/501'/0'/0'")
    RPC_URL = os.getenv('RPC_URL', 'https://api.mainnet-beta.solana.com')
    
    # API Configuration (for centralized exchanges - optional)
    API_KEY = os.getenv('API_KEY', '')
    API_SECRET = os.getenv('API_SECRET', '')
    BASE_URL = os.getenv('BASE_URL', 'https://api.goodcrypto.app')
    
    # Trading Parameters
    TRADING_PAIR = os.getenv('TRADING_PAIR', 'SOL/USDC')
    CAPITAL = float(os.getenv('CAPITAL', '250.0'))
    GRID_LEVELS = int(os.getenv('GRID_LEVELS', '5'))
    PRICE_RANGE_PERCENT = float(os.getenv('PRICE_RANGE_PERCENT', '0.10'))
    RISK_PER_TRADE = float(os.getenv('RISK_PER_TRADE', '0.02'))
    
    # Micro-Grid Strategy Configuration
    MICRO_GRID_MODE = bool(os.getenv('MICRO_GRID_MODE', 'True'))
    ADAPTIVE_SPACING = bool(os.getenv('ADAPTIVE_SPACING', 'True'))
    MIN_GRID_SPACING = float(os.getenv('MIN_GRID_SPACING', '0.005'))  # 0.5%
    MAX_GRID_SPACING = float(os.getenv('MAX_GRID_SPACING', '0.03'))   # 3%
    VOLATILITY_LOOKBACK = int(os.getenv('VOLATILITY_LOOKBACK', '24'))  # hours
    SMALL_CAPITAL_THRESHOLD = float(os.getenv('SMALL_CAPITAL_THRESHOLD', '1000'))
    MICRO_CAPITAL_THRESHOLD = float(os.getenv('MICRO_CAPITAL_THRESHOLD', '500'))
    GRID_DENSITY_MULTIPLIER = float(os.getenv('GRID_DENSITY_MULTIPLIER', '2.0'))
    
    # Risk Management
    MAX_DAILY_LOSS = float(os.getenv('MAX_DAILY_LOSS', '0.05'))  # 5% max daily loss
    STOP_LOSS_PERCENT = float(os.getenv('STOP_LOSS_PERCENT', '0.05'))  # 5% stop loss
    PROFIT_TARGET_PERCENT = float(os.getenv('PROFIT_TARGET_PERCENT', '0.02'))  # 2% profit target
    
    # Dynamic Position Sizing Configuration
    DYNAMIC_SIZING = bool(os.getenv('DYNAMIC_SIZING', 'True'))
    MIN_RISK_PER_TRADE = float(os.getenv('MIN_RISK_PER_TRADE', '0.01'))  # 1%
    MAX_RISK_PER_TRADE = float(os.getenv('MAX_RISK_PER_TRADE', '0.05'))  # 5%
    PERFORMANCE_SCALING = bool(os.getenv('PERFORMANCE_SCALING', 'True'))
    COMPOUND_PROFITS = bool(os.getenv('COMPOUND_PROFITS', 'True'))
    WIN_RATE_THRESHOLD_HIGH = float(os.getenv('WIN_RATE_THRESHOLD_HIGH', '0.7'))
    WIN_RATE_THRESHOLD_LOW = float(os.getenv('WIN_RATE_THRESHOLD_LOW', '0.5'))
    RISK_SCALING_FACTOR = float(os.getenv('RISK_SCALING_FACTOR', '1.5'))
    SMALL_ACCOUNT_BOOST = float(os.getenv('SMALL_ACCOUNT_BOOST', '1.2'))
    
    # Performance Settings
    CHECK_INTERVAL = int(os.getenv('CHECK_INTERVAL', '60'))  # seconds
    RETRY_DELAY = int(os.getenv('RETRY_DELAY', '300'))  # seconds
    MAX_RETRIES = int(os.getenv('MAX_RETRIES', '3'))
    
    # Logging
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    LOG_FILE = os.getenv('LOG_FILE', 'trading_bot.log')
    
    # Security
    IP_WHITELIST = os.getenv('IP_WHITELIST', '').split(',') if os.getenv('IP_WHITELIST') else []
    ENCRYPTION_KEY = os.getenv('ENCRYPTION_KEY', '')
    
    @classmethod
    def validate(cls) -> bool:
        """Validate configuration settings."""
        # Check for either wallet or API configuration
        if cls.WALLET_TYPE == 'software':
            if not cls.PRIVATE_KEY and (not cls.API_KEY or not cls.API_SECRET):
                raise ValueError("Either PRIVATE_KEY (for DEX) or API_KEY/API_SECRET (for CEX) must be set")
        elif cls.WALLET_TYPE in ['ledger', 'trezor']:
            if not cls.HARDWARE_DERIVATION_PATH:
                raise ValueError("HARDWARE_DERIVATION_PATH must be set for hardware wallets")
        else:
            raise ValueError("WALLET_TYPE must be 'software', 'ledger', or 'trezor'")
        
        if cls.CAPITAL <= 0:
            raise ValueError("CAPITAL must be greater than 0")
        
        if cls.GRID_LEVELS < 2:
            raise ValueError("GRID_LEVELS must be at least 2")
        
        if cls.RISK_PER_TRADE <= 0 or cls.RISK_PER_TRADE > 0.1:
            raise ValueError("RISK_PER_TRADE must be between 0 and 0.1 (10%)")
        
        return True
    
    @classmethod
    def get_trading_config(cls) -> Dict[str, Any]:
        """Get trading configuration as dictionary."""
        return {
            'trading_pair': cls.TRADING_PAIR,
            'capital': cls.CAPITAL,
            'grid_levels': cls.GRID_LEVELS,
            'price_range_percent': cls.PRICE_RANGE_PERCENT,
            'risk_per_trade': cls.RISK_PER_TRADE,
            'max_daily_loss': cls.MAX_DAILY_LOSS,
            'stop_loss_percent': cls.STOP_LOSS_PERCENT,
            'profit_target_percent': cls.PROFIT_TARGET_PERCENT,
            'micro_grid_mode': cls.MICRO_GRID_MODE,
            'adaptive_spacing': cls.ADAPTIVE_SPACING,
            'min_grid_spacing': cls.MIN_GRID_SPACING,
            'max_grid_spacing': cls.MAX_GRID_SPACING,
            'volatility_lookback': cls.VOLATILITY_LOOKBACK,
            'small_capital_threshold': cls.SMALL_CAPITAL_THRESHOLD,
            'micro_capital_threshold': cls.MICRO_CAPITAL_THRESHOLD,
            'grid_density_multiplier': cls.GRID_DENSITY_MULTIPLIER,
            'dynamic_sizing': cls.DYNAMIC_SIZING,
            'min_risk_per_trade': cls.MIN_RISK_PER_TRADE,
            'max_risk_per_trade': cls.MAX_RISK_PER_TRADE,
            'performance_scaling': cls.PERFORMANCE_SCALING,
            'compound_profits': cls.COMPOUND_PROFITS,
            'win_rate_threshold_high': cls.WIN_RATE_THRESHOLD_HIGH,
            'win_rate_threshold_low': cls.WIN_RATE_THRESHOLD_LOW,
            'risk_scaling_factor': cls.RISK_SCALING_FACTOR,
            'small_account_boost': cls.SMALL_ACCOUNT_BOOST
        } 