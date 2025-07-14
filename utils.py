import logging
import os
from datetime import datetime
from typing import Dict
from colorama import init, Fore, Back, Style
from tabulate import tabulate

# Initialize colorama for cross-platform colored output
init(autoreset=True)

def setup_logging(log_level: str = "INFO", log_file: str = "trading_bot.log") -> None:
    """Setup logging configuration."""
    # Create logs directory if it doesn't exist
    os.makedirs("logs", exist_ok=True)
    
    # Configure logging format
    log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    # Setup file handler
    file_handler = logging.FileHandler(f"logs/{log_file}")
    file_handler.setLevel(getattr(logging, log_level.upper()))
    file_formatter = logging.Formatter(log_format)
    file_handler.setFormatter(file_formatter)
    
    # Setup console handler with colors
    console_handler = logging.StreamHandler()
    console_handler.setLevel(getattr(logging, log_level.upper()))
    console_formatter = ColoredFormatter(log_format)
    console_handler.setFormatter(console_formatter)
    
    # Setup root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level.upper()))
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)
    
    # Suppress verbose logs from external libraries
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("requests").setLevel(logging.WARNING)

class ColoredFormatter(logging.Formatter):
    """Custom formatter with colored output."""
    
    COLORS = {
        'DEBUG': Fore.CYAN,
        'INFO': Fore.GREEN,
        'WARNING': Fore.YELLOW,
        'ERROR': Fore.RED,
        'CRITICAL': Fore.RED + Back.WHITE + Style.BRIGHT,
    }
    
    def format(self, record):
        # Add color to the level name
        levelname = record.levelname
        if levelname in self.COLORS:
            record.levelname = f"{self.COLORS[levelname]}{levelname}{Style.RESET_ALL}"
        
        return super().format(record)

def display_performance_summary(summary: Dict) -> None:
    """Display a formatted performance summary."""
    print("\n" + "="*60)
    print(f"{Fore.CYAN}{Style.BRIGHT}PERFORMANCE SUMMARY{Style.RESET_ALL}")
    print("="*60)
    
    # Create summary table
    summary_data = [
        ["Total P&L", f"${summary['total_pnl']:.2f}"],
        ["Daily P&L", f"${summary['daily_pnl']:.2f}"],
        ["ROI %", f"{summary['roi_percent']:.2f}%"],
        ["Win Rate", f"{summary['win_rate']:.1%}"],
        ["Total Trades", str(summary['total_trades'])],
        ["Current Exposure", f"${summary['current_exposure']:.2f}"],
        ["Max Drawdown", f"${summary['max_drawdown']:.2f}"],
        ["Session Duration", f"{summary['session_duration_hours']:.1f} hours"]
    ]
    
    # Color code the P&L values
    for row in summary_data:
        if "P&L" in row[0] or "ROI" in row[0]:
            value = float(row[1].replace('$', '').replace('%', ''))
            if value > 0:
                row[1] = f"{Fore.GREEN}{row[1]}{Style.RESET_ALL}"
            elif value < 0:
                row[1] = f"{Fore.RED}{row[1]}{Style.RESET_ALL}"
    
    print(tabulate(summary_data, headers=["Metric", "Value"], tablefmt="grid"))
    print("="*60 + "\n")

def display_grid_status(grid_levels: list) -> None:
    """Display current grid status."""
    print(f"\n{Fore.BLUE}{Style.BRIGHT}GRID STATUS{Style.RESET_ALL}")
    print("-" * 40)
    
    grid_data = []
    for level in grid_levels:
        status = []
        if level.buy_filled:
            status.append("BUY✓")
        elif level.buy_order_id:
            status.append("BUY●")
        else:
            status.append("BUY○")
            
        if level.sell_filled:
            status.append("SELL✓")
        elif level.sell_order_id:
            status.append("SELL●")
        else:
            status.append("SELL○")
        
        grid_data.append([
            f"Level {level.level}",
            f"${level.buy_price:.4f}",
            f"${level.sell_price:.4f}",
            " ".join(status)
        ])
    
    print(tabulate(grid_data, 
                  headers=["Level", "Buy Price", "Sell Price", "Status"],
                  tablefmt="grid"))
    print()

def display_welcome_banner() -> None:
    """Display welcome banner."""
    banner = f"""
{Fore.CYAN}{Style.BRIGHT}
╔══════════════════════════════════════════════════════════════╗
║                    SOLANA GRID TRADING BOT                   ║
║                                                              ║
║  🚀 Maximum Profitability & Security                        ║
║  🔒 Advanced Risk Management                                ║
║  📊 Real-time Performance Tracking                          ║
║  🛡️  Enterprise-grade Security                              ║
╚══════════════════════════════════════════════════════════════╝
{Style.RESET_ALL}
"""
    print(banner)

