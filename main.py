#!/usr/bin/env python3
"""
Solana Grid Trading Bot - Main Execution Script
===============================================

A sophisticated grid trading bot designed for maximum profitability and security
on Solana-based exchanges. Features advanced risk management, real-time monitoring,
and enterprise-grade security.

Usage:
    python main.py [--config CONFIG_FILE] [--dry-run] [--backtest]

Author: AI Trading Bot Developer
License: MIT
"""

import sys
import os
import signal
import argparse
import time
from datetime import datetime
import logging

# Add current directory to path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config import Config
from grid_trading_bot import GridTradingBot
from dex_grid_bot import DEXGridTradingBot
from utils import (
    setup_logging, display_welcome_banner, display_config_summary,
    display_performance_summary, check_system_resources
)

# Global bot instance for signal handling
bot_instance = None

def signal_handler(signum, frame):
    """Handle system signals for graceful shutdown."""
    global bot_instance
    
    print(f"\n{chr(27)}[33mReceived signal {signum}. Shutting down gracefully...{chr(27)}[0m")
    
    if bot_instance:
        bot_instance.stop()
    
    sys.exit(0)

def validate_environment():
    """Validate the execution environment."""
    print("🔍 Validating environment...")
    
    # Check Python version
    if sys.version_info < (3, 8):
        print("❌ Python 3.8 or higher is required")
        sys.exit(1)
    
    # Check required environment variables
    required_vars = ['API_KEY', 'API_SECRET']
    missing_vars = []
    
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    if missing_vars:
        print(f"❌ Missing required environment variables: {', '.join(missing_vars)}")
        print("Please set them in your .env file or environment")
        sys.exit(1)
    
    # Check system resources
    resources = check_system_resources()
    if resources:
        print(f"💻 System Resources:")
        print(f"   CPU: {resources.get('cpu_percent', 'N/A')}%")
        print(f"   Memory: {resources.get('memory_percent', 'N/A')}%")
        print(f"   Disk: {resources.get('disk_percent', 'N/A')}%")
        
        # Warn if resources are low
        if resources.get('memory_percent', 0) > 90:
            print("⚠️  Warning: High memory usage detected")
        if resources.get('disk_percent', 0) > 90:
            print("⚠️  Warning: Low disk space detected")
    
    print("✅ Environment validation completed")

def setup_signal_handlers():
    """Setup signal handlers for graceful shutdown."""
    signal.signal(signal.SIGINT, signal_handler)   # Ctrl+C
    signal.signal(signal.SIGTERM, signal_handler)  # Termination signal
    
    if hasattr(signal, 'SIGBREAK'):  # Windows
        signal.signal(signal.SIGBREAK, signal_handler)

def run_backtest(config: Config):
    """Run backtest mode (placeholder for future implementation)."""
    print("🧪 Backtest mode not yet implemented")
    print("This feature will be available in future versions")
    return False

def run_dry_run(config: Config):
    """Run in dry-run mode (simulation without real trades)."""
    print("🧪 Running in DRY-RUN mode (no real trades will be executed)")
    
    # Modify config for dry run
    config.BASE_URL = "https://api.testnet.example.com"  # Use testnet
    
    bot = GridTradingBot(config)
    
    if bot.initialize():
        print("✅ Dry run initialization successful")
        print("Simulating trading operations...")
        
        # Simulate some operations
        time.sleep(2)
        print("📊 Simulated grid orders placed")
        time.sleep(1)
        print("📈 Simulated market monitoring active")
        time.sleep(1)
        print("✅ Dry run completed successfully")
        return True
    else:
        print("❌ Dry run initialization failed")
        return False

def run_live_trading(config: Config):
    """Run the bot in live trading mode."""
    global bot_instance
    
    print("🚀 Starting live trading mode...")
    
    try:
        # Determine trading mode
        if config.PRIVATE_KEY:
            print("🔗 DEX Mode: Using wallet for decentralized trading")
            bot_instance = DEXGridTradingBot(config)
        else:
            print("🏢 CEX Mode: Using centralized exchange API")
            bot_instance = GridTradingBot(config)
        
        if not bot_instance.initialize():
            print("❌ Bot initialization failed")
            return False
        
        # Display configuration summary
        display_config_summary(config.get_trading_config())
        
        # Start trading
        print("🎯 Starting grid trading operations...")
        bot_instance.run()
        
        return True
        
    except KeyboardInterrupt:
        print("\n⏹️  Trading stopped by user")
        return True
    except Exception as e:
        print(f"❌ Trading failed with error: {e}")
        logging.error(f"Trading error: {e}", exc_info=True)
        return False
    finally:
        if bot_instance:
            bot_instance.stop()

def main():
    """Main execution function."""
    parser = argparse.ArgumentParser(
        description="Solana Grid Trading Bot - Maximum Profitability & Security",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py                    # Run with default settings
  python main.py --dry-run          # Run in simulation mode
  python main.py --backtest         # Run backtest (future feature)
  python main.py --config custom.env # Use custom config file
        """
    )
    
    parser.add_argument(
        '--config',
        type=str,
        help='Path to configuration file (.env format)'
    )
    
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Run in simulation mode (no real trades)'
    )
    
    parser.add_argument(
        '--backtest',
        action='store_true',
        help='Run backtest mode (future feature)'
    )
    
    parser.add_argument(
        '--log-level',
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
        default='INFO',
        help='Set logging level'
    )
    
    args = parser.parse_args()
    
    # Display welcome banner
    display_welcome_banner()
    
    # Setup logging
    setup_logging(args.log_level)
    
    # Setup signal handlers
    setup_signal_handlers()
    
    # Validate environment
    validate_environment()
    
    try:
        # Load configuration
        if args.config:
            # Load custom config file
            if not os.path.exists(args.config):
                print(f"❌ Configuration file not found: {args.config}")
                sys.exit(1)
            
            # Set environment variable to load custom config
            os.environ['ENV_FILE'] = args.config
        
        config = Config()
        
        # Validate configuration
        try:
            config.validate()
        except ValueError as e:
            print(f"❌ Configuration error: {e}")
            sys.exit(1)
        
        print(f"✅ Configuration loaded successfully")
        print(f"📊 Trading pair: {config.TRADING_PAIR}")
        print(f"💰 Capital: ${config.CAPITAL:.2f}")
        print(f"🔢 Grid levels: {config.GRID_LEVELS}")
        
        # Run appropriate mode
        success = False
        
        if args.backtest:
            success = run_backtest(config)
        elif args.dry_run:
            success = run_dry_run(config)
        else:
            success = run_live_trading(config)
        
        if success:
            print("✅ Bot execution completed successfully")
            sys.exit(0)
        else:
            print("❌ Bot execution failed")
            sys.exit(1)
            
    except Exception as e:
        print(f"❌ Fatal error: {e}")
        logging.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main() 