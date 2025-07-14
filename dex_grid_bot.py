import time
import uuid
import logging
from datetime import datetime
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass

from config import Config
from security import SecurityManager
from risk_manager import RiskManager, Position
from solana_wallet import SolanaWallet
from dex_client import DEXManager, DEXPrice
from utils import setup_logging, display_performance_summary

logger = logging.getLogger(__name__)

@dataclass
class DEXGridLevel:
    """Represents a grid level for DEX trading."""
    level: int
    buy_price: float
    sell_price: float
    buy_quote: Optional[DEXPrice] = None
    sell_quote: Optional[DEXPrice] = None
    buy_executed: bool = False
    sell_executed: bool = False
    buy_signature: Optional[str] = None
    sell_signature: Optional[str] = None

class DEXGridTradingBot:
    """Advanced grid trading bot for Solana DEXs with wallet integration."""
    
    def __init__(self, config: Config):
        """Initialize the DEX grid trading bot."""
        self.config = config
        self.security_manager = SecurityManager(config.ENCRYPTION_KEY)
        
        # Initialize wallet and DEX manager
        if config.PRIVATE_KEY:
            self.wallet = SolanaWallet(config.PRIVATE_KEY, config.RPC_URL)
            self.dex_manager = DEXManager(self.wallet)
            self.trading_mode = "DEX"
        else:
            self.wallet = None
            self.dex_manager = None
            self.trading_mode = "CEX"
        
        self.risk_manager = RiskManager(config.get_trading_config())
        
        self.grid_levels: List[DEXGridLevel] = []
        self.active_positions: Dict[str, Dict] = {}
        self.is_running = False
        self.session_start = time.time()
        
        # Performance tracking
        self.total_profit = 0.0
        self.total_trades = 0
        self.successful_trades = 0
        
        logger.info(f"DEX grid trading bot initialized in {self.trading_mode} mode")
    
    def initialize(self) -> bool:
        """Initialize the bot and validate all components."""
        try:
            logger.info("Initializing DEX grid trading bot...")
            
            # Validate configuration
            self.config.validate()
            
            if self.trading_mode == "DEX":
                # Test wallet connection
                balance = self.wallet.get_balance()
                logger.info(f"Wallet balance: {balance:.6f} SOL")
                
                # Test DEX connection
                current_price = self.dex_manager.get_market_price(self.config.TRADING_PAIR)
                if current_price:
                    logger.info(f"Current {self.config.TRADING_PAIR} price: {current_price:.6f}")
                else:
                    logger.warning("Could not fetch current price from DEX")
                
                # Initialize grid levels
                self._initialize_grid(current_price or 100.0)  # Fallback price
                
            else:
                logger.info("CEX mode - using traditional API client")
                # Initialize traditional API client for CEX
                from api_client import APIClient
                self.api_client = APIClient(self.config, self.security_manager)
                
                if not self.api_client.test_connection():
                    logger.error("Failed to connect to CEX API")
                    return False
                
                current_price = self.api_client.get_market_price(self.config.TRADING_PAIR)
                self._initialize_grid(current_price)
            
            logger.info("DEX grid trading bot initialization completed successfully")
            return True
            
        except Exception as e:
            logger.error(f"Initialization failed: {e}")
            return False
    
    def _initialize_grid(self, current_price: float):
        """Initialize grid levels around current price."""
        try:
            # Get optimal grid levels from risk manager
            buy_prices, sell_prices = self.risk_manager.get_optimal_grid_levels(current_price)
            
            self.grid_levels = []
            for i in range(self.config.GRID_LEVELS):
                grid_level = DEXGridLevel(
                    level=i + 1,
                    buy_price=buy_prices[i],
                    sell_price=sell_prices[i]
                )
                self.grid_levels.append(grid_level)
            
            logger.info(f"Initialized {len(self.grid_levels)} grid levels")
            logger.info(f"Buy prices: {[level.buy_price for level in self.grid_levels]}")
            logger.info(f"Sell prices: {[level.sell_price for level in self.grid_levels]}")
            
        except Exception as e:
            logger.error(f"Failed to initialize grid: {e}")
            raise
    
    def place_grid_orders(self, current_price: float):
        """Place initial grid orders on DEX."""
        if self.trading_mode != "DEX":
            logger.warning("Grid orders only supported in DEX mode")
            return
        
        try:
            logger.info("Placing grid orders on DEX...")
            
            # Parse trading pair
            tokens = self.config.TRADING_PAIR.split('/')
            if len(tokens) != 2:
                logger.error(f"Invalid trading pair: {self.config.TRADING_PAIR}")
                return
            
            input_token, output_token = tokens
            
            for level in self.grid_levels:
                # Calculate position size
                position_size = self.risk_manager.calculate_position_size(
                    current_price, self.config.RISK_PER_TRADE
                )
                
                if position_size <= 0:
                    logger.warning(f"Skipping level {level.level} - insufficient position size")
                    continue
                
                # Get quotes for buy and sell orders
                if not level.buy_executed:
                    try:
                        # Convert to token amount (assuming SOL as base)
                        if input_token == "SOL":
                            amount = position_size * 1e9  # Convert to lamports
                        else:
                            amount = position_size * (10 ** 6)  # Assume 6 decimals for tokens
                        
                        buy_quote = self.dex_manager.get_best_price(output_token, input_token, amount)
                        if buy_quote:
                            level.buy_quote = buy_quote
                            logger.info(f"Buy quote at level {level.level}: {buy_quote.price:.6f}")
                        else:
                            logger.warning(f"No buy quote available for level {level.level}")
                            
                    except Exception as e:
                        logger.error(f"Failed to get buy quote at level {level.level}: {e}")
                
                if not level.sell_executed:
                    try:
                        # Convert to token amount
                        if output_token == "SOL":
                            amount = position_size * 1e9  # Convert to lamports
                        else:
                            amount = position_size * (10 ** 6)  # Assume 6 decimals
                        
                        sell_quote = self.dex_manager.get_best_price(input_token, output_token, amount)
                        if sell_quote:
                            level.sell_quote = sell_quote
                            logger.info(f"Sell quote at level {level.level}: {sell_quote.price:.6f}")
                        else:
                            logger.warning(f"No sell quote available for level {level.level}")
                            
                    except Exception as e:
                        logger.error(f"Failed to get sell quote at level {level.level}: {e}")
            
            logger.info(f"Grid quotes obtained for {len([l for l in self.grid_levels if l.buy_quote or l.sell_quote])} levels")
            
        except Exception as e:
            logger.error(f"Failed to place grid orders: {e}")
            raise
    
    def execute_grid_trades(self):
        """Execute trades when market conditions are met."""
        if self.trading_mode != "DEX":
            return
        
        try:
            current_price = self.dex_manager.get_market_price(self.config.TRADING_PAIR)
            if not current_price:
                logger.warning("Could not get current market price")
                return
            
            logger.info(f"Current price: {current_price:.6f}")
            
            for level in self.grid_levels:
                # Check if buy order should be executed
                if (not level.buy_executed and 
                    level.buy_quote and 
                    current_price <= level.buy_price):
                    
                    try:
                        logger.info(f"Executing buy order at level {level.level}")
                        signature = self.dex_manager.execute_swap(level.buy_quote)
                        if signature:
                            level.buy_executed = True
                            level.buy_signature = signature
                            
                            # Add position to risk manager
                            position = Position(
                                id=signature,
                                side="buy",
                                quantity=level.buy_quote.input_amount,
                                price=level.buy_price,
                                timestamp=time.time(),
                                status="filled"
                            )
                            self.risk_manager.add_position(position)
                            
                            logger.info(f"Buy order executed: {signature}")
                            
                    except Exception as e:
                        logger.error(f"Failed to execute buy order at level {level.level}: {e}")
                
                # Check if sell order should be executed
                if (not level.sell_executed and 
                    level.sell_quote and 
                    current_price >= level.sell_price):
                    
                    try:
                        logger.info(f"Executing sell order at level {level.level}")
                        signature = self.dex_manager.execute_swap(level.sell_quote)
                        if signature:
                            level.sell_executed = True
                            level.sell_signature = signature
                            
                            # Add position to risk manager
                            position = Position(
                                id=signature,
                                side="sell",
                                quantity=level.sell_quote.input_amount,
                                price=level.sell_price,
                                timestamp=time.time(),
                                status="filled"
                            )
                            self.risk_manager.add_position(position)
                            
                            logger.info(f"Sell order executed: {signature}")
                            
                    except Exception as e:
                        logger.error(f"Failed to execute sell order at level {level.level}: {e}")
            
        except Exception as e:
            logger.error(f"Failed to execute grid trades: {e}")
    
    def manage_positions(self, current_price: float):
        """Monitor and manage open positions."""
        try:
            # Check stop loss conditions
            positions_to_close = self.risk_manager.check_stop_loss(current_price)
            for position_id in positions_to_close:
                self._close_position(position_id, "stop_loss")
            
            # Update grid levels based on market conditions
            self._update_grid_levels(current_price)
            
        except Exception as e:
            logger.error(f"Failed to manage positions: {e}")
    
    def _close_position(self, position_id: str, reason: str):
        """Close a position (placeholder for DEX implementation)."""
        try:
            logger.info(f"Closing position {position_id} due to {reason}")
            # In DEX mode, positions are typically closed by executing opposite trades
            # This would need to be implemented based on the specific DEX protocol
            
        except Exception as e:
            logger.error(f"Failed to close position {position_id}: {e}")
    
    def _update_grid_levels(self, current_price: float):
        """Update grid levels based on market conditions."""
        try:
            # Check if we need to adjust grid levels
            for level in self.grid_levels:
                # If both orders are executed, we can place new orders
                if level.buy_executed and level.sell_executed:
                    # Reset level
                    level.buy_executed = False
                    level.sell_executed = False
                    level.buy_quote = None
                    level.sell_quote = None
                    
                    # Recalculate prices based on current market
                    buy_prices, sell_prices = self.risk_manager.get_optimal_grid_levels(current_price)
                    level.buy_price = buy_prices[level.level - 1]
                    level.sell_price = sell_prices[level.level - 1]
                    
                    logger.info(f"Updated grid level {level.level}: buy={level.buy_price}, sell={level.sell_price}")
            
        except Exception as e:
            logger.error(f"Failed to update grid levels: {e}")
    
    def run(self):
        """Main execution loop for DEX grid trading."""
        try:
            logger.info("Starting DEX grid trading bot...")
            self.is_running = True
            
            # Place initial grid orders
            current_price = self.dex_manager.get_market_price(self.config.TRADING_PAIR) or 100.0
            self.place_grid_orders(current_price)
            
            # Main loop
            while self.is_running:
                try:
                    # Check if we should continue trading
                    if not self.risk_manager.should_continue_trading():
                        logger.warning("Risk limits exceeded, stopping trading")
                        break
                    
                    # Execute grid trades
                    self.execute_grid_trades()
                    
                    # Get current market price
                    current_price = self.dex_manager.get_market_price(self.config.TRADING_PAIR)
                    if current_price:
                        # Manage positions
                        self.manage_positions(current_price)
                    
                    # Display performance summary every 10 minutes
                    if int(time.time() - self.session_start) % 600 == 0:
                        self._display_summary()
                    
                    # Sleep
                    time.sleep(self.config.CHECK_INTERVAL)
                    
                except KeyboardInterrupt:
                    logger.info("Received interrupt signal, stopping bot...")
                    break
                except Exception as e:
                    logger.error(f"Error in main loop: {e}")
                    time.sleep(self.config.RETRY_DELAY)
            
            # Cleanup
            self._cleanup()
            
        except Exception as e:
            logger.error(f"Bot execution failed: {e}")
            self._cleanup()
    
    def _display_summary(self):
        """Display performance summary."""
        try:
            summary = self.risk_manager.get_performance_summary()
            display_performance_summary(summary)
        except Exception as e:
            logger.error(f"Failed to display summary: {e}")
    
    def _cleanup(self):
        """Cleanup resources."""
        try:
            logger.info("Cleaning up...")
            
            # Display final summary
            self._display_summary()
            
            self.is_running = False
            logger.info("Cleanup completed")
            
        except Exception as e:
            logger.error(f"Cleanup failed: {e}")
    
    def stop(self):
        """Stop the bot gracefully."""
        logger.info("Stopping bot...")
        self.is_running = False 