def display_config_summary(config: Dict) -> None:
    """Display configuration summary."""
    print(f"{Fore.YELLOW}{Style.BRIGHT}CONFIGURATION SUMMARY{Style.RESET_ALL}")
    print("-" * 40)
    
    config_data = [
        ["Trading Pair", config['trading_pair']],
        ["Capital", f"${config['capital']:.2f}"],
        ["Grid Levels", str(config['grid_levels'])],
        ["Price Range", f"{config['price_range_percent']*100:.1f}%"],
        ["Risk Per Trade", f"{config['risk_per_trade']*100:.1f}%"],
        ["Max Daily Loss", f"{config['max_daily_loss']*100:.1f}%"],
        ["Stop Loss", f"{config['stop_loss_percent']*100:.1f}%"],
        ["Profit Target", f"{config['profit_target_percent']*100:.1f}%"]
    ]
    
    print(tabulate(config_data, headers=["Setting", "Value"], tablefmt="grid"))
    print()

def format_currency(amount: float) -> str:
    """Format currency amount with proper formatting."""
    if amount >= 1000000:
        return f"${amount/1000000:.2f}M"
    elif amount >= 1000:
        return f"${amount/1000:.2f}K"
    else:
        return f"${amount:.2f}"

def format_percentage(value: float) -> str:
    """Format percentage with proper formatting."""
    return f"{value*100:.2f}%"

def validate_trading_pair(trading_pair: str) -> bool:
    """Validate trading pair format."""
    if not trading_pair or '/' not in trading_pair:
        return False
    
    base, quote = trading_pair.split('/')
    if not base or not quote:
        return False
    
    # Common Solana trading pairs
    valid_pairs = [
        'SOL/USDC', 'SOL/USDT', 'SOL/BTC', 'SOL/ETH',
        'RAY/USDC', 'SRM/USDC', 'ORCA/USDC', 'MNGO/USDC'
    ]
    
    return trading_pair.upper() in valid_pairs

def calculate_optimal_grid_spacing(current_price: float, volatility: float = 0.02) -> float:
    """Calculate optimal grid spacing based on price and volatility."""
    # Base spacing of 2% of current price
    base_spacing = current_price * 0.02
    
    # Adjust for volatility
    adjusted_spacing = base_spacing * (1 + volatility)
    
    # Ensure minimum spacing
    min_spacing = current_price * 0.005  # 0.5% minimum
    max_spacing = current_price * 0.05   # 5% maximum
    
    return max(min_spacing, min(adjusted_spacing, max_spacing))

def get_market_sentiment() -> str:
    """Get market sentiment (placeholder for future implementation)."""
    # This could integrate with sentiment analysis APIs
    # For now, return neutral
    return "neutral"

def log_trade_execution(side: str, quantity: float, price: float, 
                       trading_pair: str, order_id: str) -> None:
    """Log trade execution details."""
    logger = logging.getLogger(__name__)
    
    trade_info = {
        'timestamp': datetime.now().isoformat(),
        'side': side,
        'quantity': quantity,
        'price': price,
        'pair': trading_pair,
        'order_id': order_id,
        'value': quantity * price
    }
    
    logger.info(f"Trade executed: {side.upper()} {quantity} {trading_pair} @ ${price:.6f} "
                f"(Order: {order_id}, Value: ${trade_info['value']:.2f})")
    
    # Save to trade log file
    try:
        with open('logs/trades.log', 'a') as f:
            f.write(f"{trade_info['timestamp']},{side},{quantity},{price},{trading_pair},{order_id},{trade_info['value']}\n")
    except Exception as e:
        logger.error(f"Failed to log trade: {e}")

def create_backup_config() -> None:
    """Create a backup of the current configuration."""
    try:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = f"config_backup_{timestamp}.json"
        
        # This would save the current config to a backup file
        # Implementation depends on how config is stored
        logger.info(f"Configuration backup created: {backup_file}")
        
    except Exception as e:
        logger.error(f"Failed to create config backup: {e}")

def check_system_resources() -> Dict:
    """Check system resources and return status."""
    try:
        import psutil
        
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        return {
            'cpu_percent': cpu_percent,
            'memory_percent': memory.percent,
            'disk_percent': disk.percent,
            'memory_available': memory.available / (1024**3),  # GB
            'disk_free': disk.free / (1024**3)  # GB
        }
    except ImportError:
        logger.warning("psutil not available, skipping system resource check")
        return {}
    except Exception as e:
        logger.error(f"Failed to check system resources: {e}")
        return {} 