import time
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
import logging
from market_analysis import MarketAnalyzer

logger = logging.getLogger(__name__)

@dataclass
class Position:
    """Represents a trading position."""
    id: str
    side: str  # 'buy' or 'sell'
    quantity: float
    price: float
    timestamp: float
    status: str  # 'open', 'filled', 'cancelled'
    profit_loss: float = 0.0

@dataclass
class RiskMetrics:
    """Risk metrics for the trading session."""
    total_pnl: float = 0.0
    daily_pnl: float = 0.0
    max_drawdown: float = 0.0
    win_rate: float = 0.0
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0

class RiskManager:
    """Manages risk for the grid trading bot."""
    
    def __init__(self, config):
        self.config = config
        self.positions: List[Position] = []
        self.risk_metrics = RiskMetrics()
        self.session_start = time.time()
        self.daily_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        self.max_capital_used = 0.0
        self.peak_capital = 0.0
        
        # Initialize market analyzer for volume-weighted grids (P3)
        # Handle both dict and Config object
        if isinstance(config, dict):
            self.market_analyzer = MarketAnalyzer(config) if config.get('volume_weighted_grids', True) else None
        else:
            self.market_analyzer = MarketAnalyzer(config) if getattr(config, 'VOLUME_WEIGHTED_GRIDS', True) else None
        
        # Load historical data if exists
        self._load_historical_data()
    
    def _get_config_value(self, key: str, default=None):
        """Safely get config value from either dict or Config object."""
        if isinstance(self.config, dict):
            return self.config.get(key, default)
        else:
            return getattr(self.config, key.upper(), default)
    
    def _load_historical_data(self):
        """Load historical trading data from file."""
        try:
            with open('trading_history.json', 'r') as f:
                data = json.load(f)
                self.risk_metrics = RiskMetrics(**data.get('metrics', {}))
                logger.info("Loaded historical trading data")
        except FileNotFoundError:
            logger.info("No historical data found, starting fresh")
        except Exception as e:
            logger.error(f"Failed to load historical data: {e}")
    
    def _save_historical_data(self):
        """Save trading data to file."""
        try:
            data = {
                'metrics': asdict(self.risk_metrics),
                'last_updated': datetime.now().isoformat()
            }
            with open('trading_history.json', 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save historical data: {e}")
    
    def calculate_position_size(self, current_price: float, base_risk: float) -> float:
        """Calculate optimal position size with dynamic scaling."""
        try:
            # Get effective capital including compounded profits
            effective_capital = self._get_effective_capital()
            
            # Calculate performance-adjusted risk
            dynamic_risk = self._calculate_dynamic_risk(base_risk)
            
            # Apply small account optimizations
            optimized_risk = self._apply_small_account_optimizations(
                dynamic_risk, effective_capital
            )
            
            # Calculate base position size
            base_position_value = effective_capital * optimized_risk
            base_position_size = base_position_value / current_price
            
            # Apply position sizing optimizations
            optimized_size = self._optimize_position_for_capital(
                base_position_size, current_price, effective_capital
            )
            
            # Check exposure limits
            if not self._check_exposure_limits(optimized_size, current_price, effective_capital):
                logger.warning(f"Position would exceed exposure limits")
                return 0.0
            
            # Ensure minimum viable position
            min_position_size = self._calculate_minimum_position(current_price, effective_capital)
            final_position_size = max(min_position_size, optimized_size)
            
            # Log detailed sizing information
            logger.info(f"Dynamic sizing: capital=${effective_capital:.2f}, "
                       f"risk={optimized_risk:.1%}, size={final_position_size:.6f}, "
                       f"value=${final_position_size * current_price:.2f}")
            
            return final_position_size
            
        except Exception as e:
            logger.error(f"Position size calculation failed: {e}")
            return self._get_fallback_position_size(current_price, base_risk)

    def _get_effective_capital(self) -> float:
        """Calculate effective capital including compounded profits."""
        base_capital = self._get_config_value('capital', 250.0)
        
        if self._get_config_value('compound_profits', True):
            # Add realized profits to capital base
            total_realized_pnl = sum(
                pos.profit_loss for pos in self.positions 
                if pos.status == 'filled' and pos.profit_loss > 0
            )
            # Only compound positive P&L, up to 2x original capital
            compounded_profits = min(total_realized_pnl, base_capital)
            effective_capital = base_capital + max(0, compounded_profits)
        else:
            effective_capital = base_capital
        
        return effective_capital

    def _calculate_dynamic_risk(self, base_risk: float) -> float:
        """Calculate risk percentage based on recent performance."""
        if not self.config.get('dynamic_sizing', True):
            return base_risk
        
        min_risk = self.config.get('min_risk_per_trade', 0.01)
        max_risk = self.config.get('max_risk_per_trade', 0.05)
        
        # Require minimum trades for performance analysis
        if self.risk_metrics.total_trades < 10:
            return base_risk
        
        # Get performance metrics
        win_rate = self.risk_metrics.win_rate
        recent_performance = self._calculate_recent_performance()
        
        # Calculate performance multiplier
        performance_multiplier = self._get_performance_multiplier(win_rate, recent_performance)
        
        # Apply scaling
        adjusted_risk = base_risk * performance_multiplier
        
        # Enforce bounds
        return max(min_risk, min(max_risk, adjusted_risk))

    def _get_performance_multiplier(self, win_rate: float, recent_performance: float) -> float:
        """Calculate position size multiplier based on performance."""
        high_threshold = self.config.get('win_rate_threshold_high', 0.7)
        low_threshold = self.config.get('win_rate_threshold_low', 0.5)
        scaling_factor = self.config.get('risk_scaling_factor', 1.5)
        
        # Win rate-based scaling
        if win_rate >= high_threshold:
            # Excellent performance: increase position sizes
            win_rate_multiplier = 1.0 + (win_rate - high_threshold) * scaling_factor
        elif win_rate <= low_threshold:
            # Poor performance: reduce position sizes
            win_rate_multiplier = low_threshold + (win_rate * 0.5)
        else:
            # Average performance: neutral
            win_rate_multiplier = 1.0
        
        # Recent performance adjustment
        recent_multiplier = 1.0 + (recent_performance * 0.5)  # Max 50% boost/reduction
        
        # Combine multipliers with dampening
        combined_multiplier = (win_rate_multiplier + recent_multiplier) / 2
        
        # Clamp to reasonable bounds
        return max(0.5, min(2.0, combined_multiplier))

    def _apply_small_account_optimizations(self, risk: float, capital: float) -> float:
        """Apply specific optimizations for small capital accounts."""
        micro_threshold = self.config.get('micro_capital_threshold', 500)
        small_threshold = self.config.get('small_capital_threshold', 1000)
        boost_factor = self.config.get('small_account_boost', 1.2)
        
        if capital < micro_threshold:
            # Micro accounts: allow higher risk for viability
            max_micro_risk = min(0.04, risk * 1.5)  # Up to 4% risk
            return max(risk, max_micro_risk)
        elif capital < small_threshold:
            # Small accounts: moderate boost
            return risk * boost_factor
        else:
            # Regular accounts: no change
            return risk

    def _calculate_recent_performance(self) -> float:
        """Calculate recent performance trend (-1 to +1)."""
        recent_positions = self.positions[-20:]  # Last 20 trades
        
        if len(recent_positions) < 5:
            return 0.0
        
        # Calculate recent P&L trend
        recent_pnls = [pos.profit_loss for pos in recent_positions if pos.profit_loss != 0]
        
        if not recent_pnls:
            return 0.0
        
        # Simple momentum: ratio of positive to total P&L
        positive_pnls = [pnl for pnl in recent_pnls if pnl > 0]
        momentum = (len(positive_pnls) / len(recent_pnls)) - 0.5  # Center around 0
        
        return max(-1.0, min(1.0, momentum * 2))  # Scale to -1 to +1 range

    def _optimize_position_for_capital(self, base_size: float, price: float, capital: float) -> float:
        """Apply capital-specific position optimizations."""
        position_value = base_size * price
        
        # For very small capital, ensure positions are meaningful
        if capital < 300:
            min_meaningful_value = capital * 0.015  # 1.5% minimum
            if position_value < min_meaningful_value:
                return min_meaningful_value / price
        
        # For medium capital, apply standard optimizations
        elif capital < 1000:
            # Ensure position is at least 0.5% of capital
            min_value = capital * 0.005
            if position_value < min_value:
                return min_value / price
        
        return base_size

    def _check_exposure_limits(self, position_size: float, price: float, capital: float) -> bool:
        """Check if position would exceed exposure limits."""
        current_exposure = self.get_current_exposure()
        new_position_value = position_size * price
        total_exposure = current_exposure + new_position_value
        
        # Dynamic exposure limits based on capital size
        if capital < 500:
            max_exposure_percent = 0.90  # 90% for micro accounts
        elif capital < 1000:
            max_exposure_percent = 0.85  # 85% for small accounts
        else:
            max_exposure_percent = 0.80  # 80% for regular accounts
        
        max_exposure = capital * max_exposure_percent
        
        return total_exposure <= max_exposure

    def _calculate_minimum_position(self, price: float, capital: float) -> float:
        """Calculate minimum viable position size."""
        # Minimum $1 position or 0.1% of capital, whichever is larger
        min_dollar_value = max(1.0, capital * 0.001)
        return min_dollar_value / price

    def _get_fallback_position_size(self, price: float, base_risk: float) -> float:
        """Get safe fallback position size on calculation errors."""
        safe_capital = self._get_config_value('capital', 250.0)
        safe_risk = min(base_risk, 0.02)  # Cap at 2% for safety
        return (safe_capital * safe_risk) / price
    
    def get_current_exposure(self) -> float:
        """Calculate current market exposure."""
        exposure = 0.0
        for position in self.positions:
            if position.status == 'open':
                exposure += position.quantity * position.price
        return exposure
    
    def check_daily_loss_limit(self) -> bool:
        """Check if daily loss limit has been reached."""
        daily_loss = abs(min(0, self.risk_metrics.daily_pnl))
        max_daily_loss = self._get_config_value('capital', 250.0) * self._get_config_value('max_daily_loss', 0.05)
        
        if daily_loss >= max_daily_loss:
            logger.warning(f"Daily loss limit reached: {daily_loss:.2f} >= {max_daily_loss:.2f}")
            return False
        return True
    
    def check_stop_loss(self, current_price: float) -> List[str]:
        """Check stop loss conditions and return positions to close."""
        positions_to_close = []
        
        for position in self.positions:
            if position.status != 'open':
                continue
                
            if position.side == 'buy':
                # Check if price dropped below stop loss
                stop_loss_price = position.price * (1 - self._get_config_value('stop_loss_percent', 0.05))
                if current_price <= stop_loss_price:
                    positions_to_close.append(position.id)
                    logger.warning(f"Stop loss triggered for buy position {position.id} at {current_price:.2f}")
            
            elif position.side == 'sell':
                # Check if price rose above stop loss
                stop_loss_price = position.price * (1 + self._get_config_value('stop_loss_percent', 0.05))
                if current_price >= stop_loss_price:
                    positions_to_close.append(position.id)
                    logger.warning(f"Stop loss triggered for sell position {position.id} at {current_price:.2f}")
        
        return positions_to_close
    
    def update_position(self, position_id: str, status: str, fill_price: float = None):
        """Update position status and calculate P&L."""
        for position in self.positions:
            if position.id == position_id:
                old_status = position.status
                position.status = status
                
                if status == 'filled' and fill_price:
                    # Calculate P&L
                    if position.side == 'buy':
                        position.profit_loss = (fill_price - position.price) * position.quantity
                    else:  # sell
                        position.profit_loss = (position.price - fill_price) * position.quantity
                    
                    # Update metrics
                    self._update_metrics(position.profit_loss)
                    
                    logger.info(f"Position {position_id} filled at {fill_price:.2f}, P&L: {position.profit_loss:.2f}")
                
                break
    
    def _update_metrics(self, pnl: float):
        """Update risk metrics with new P&L."""
        self.risk_metrics.total_pnl += pnl
        self.risk_metrics.daily_pnl += pnl
        self.risk_metrics.total_trades += 1
        
        if pnl > 0:
            self.risk_metrics.winning_trades += 1
        else:
            self.risk_metrics.losing_trades += 1
        
        # Calculate win rate
        if self.risk_metrics.total_trades > 0:
            self.risk_metrics.win_rate = self.risk_metrics.winning_trades / self.risk_metrics.total_trades
        
        # Update max drawdown
        if self.risk_metrics.total_pnl < self.risk_metrics.max_drawdown:
            self.risk_metrics.max_drawdown = self.risk_metrics.total_pnl
        
        # Reset daily P&L at midnight
        now = datetime.now()
        if now.date() > self.daily_start.date():
            self.risk_metrics.daily_pnl = 0.0
            self.daily_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        
        # Save data periodically
        if self.risk_metrics.total_trades % 10 == 0:
            self._save_historical_data()
    
    def add_position(self, position: Position):
        """Add a new position to track."""
        self.positions.append(position)
        logger.info(f"Added position: {position.side} {position.quantity} at {position.price}")
    
    def get_performance_summary(self) -> Dict:
        """Get current performance summary."""
        current_exposure = self.get_current_exposure()
        session_duration = time.time() - self.session_start
        
        return {
            'total_pnl': self.risk_metrics.total_pnl,
            'daily_pnl': self.risk_metrics.daily_pnl,
            'win_rate': self.risk_metrics.win_rate,
            'total_trades': self.risk_metrics.total_trades,
            'current_exposure': current_exposure,
            'max_drawdown': self.risk_metrics.max_drawdown,
            'session_duration_hours': session_duration / 3600,
            'roi_percent': (self.risk_metrics.total_pnl / self._get_config_value('capital', 250.0)) * 100 if self._get_config_value('capital', 250.0) > 0 else 0
        }
    
    def should_continue_trading(self) -> bool:
        """Determine if trading should continue based on risk metrics."""
        # Check daily loss limit
        if not self.check_daily_loss_limit():
            return False
        
        # Check if max drawdown exceeded
        max_drawdown_limit = self._get_config_value('capital', 250.0) * 0.15  # 15% max drawdown
        if abs(self.risk_metrics.max_drawdown) > max_drawdown_limit:
            logger.warning(f"Maximum drawdown exceeded: {self.risk_metrics.max_drawdown:.2f}")
            return False
        
        return True
    
    def get_optimal_grid_levels(self, current_price: float, api_client=None) -> Tuple[List[float], List[float]]:
        """
        Calculate optimal grid levels with micro-grid strategy (P1), 
        dynamic position sizing (P2), and volume-weighted placement (P3).
        """
        # Phase 1: Calculate base micro-grid levels
        buy_prices, sell_prices = self._calculate_base_grid_levels(current_price)
        
        # Phase 3: Apply volume-weighted adjustments if enabled and market data available
        if (self.market_analyzer and api_client and 
            self.config.get('volume_weighted_grids', True) and
            self.config.get('market_depth_analysis', True)):
            
            try:
                # Get market depth data
                order_book = api_client.get_market_depth(self.config.get('trading_pair', 'SOL/USDC'))
                
                if order_book:
                    # Analyze market depth
                    analysis = self.market_analyzer.analyze_market_depth(order_book, current_price)
                    
                    if analysis and self.market_analyzer.is_market_suitable_for_volume_weighting(analysis):
                        # Apply volume-weighted adjustments
                        buy_prices = self.market_analyzer.get_volume_weighted_adjustments(
                            buy_prices, current_price, 'buy', analysis
                        )
                        sell_prices = self.market_analyzer.get_volume_weighted_adjustments(
                            sell_prices, current_price, 'sell', analysis
                        )
                        
                        logger.info(f"Volume-weighted grid applied: quality={analysis.depth_quality:.3f}, "
                                   f"imbalance={analysis.volume_imbalance:.3f}, "
                                   f"bid_levels={len(analysis.bid_levels)}, ask_levels={len(analysis.ask_levels)}")
                    else:
                        logger.debug("Market conditions not suitable for volume weighting, using base grid")
                else:
                    logger.debug("No market depth data available, using base grid")
                    
            except Exception as e:
                logger.warning(f"Volume-weighted grid calculation failed, falling back to base grid: {e}")
        
        # Log final strategy details
        base_grid_levels = len(buy_prices)
        volatility = self._calculate_recent_volatility()
        spacing = abs(buy_prices[0] - current_price) / current_price if buy_prices else 0.01
        
        logger.info(f"Final grid: {base_grid_levels} levels, spacing: {spacing:.1%}, "
                   f"volatility: {volatility:.1%}, capital: ${self._get_config_value('capital', 250.0)}")
        
        return buy_prices, sell_prices
    
    def _calculate_base_grid_levels(self, current_price: float) -> Tuple[List[float], List[float]]:
        """Calculate base micro-grid levels (P1 implementation)."""
        base_grid_levels = self._get_config_value('grid_levels', 5)
        
        if self._get_config_value('micro_grid_mode', True):
            # Calculate dynamic spacing based on volatility
            volatility = self._calculate_recent_volatility()
            base_spacing = self._get_config_value('price_range_percent', 0.10) / base_grid_levels
            
            # Small capital optimizations
            capital = self._get_config_value('capital', 250.0)
            if capital < self._get_config_value('small_capital_threshold', 1000):
                # Increase grid density for small capital
                density_multiplier = self._get_config_value('grid_density_multiplier', 2.0)
                
                if capital < self._get_config_value('micro_capital_threshold', 500):
                    # Extra tight spacing for micro capital
                    base_spacing *= 0.3  # 70% tighter spacing
                    density_multiplier *= 1.5  # 50% more levels
                else:
                    # Moderate tightening for small capital
                    base_spacing *= 0.5  # 50% tighter spacing
                
                # Calculate new grid count
                max_levels = 20 if capital < 500 else 15
                grid_levels = min(int(base_grid_levels * density_multiplier), max_levels)
            else:
                grid_levels = base_grid_levels
            
            # Apply volatility adjustment
            if self.config.get('adaptive_spacing', True):
                volatility_multiplier = self._calculate_volatility_multiplier(volatility)
                adjusted_spacing = base_spacing * volatility_multiplier
                
                # Enforce min/max spacing bounds
                min_spacing = self.config.get('min_grid_spacing', 0.005)
                max_spacing = self.config.get('max_grid_spacing', 0.03)
                spacing = max(min_spacing, min(adjusted_spacing, max_spacing))
            else:
                spacing = base_spacing
        else:
            # Original calculation for larger accounts
            price_range = self._get_config_value('price_range_percent', 0.10)
            spacing = (current_price * price_range) / base_grid_levels
            grid_levels = base_grid_levels
        
        # Generate base grid levels
        price_step = current_price * spacing
        buy_prices = [current_price - (i * price_step) for i in range(1, grid_levels + 1)]
        sell_prices = [current_price + (i * price_step) for i in range(1, grid_levels + 1)]
        
        return buy_prices, sell_prices

    def _calculate_volatility_multiplier(self, volatility: float) -> float:
        """Calculate multiplier based on volatility for spacing adjustment."""
        # Base multiplier of 1.0 for 2% volatility
        base_volatility = 0.02
        
        # Scale factor: higher volatility = wider spacing
        scale_factor = 2.0
        multiplier = 1.0 + (volatility - base_volatility) * scale_factor
        
        # Clamp between 0.5x and 2.5x
        return max(0.5, min(2.5, multiplier))

    def _calculate_recent_volatility(self) -> float:
        """Calculate recent price volatility for grid spacing adjustment."""
        try:
            # Use trade history for volatility estimation
            if self.risk_metrics.total_trades < 10:
                return 0.02  # Default 2% volatility for new accounts
            
            # Get recent position P&L data for volatility proxy
            recent_positions = [pos for pos in self.positions[-50:] 
                               if pos.status == 'filled' and pos.profit_loss != 0]
            
            if len(recent_positions) < 5:
                return 0.02  # Insufficient data
            
            # Calculate price movement volatility from P&L variance
            import statistics
            pnl_percentages = [
                abs(pos.profit_loss) / (pos.quantity * pos.price) 
                for pos in recent_positions
            ]
            
            if len(pnl_percentages) >= 5:
                volatility = statistics.stdev(pnl_percentages)
                
                # Apply smoothing factor to prevent overreaction
                smoothing_factor = 0.7
                previous_volatility = getattr(self, '_last_volatility', 0.02)
                self._last_volatility = (smoothing_factor * previous_volatility + 
                                       (1 - smoothing_factor) * volatility)
                
                # Return clamped volatility
                return max(0.005, min(0.15, self._last_volatility))
            
            return 0.02  # Safe default
            
        except Exception as e:
            logger.warning(f"Volatility calculation failed: {e}")
            return 0.02  # Always return safe default 