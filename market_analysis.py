"""
Market Analysis Module for Volume-Weighted Grid Placement (Phase 2 P3)

This module provides real-time market depth analysis and volume-weighted price level
detection to optimize grid placement for the trading bot. It integrates with the
existing micro-grid strategy (P1) and dynamic position sizing (P2).
"""

import time
import logging
from dataclasses import dataclass
from typing import List, Dict, Optional, Tuple
from collections import defaultdict


@dataclass
class VolumeLevel:
    """Represents a significant volume level in the order book"""
    price: float
    volume: float
    side: str  # 'buy' or 'sell'
    strength: float  # 0-1 confidence score
    depth_rank: int  # 1-N ranking by volume
    price_distance: float  # Distance from current price (%)


@dataclass
class MarketDepthAnalysis:
    """Complete market depth analysis result"""
    current_price: float
    bid_levels: List[VolumeLevel]
    ask_levels: List[VolumeLevel]
    volume_imbalance: float  # -1 to +1, negative = more sell pressure
    spread_percent: float
    depth_quality: float  # 0-1 quality score
    timestamp: float


class MarketAnalyzer:
    """
    Analyzes order book depth and identifies high-volume price levels for
    optimal grid placement in the trading bot.
    """
    
    def __init__(self, config):
        """
        Initialize the market analyzer with configuration settings.
        
        Args:
            config: Configuration object with market analysis parameters
        """
        self.config = config
        self.logger = logging.getLogger(__name__)
        self._cache = {}
        self._cache_duration = getattr(config, 'MARKET_ANALYSIS_CACHE_DURATION', 30)
        self._min_volume_strength = getattr(config, 'MIN_VOLUME_STRENGTH', 0.3)
        self._min_depth_quality = getattr(config, 'MIN_DEPTH_QUALITY', 0.3)
        self._volume_adjustment_tolerance = getattr(config, 'VOLUME_ADJUSTMENT_TOLERANCE', 0.02)
        
    def analyze_market_depth(self, order_book_data: Dict, current_price: float) -> Optional[MarketDepthAnalysis]:
        """
        Analyze order book depth and return volume-weighted price levels.
        
        Args:
            order_book_data: Raw order book data from API
            current_price: Current market price
            
        Returns:
            MarketDepthAnalysis object or None if analysis fails
        """
        cache_key = f"depth_{hash(str(order_book_data))}_{current_price}"
        
        # Check cache first
        if cache_key in self._cache:
            cached_result, timestamp = self._cache[cache_key]
            if time.time() - timestamp < self._cache_duration:
                self.logger.debug("Returning cached market depth analysis")
                return cached_result
                
        try:
            # Parse order book data
            bids = order_book_data.get('bids', [])
            asks = order_book_data.get('asks', [])
            
            if not bids or not asks:
                self.logger.warning("Empty order book data received")
                return None
                
            # Analyze each side of the order book
            bid_levels = self._analyze_order_book_side(bids, 'buy', current_price, max_levels=10)
            ask_levels = self._analyze_order_book_side(asks, 'sell', current_price, max_levels=10)
            
            # Calculate market metrics
            volume_imbalance = self._calculate_volume_imbalance(bid_levels, ask_levels)
            spread_percent = self._calculate_spread_percent(bids, asks, current_price)
            depth_quality = self._calculate_depth_quality(bid_levels, ask_levels, bids, asks)
            
            # Create analysis result
            analysis = MarketDepthAnalysis(
                current_price=current_price,
                bid_levels=bid_levels,
                ask_levels=ask_levels,
                volume_imbalance=volume_imbalance,
                spread_percent=spread_percent,
                depth_quality=depth_quality,
                timestamp=time.time()
            )
            
            # Cache the result
            self._cache[cache_key] = (analysis, time.time())
            
            # Clean old cache entries
            self._clean_cache()
            
            self.logger.debug(f"Market depth analysis completed: quality={depth_quality:.3f}, "
                            f"imbalance={volume_imbalance:.3f}, spread={spread_percent:.4f}%")
            
            return analysis
            
        except Exception as e:
            self.logger.error(f"Failed to analyze market depth: {e}")
            return None
            
    def _analyze_order_book_side(self, orders: List, side: str, current_price: float, max_levels: int) -> List[VolumeLevel]:
        """
        Analyze one side of the order book and identify significant volume levels.
        
        Args:
            orders: List of [price, volume] orders
            side: 'buy' or 'sell'
            current_price: Current market price
            max_levels: Maximum number of levels to return
            
        Returns:
            List of VolumeLevel objects ranked by strength
        """
        if not orders:
            return []
            
        # Group orders into 0.1% price buckets
        price_buckets = defaultdict(float)
        
        for order in orders:
            if len(order) < 2:
                continue
                
            try:
                price = float(order[0])
                volume = float(order[1])
                
                # Skip orders too far from current price (>5%)
                price_distance = abs(price - current_price) / current_price
                if price_distance > 0.05:
                    continue
                    
                # Determine bucket (0.1% increments)
                bucket_key = round(price / current_price, 3)
                price_buckets[bucket_key] += volume
                
            except (ValueError, IndexError) as e:
                self.logger.warning(f"Invalid order data: {order}, error: {e}")
                continue
                
        # Convert buckets to VolumeLevel objects
        volume_levels = []
        for bucket_price_ratio, total_volume in price_buckets.items():
            bucket_price = bucket_price_ratio * current_price
            price_distance = abs(bucket_price - current_price) / current_price
            
            # Calculate strength score (0-1)
            volume_score = min(total_volume / max(price_buckets.values()), 1.0) if price_buckets.values() else 0
            proximity_score = max(0, 1.0 - (price_distance * 20))  # Closer = stronger
            strength = (volume_score * 0.7) + (proximity_score * 0.3)
            
            volume_levels.append(VolumeLevel(
                price=bucket_price,
                volume=total_volume,
                side=side,
                strength=strength,
                depth_rank=0,  # Will be set after sorting
                price_distance=price_distance
            ))
            
        # Sort by strength and assign ranks
        volume_levels.sort(key=lambda x: x.strength, reverse=True)
        for i, level in enumerate(volume_levels[:max_levels]):
            level.depth_rank = i + 1
            
        # Filter by minimum strength
        strong_levels = [level for level in volume_levels if level.strength >= self._min_volume_strength]
        
        return strong_levels[:max_levels]
        
    def _calculate_volume_imbalance(self, bid_levels: List[VolumeLevel], ask_levels: List[VolumeLevel]) -> float:
        """
        Calculate volume imbalance between buy and sell pressure.
        
        Returns:
            Float between -1 and +1, where negative = more sell pressure
        """
        total_bid_volume = sum(level.volume for level in bid_levels)
        total_ask_volume = sum(level.volume for level in ask_levels)
        
        if total_bid_volume + total_ask_volume == 0:
            return 0.0
            
        imbalance = (total_bid_volume - total_ask_volume) / (total_bid_volume + total_ask_volume)
        return max(-1.0, min(1.0, imbalance))
        
    def _calculate_spread_percent(self, bids: List, asks: List, current_price: float) -> float:
        """Calculate bid-ask spread as percentage of current price."""
        if not bids or not asks:
            return 0.0
            
        try:
            best_bid = float(bids[0][0])
            best_ask = float(asks[0][0])
            spread = best_ask - best_bid
            return (spread / current_price) * 100
        except (ValueError, IndexError):
            return 0.0
            
    def _calculate_depth_quality(self, bid_levels: List[VolumeLevel], ask_levels: List[VolumeLevel], 
                               raw_bids: List, raw_asks: List) -> float:
        """
        Calculate overall depth quality score (0-1).
        
        Considers:
        - Number of significant levels found
        - Volume distribution consistency
        - Overall order book depth
        """
        # Level count score (0-1)
        total_levels = len(bid_levels) + len(ask_levels)
        level_score = min(total_levels / 10, 1.0)  # Optimal around 10 total levels
        
        # Volume distribution score
        all_levels = bid_levels + ask_levels
        if not all_levels:
            return 0.0
            
        strengths = [level.strength for level in all_levels]
        avg_strength = sum(strengths) / len(strengths)
        strength_score = avg_strength
        
        # Order book depth score
        total_orders = len(raw_bids) + len(raw_asks)
        depth_score = min(total_orders / 100, 1.0)  # Good depth around 100+ orders
        
        # Combined quality score
        quality = (level_score * 0.4) + (strength_score * 0.4) + (depth_score * 0.2)
        return min(max(quality, 0.0), 1.0)
        
    def _clean_cache(self):
        """Remove expired cache entries."""
        current_time = time.time()
        expired_keys = [
            key for key, (_, timestamp) in self._cache.items()
            if current_time - timestamp > self._cache_duration
        ]
        for key in expired_keys:
            del self._cache[key]
            
    def get_volume_weighted_adjustments(self, base_levels: List[float], current_price: float, 
                                      side: str, analysis: MarketDepthAnalysis) -> List[float]:
        """
        Adjust base grid levels to align with high-volume price levels.
        
        Args:
            base_levels: Original grid price levels
            current_price: Current market price
            side: 'buy' or 'sell'
            analysis: Market depth analysis
            
        Returns:
            Adjusted price levels optimized for volume
        """
        if not analysis or analysis.depth_quality < self._min_depth_quality:
            self.logger.debug("Insufficient market depth quality, using base levels")
            return base_levels
            
        # Get relevant volume levels for this side
        volume_levels = analysis.bid_levels if side == 'buy' else analysis.ask_levels
        
        if not volume_levels:
            return base_levels
            
        adjusted_levels = []
        
        for base_price in base_levels:
            best_adjustment = base_price
            best_benefit = 0
            
            # Find nearby volume levels within tolerance
            for vol_level in volume_levels:
                if vol_level.strength < self._min_volume_strength:
                    continue
                    
                # Calculate adjustment distance
                adjustment_distance = abs(vol_level.price - base_price) / base_price
                
                # Check if adjustment is within tolerance
                if adjustment_distance <= self._volume_adjustment_tolerance:
                    # Validate direction (buy orders should be below current price)
                    if side == 'buy' and vol_level.price >= current_price:
                        continue
                    if side == 'sell' and vol_level.price <= current_price:
                        continue
                        
                    # Calculate benefit score
                    benefit = vol_level.strength * (1.0 - adjustment_distance)
                    
                    if benefit > best_benefit:
                        best_adjustment = vol_level.price
                        best_benefit = benefit
                        
            adjusted_levels.append(best_adjustment)
            
        # Apply market imbalance bias if significant
        if abs(analysis.volume_imbalance) > 0.3:
            adjusted_levels = self._apply_imbalance_bias(adjusted_levels, current_price, 
                                                       analysis.volume_imbalance, side)
            
        return adjusted_levels
        
    def _apply_imbalance_bias(self, levels: List[float], current_price: float, 
                            imbalance: float, side: str) -> List[float]:
        """
        Apply subtle bias based on market volume imbalance.
        
        Args:
            levels: Price levels to adjust
            current_price: Current market price
            imbalance: Volume imbalance (-1 to +1)
            side: 'buy' or 'sell'
            
        Returns:
            Bias-adjusted price levels
        """
        # Conservative bias application (max 1% adjustment)
        bias_factor = imbalance * 0.01
        
        adjusted_levels = []
        for price in levels:
            if side == 'buy' and imbalance > 0:
                # More buy pressure - slightly lower buy orders
                adjusted_price = price * (1 - abs(bias_factor))
            elif side == 'sell' and imbalance < 0:
                # More sell pressure - slightly higher sell orders
                adjusted_price = price * (1 + abs(bias_factor))
            else:
                adjusted_price = price
                
            adjusted_levels.append(adjusted_price)
            
        return adjusted_levels
        
    def is_market_suitable_for_volume_weighting(self, analysis: MarketDepthAnalysis) -> bool:
        """
        Determine if market conditions are suitable for volume-weighted grid placement.
        
        Args:
            analysis: Market depth analysis
            
        Returns:
            True if volume weighting should be applied
        """
        if not analysis:
            return False
            
        # Check minimum quality threshold
        if analysis.depth_quality < self._min_depth_quality:
            return False
            
        # Check for sufficient volume levels
        total_strong_levels = len([l for l in analysis.bid_levels + analysis.ask_levels 
                                 if l.strength >= self._min_volume_strength])
        
        if total_strong_levels < 3:
            return False
            
        # Check spread reasonableness (not too wide)
        if analysis.spread_percent > 2.0:  # 2% spread threshold
            return False
            
        return True