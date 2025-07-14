import time
import uuid
import logging
import schedule
from datetime import datetime
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass

from config import Config
from security import SecurityManager
from risk_manager import RiskManager, Position
from api_client import APIClient
from utils import setup_logging, display_performance_summary

logger = logging.getLogger(__name__)

@dataclass
class GridLevel:
    """Represents a grid level with buy/sell orders."""
    level: int
    buy_price: float
    sell_price: float
    buy_order_id: Optional[str] = None
    sell_order_id: Optional[str] = None
    buy_filled: bool = False
    sell_filled: bool = False

class GridTradingBot:
    """Advanced grid trading bot with maximum profitability and security."""
    
    def __init__(self, config: Config):
        """Initialize the grid trading bot."""
        self.config = config
        self.security_manager = SecurityManager(config.ENCRYPTION_KEY)
        self.api_client = APIClient(config, self.security_manager)
        self.risk_manager = RiskManager(config.get_trading_config())
        
        self.grid_levels: List[GridLevel] = []
        self.active_orders: Dict[str, Dict] = {}
        self.is_running = False
        self.session_start = time.time()
        
        # Performance tracking
        self.total_profit = 0.0
        self.total_trades = 0
        self.successful_trades = 0
        
        logger.info("Grid trading bot initialized")
    
    def initialize(self) -> bool:
        """Initialize the bot and validate all components."""
        try:
            logger.info("Initializing grid trading bot...")
            
            # Validate configuration
            self.config.validate()
            
            # Test API connection
            if not self.api_client.test_connection():
                logger.error("Failed to connect to API")
                return False
            
            # Validate IP if whitelist is configured
            if not self.security_manager.validate_ip(self.config.IP_WHITELIST):
                logger.error("IP not in whitelist")
                return False
            
            # Get initial account balance
            balances = self.api_client.get_account_balance()
            logger.info(f"Account balances: {balances}")
            
            # Get current market price
            current_price = self.api_client.get_market_price(self.config.TRADING_PAIR)
            logger.info(f"Current {self.config.TRADING_PAIR} price: {current_price:.6f}")
            
            # Initialize grid levels
            self._initialize_grid(current_price)
            
            logger.info("Grid trading bot initialization completed successfully")
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
                grid_level = GridLevel(
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
        """Place initial grid orders."""
        try:
            logger.info("Placing grid orders...")
            
            for level in self.grid_levels:
                # Calculate position size
                position_size = self.risk_manager.calculate_position_size(
                    current_price, self.config.RISK_PER_TRADE
                )
                
                if position_size <= 0:
                    logger.warning(f"Skipping level {level.level} - insufficient position size")
                    continue
                
                # Place buy order
                if not level.buy_order_id and not level.buy_filled:
                    try:
                        buy_order = self.api_client.place_order(
                            self.config.TRADING_PAIR,
                            "buy",
                            "limit",
                            position_size,
                            level.buy_price
                        )
                        level.buy_order_id = buy_order.get('id')
                        self.active_orders[level.buy_order_id] = buy_order
                        
                        # Add position to risk manager
                        position = Position(
                            id=level.buy_order_id,
                            side="buy",
                            quantity=position_size,
                            price=level.buy_price,
                            timestamp=time.time(),
                            status="open"
                        )
                        self.risk_manager.add_position(position)
                        
                        logger.info(f"Placed buy order at level {level.level}: {position_size} @ {level.buy_price}")
                        
                    except Exception as e:
                        logger.error(f"Failed to place buy order at level {level.level}: {e}")
                
                # Place sell order
                if not level.sell_order_id and not level.sell_filled:
                    try:
                        sell_order = self.api_client.place_order(
                            self.config.TRADING_PAIR,
                            "sell",
                            "limit",
                            position_size,
                            level.sell_price
                        )
                        level.sell_order_id = sell_order.get('id')
                        self.active_orders[level.sell_order_id] = sell_order
                        
                        # Add position to risk manager
                        position = Position(
                            id=level.sell_order_id,
                            side="sell",
                            quantity=position_size,
                            price=level.sell_price,
                            timestamp=time.time(),
                            status="open"
                        )
                        self.risk_manager.add_position(position)
                        
                        logger.info(f"Placed sell order at level {level.level}: {position_size} @ {level.sell_price}")
                        
                    except Exception as e:
                        logger.error(f"Failed to place sell order at level {level.level}: {e}")
            
            logger.info(f"Grid orders placed. Active orders: {len(self.active_orders)}")
            
        except Exception as e:
            logger.error(f"Failed to place grid orders: {e}")
            raise
    
    def manage_positions(self, current_price: float):
        """Monitor and manage open positions."""
        try:
            # Check for filled orders
            open_orders = self.api_client.get_open_orders(self.config.TRADING_PAIR)
            filled_orders = []
            
            for order_id in list(self.active_orders.keys()):
                order_found = False
                for open_order in open_orders:
                    if open_order.get('id') == order_id:
                        order_found = True
                        break
                
                if not order_found:
                    # Order might be filled, check status
                    try:
                        order_status = self.api_client.get_order_status(order_id)
                        if order_status.get('status') == 'filled':
                            filled_orders.append(order_status)
                            self._handle_filled_order(order_status)
                    except Exception as e:
                        logger.error(f"Failed to check order status for {order_id}: {e}")
            
            # Check stop loss conditions
            positions_to_close = self.risk_manager.check_stop_loss(current_price)
            for position_id in positions_to_close:
                self._close_position(position_id, "stop_loss")
            
            # Update grid levels based on filled orders
            self._update_grid_levels()
            
        except Exception as e:
            logger.error(f"Failed to manage positions: {e}")
    
    def _handle_filled_order(self, order_data: Dict):
        """Handle a filled order and place corresponding order."""
        try:
            order_id = order_data.get('id')
            side = order_data.get('side')
            quantity = float(order_data.get('quantity', 0))
            fill_price = float(order_data.get('price', 0))
            
            # Update risk manager
            self.risk_manager.update_position(order_id, 'filled', fill_price)
            
            # Remove from active orders
            if order_id in self.active_orders:
                del self.active_orders[order_id]
            
            # Update grid level
            for level in self.grid_levels:
                if level.buy_order_id == order_id:
                    level.buy_filled = True
                    level.buy_order_id = None
                    self._place_corresponding_sell_order(level, quantity, fill_price)
                    break
                elif level.sell_order_id == order_id:
                    level.sell_filled = True
                    level.sell_order_id = None
                    self._place_corresponding_buy_order(level, quantity, fill_price)
                    break
            
            logger.info(f"Handled filled {side} order: {quantity} @ {fill_price}")
            
        except Exception as e:
            logger.error(f"Failed to handle filled order: {e}")
    
    def _place_corresponding_sell_order(self, level: GridLevel, quantity: float, buy_price: float):
        """Place a sell order after a buy order is filled."""
        try:
            # Calculate sell price with profit target
            sell_price = buy_price * (1 + self.config.PROFIT_TARGET_PERCENT)
            
            sell_order = self.api_client.place_order(
                self.config.TRADING_PAIR,
                "sell",
                "limit",
                quantity,
                sell_price
            )
            
            level.sell_order_id = sell_order.get('id')
            self.active_orders[level.sell_order_id] = sell_order
            
            # Add to risk manager
            position = Position(
                id=level.sell_order_id,
                side="sell",
                quantity=quantity,
                price=sell_price,
                timestamp=time.time(),
                status="open"
            )
            self.risk_manager.add_position(position)
            
            logger.info(f"Placed corresponding sell order: {quantity} @ {sell_price}")
            
        except Exception as e:
            logger.error(f"Failed to place corresponding sell order: {e}")
    
    def _place_corresponding_buy_order(self, level: GridLevel, quantity: float, sell_price: float):
        """Place a buy order after a sell order is filled."""
        try:
            # Calculate buy price with profit target
            buy_price = sell_price * (1 - self.config.PROFIT_TARGET_PERCENT)
            
            buy_order = self.api_client.place_order(
                self.config.TRADING_PAIR,
                "buy",
                "limit",
                quantity,
                buy_price
            )
            
            level.buy_order_id = buy_order.get('id')
            self.active_orders[level.buy_order_id] = buy_order
            
            # Add to risk manager
            position = Position(
                id=level.buy_order_id,
                side="buy",
                quantity=quantity,
                price=buy_price,
                timestamp=time.time(),
                status="open"
            )
            self.risk_manager.add_position(position)
            
            logger.info(f"Placed corresponding buy order: {quantity} @ {buy_price}")
            
        except Exception as e:
            logger.error(f"Failed to place corresponding buy order: {e}")
    
    def _update_grid_levels(self):
        """Update grid levels based on market conditions."""
        try:
            current_price = self.api_client.get_market_price(self.config.TRADING_PAIR)
            
            # Check if we need to adjust grid levels
            for level in self.grid_levels:
                # If both orders are filled, we can place new orders
                if level.buy_filled and level.sell_filled:
                    # Reset level
                    level.buy_filled = False
                    level.sell_filled = False
                    
                    # Recalculate prices based on current market
                    buy_prices, sell_prices = self.risk_manager.get_optimal_grid_levels(current_price)
                    level.buy_price = buy_prices[level.level - 1]
                    level.sell_price = sell_prices[level.level - 1]
                    
                    logger.info(f"Updated grid level {level.level}: buy={level.buy_price}, sell={level.sell_price}")
            
        except Exception as e:
            logger.error(f"Failed to update grid levels: {e}")
    
    def _close_position(self, position_id: str, reason: str):
        """Close a position."""
        try:
            # Cancel the order
            if self.api_client.cancel_order(position_id):
                logger.info(f"Closed position {position_id} due to {reason}")
                
                # Update risk manager
                self.risk_manager.update_position(position_id, 'cancelled')
                
                # Remove from active orders
                if position_id in self.active_orders:
                    del self.active_orders[position_id]
            
        except Exception as e:
            logger.error(f"Failed to close position {position_id}: {e}")
    
    def run(self):
        """Main execution loop."""
        try:
            logger.info("Starting grid trading bot...")
            self.is_running = True
            
            # Place initial grid orders
            current_price = self.api_client.get_market_price(self.config.TRADING_PAIR)
            self.place_grid_orders(current_price)
            
            # Main loop
            while self.is_running:
                try:
                    # Check if we should continue trading
                    if not self.risk_manager.should_continue_trading():
                        logger.warning("Risk limits exceeded, stopping trading")
                        break
                    
                    # Get current market price
                    current_price = self.api_client.get_market_price(self.config.TRADING_PAIR)
                    
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
        """Cleanup resources and cancel open orders."""
        try:
            logger.info("Cleaning up...")
            
            # Cancel all open orders
            for order_id in list(self.active_orders.keys()):
                try:
                    self.api_client.cancel_order(order_id)
                except Exception as e:
                    logger.error(f"Failed to cancel order {order_id}: {e}")
            
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