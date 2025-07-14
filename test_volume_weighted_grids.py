"""
Comprehensive Test Suite for Volume-Weighted Grid Placement (Phase 2 P3)

This test suite validates the functionality of the market analysis module,
volume-weighted grid calculations, and integration with existing P1/P2 systems.
"""

import unittest
import time
import json
from unittest.mock import Mock, patch, MagicMock
from typing import Dict, List

from market_analysis import MarketAnalyzer, VolumeLevel, MarketDepthAnalysis
from risk_manager import RiskManager
from api_client import APIClient
from config import Config


class TestMarketAnalyzer(unittest.TestCase):
    """Test cases for the MarketAnalyzer class."""
    
    def setUp(self):
        """Set up test configuration and analyzer."""
        self.config = {
            'market_analysis_cache_duration': 30,
            'min_volume_strength': 0.3,
            'min_depth_quality': 0.3,
            'volume_adjustment_tolerance': 0.02,
            'volume_weighted_grids': True,
            'market_depth_analysis': True
        }
        self.analyzer = MarketAnalyzer(self.config)
        self.current_price = 100.0
        
    def test_volume_level_creation(self):
        """Test VolumeLevel data structure creation."""
        level = VolumeLevel(
            price=99.5,
            volume=1000.0,
            side='buy',
            strength=0.8,
            depth_rank=1,
            price_distance=0.005
        )
        
        self.assertEqual(level.price, 99.5)
        self.assertEqual(level.volume, 1000.0)
        self.assertEqual(level.side, 'buy')
        self.assertEqual(level.strength, 0.8)
        self.assertEqual(level.depth_rank, 1)
        self.assertEqual(level.price_distance, 0.005)
        
    def test_market_depth_analysis_creation(self):
        """Test MarketDepthAnalysis data structure creation."""
        bid_levels = [VolumeLevel(99.0, 500.0, 'buy', 0.7, 1, 0.01)]
        ask_levels = [VolumeLevel(101.0, 600.0, 'sell', 0.6, 1, 0.01)]
        
        analysis = MarketDepthAnalysis(
            current_price=100.0,
            bid_levels=bid_levels,
            ask_levels=ask_levels,
            volume_imbalance=0.1,
            spread_percent=2.0,
            depth_quality=0.8,
            timestamp=time.time()
        )
        
        self.assertEqual(analysis.current_price, 100.0)
        self.assertEqual(len(analysis.bid_levels), 1)
        self.assertEqual(len(analysis.ask_levels), 1)
        self.assertEqual(analysis.volume_imbalance, 0.1)
        
    def test_order_book_side_analysis_valid_data(self):
        """Test order book analysis with valid data."""
        # Mock order book data
        orders = [
            [99.5, 1000.0],  # price, volume
            [99.4, 800.0],
            [99.3, 1200.0],
            [99.2, 600.0],
            [99.1, 900.0]
        ]
        
        levels = self.analyzer._analyze_order_book_side(orders, 'buy', self.current_price, 5)
        
        self.assertIsInstance(levels, list)
        self.assertGreater(len(levels), 0)
        
        # Check that levels are sorted by strength
        for i in range(len(levels) - 1):
            self.assertGreaterEqual(levels[i].strength, levels[i + 1].strength)
            
        # Check that all levels meet minimum strength requirement
        for level in levels:
            self.assertGreaterEqual(level.strength, self.config['min_volume_strength'])
            
    def test_order_book_side_analysis_empty_data(self):
        """Test order book analysis with empty data."""
        levels = self.analyzer._analyze_order_book_side([], 'buy', self.current_price, 5)
        self.assertEqual(levels, [])
        
    def test_order_book_side_analysis_invalid_data(self):
        """Test order book analysis with invalid data."""
        # Invalid order format
        invalid_orders = [
            [99.5],  # Missing volume
            ['invalid', 800.0],  # Invalid price
            [99.3, 'invalid'],  # Invalid volume
        ]
        
        levels = self.analyzer._analyze_order_book_side(invalid_orders, 'buy', self.current_price, 5)
        self.assertEqual(levels, [])
        
    def test_volume_imbalance_calculation(self):
        """Test volume imbalance calculation."""
        bid_levels = [
            VolumeLevel(99.0, 1000.0, 'buy', 0.8, 1, 0.01),
            VolumeLevel(98.5, 800.0, 'buy', 0.6, 2, 0.015)
        ]
        ask_levels = [
            VolumeLevel(101.0, 600.0, 'sell', 0.7, 1, 0.01)
        ]
        
        imbalance = self.analyzer._calculate_volume_imbalance(bid_levels, ask_levels)
        
        # More buy volume (1800) than sell volume (600), so imbalance should be positive
        self.assertGreater(imbalance, 0)
        self.assertLessEqual(abs(imbalance), 1.0)  # Should be between -1 and 1
        
    def test_spread_calculation(self):
        """Test bid-ask spread calculation."""
        bids = [[99.5, 1000.0]]
        asks = [[100.5, 1000.0]]
        
        spread = self.analyzer._calculate_spread_percent(bids, asks, self.current_price)
        
        expected_spread = ((100.5 - 99.5) / self.current_price) * 100  # Should be 1%
        self.assertAlmostEqual(spread, expected_spread, places=2)
        
    def test_depth_quality_calculation(self):
        """Test market depth quality calculation."""
        bid_levels = [VolumeLevel(99.0, 1000.0, 'buy', 0.8, 1, 0.01)]
        ask_levels = [VolumeLevel(101.0, 1000.0, 'sell', 0.7, 1, 0.01)]
        raw_bids = [[99.0, 1000.0]] * 50  # 50 bid orders
        raw_asks = [[101.0, 1000.0]] * 50  # 50 ask orders
        
        quality = self.analyzer._calculate_depth_quality(bid_levels, ask_levels, raw_bids, raw_asks)
        
        self.assertGreaterEqual(quality, 0.0)
        self.assertLessEqual(quality, 1.0)
        
    def test_market_depth_analysis_with_valid_data(self):
        """Test complete market depth analysis with valid data."""
        order_book = {
            'bids': [
                [99.5, 1000.0],
                [99.4, 800.0],
                [99.3, 1200.0]
            ],
            'asks': [
                [100.5, 900.0],
                [100.6, 700.0],
                [100.7, 1100.0]
            ]
        }
        
        analysis = self.analyzer.analyze_market_depth(order_book, self.current_price)
        
        self.assertIsNotNone(analysis)
        self.assertIsInstance(analysis, MarketDepthAnalysis)
        self.assertEqual(analysis.current_price, self.current_price)
        self.assertGreaterEqual(analysis.depth_quality, 0.0)
        self.assertLessEqual(analysis.depth_quality, 1.0)
        
    def test_market_depth_analysis_with_empty_data(self):
        """Test market depth analysis with empty order book."""
        order_book = {'bids': [], 'asks': []}
        
        analysis = self.analyzer.analyze_market_depth(order_book, self.current_price)
        
        self.assertIsNone(analysis)
        
    def test_volume_weighted_adjustments_suitable_market(self):
        """Test volume-weighted adjustments with suitable market conditions."""
        # Create mock analysis with good quality
        bid_levels = [VolumeLevel(99.0, 1000.0, 'buy', 0.8, 1, 0.01)]
        ask_levels = [VolumeLevel(101.0, 1000.0, 'sell', 0.7, 1, 0.01)]
        
        analysis = MarketDepthAnalysis(
            current_price=self.current_price,
            bid_levels=bid_levels,
            ask_levels=ask_levels,
            volume_imbalance=0.1,
            spread_percent=1.0,
            depth_quality=0.8,
            timestamp=time.time()
        )
        
        base_levels = [99.1, 98.8, 98.5]  # Buy levels below current price
        
        adjusted_levels = self.analyzer.get_volume_weighted_adjustments(
            base_levels, self.current_price, 'buy', analysis
        )
        
        self.assertEqual(len(adjusted_levels), len(base_levels))
        self.assertIsInstance(adjusted_levels, list)
        
    def test_volume_weighted_adjustments_unsuitable_market(self):
        """Test volume-weighted adjustments with unsuitable market conditions."""
        # Create mock analysis with poor quality
        analysis = MarketDepthAnalysis(
            current_price=self.current_price,
            bid_levels=[],
            ask_levels=[],
            volume_imbalance=0.0,
            spread_percent=5.0,  # Wide spread
            depth_quality=0.1,   # Poor quality
            timestamp=time.time()
        )
        
        base_levels = [99.1, 98.8, 98.5]
        
        adjusted_levels = self.analyzer.get_volume_weighted_adjustments(
            base_levels, self.current_price, 'buy', analysis
        )
        
        # Should return original levels when market unsuitable
        self.assertEqual(adjusted_levels, base_levels)
        
    def test_market_suitability_check(self):
        """Test market suitability assessment for volume weighting."""
        # Good quality market
        good_analysis = MarketDepthAnalysis(
            current_price=self.current_price,
            bid_levels=[VolumeLevel(99.0, 1000.0, 'buy', 0.8, 1, 0.01)] * 3,
            ask_levels=[VolumeLevel(101.0, 1000.0, 'sell', 0.7, 1, 0.01)] * 3,
            volume_imbalance=0.1,
            spread_percent=1.0,
            depth_quality=0.8,
            timestamp=time.time()
        )
        
        self.assertTrue(self.analyzer.is_market_suitable_for_volume_weighting(good_analysis))
        
        # Poor quality market
        poor_analysis = MarketDepthAnalysis(
            current_price=self.current_price,
            bid_levels=[],
            ask_levels=[],
            volume_imbalance=0.0,
            spread_percent=5.0,
            depth_quality=0.1,
            timestamp=time.time()
        )
        
        self.assertFalse(self.analyzer.is_market_suitable_for_volume_weighting(poor_analysis))
        
    def test_caching_functionality(self):
        """Test market analysis caching."""
        order_book = {
            'bids': [[99.5, 1000.0]],
            'asks': [[100.5, 1000.0]]
        }
        
        # First call should perform analysis
        analysis1 = self.analyzer.analyze_market_depth(order_book, self.current_price)
        
        # Second call should return cached result
        analysis2 = self.analyzer.analyze_market_depth(order_book, self.current_price)
        
        self.assertEqual(analysis1.timestamp, analysis2.timestamp)


class TestRiskManagerIntegration(unittest.TestCase):
    """Test integration of volume-weighted grids with risk manager."""
    
    def setUp(self):
        """Set up test environment."""
        self.config = {
            'capital': 500.0,
            'grid_levels': 5,
            'price_range_percent': 0.10,
            'micro_grid_mode': True,
            'small_capital_threshold': 1000,
            'micro_capital_threshold': 500,
            'grid_density_multiplier': 2.0,
            'volume_weighted_grids': True,
            'market_depth_analysis': True,
            'trading_pair': 'SOL/USDC'
        }
        self.risk_manager = RiskManager(self.config)
        self.current_price = 100.0
        
    def test_base_grid_calculation(self):
        """Test base micro-grid calculation (P1)."""
        buy_prices, sell_prices = self.risk_manager._calculate_base_grid_levels(self.current_price)
        
        self.assertIsInstance(buy_prices, list)
        self.assertIsInstance(sell_prices, list)
        self.assertGreater(len(buy_prices), 0)
        self.assertGreater(len(sell_prices), 0)
        
        # Buy prices should be below current price
        for price in buy_prices:
            self.assertLess(price, self.current_price)
            
        # Sell prices should be above current price
        for price in sell_prices:
            self.assertGreater(price, self.current_price)
            
    @patch('risk_manager.RiskManager._calculate_recent_volatility')
    def test_optimal_grid_levels_without_api(self, mock_volatility):
        """Test optimal grid calculation without API client."""
        mock_volatility.return_value = 0.02
        
        buy_prices, sell_prices = self.risk_manager.get_optimal_grid_levels(self.current_price)
        
        self.assertIsInstance(buy_prices, list)
        self.assertIsInstance(sell_prices, list)
        self.assertGreater(len(buy_prices), 0)
        self.assertGreater(len(sell_prices), 0)
        
    @patch('api_client.APIClient.get_market_depth')
    @patch('risk_manager.RiskManager._calculate_recent_volatility')
    def test_optimal_grid_levels_with_volume_weighting(self, mock_volatility, mock_market_depth):
        """Test optimal grid calculation with volume-weighted adjustments."""
        mock_volatility.return_value = 0.02
        mock_market_depth.return_value = {
            'bids': [
                [99.5, 1000.0],
                [99.0, 800.0],
                [98.5, 1200.0]
            ],
            'asks': [
                [100.5, 900.0],
                [101.0, 700.0],
                [101.5, 1100.0]
            ]
        }
        
        # Mock API client
        mock_api_client = Mock()
        mock_api_client.get_market_depth.return_value = mock_market_depth.return_value
        
        buy_prices, sell_prices = self.risk_manager.get_optimal_grid_levels(
            self.current_price, mock_api_client
        )
        
        self.assertIsInstance(buy_prices, list)
        self.assertIsInstance(sell_prices, list)
        self.assertGreater(len(buy_prices), 0)
        self.assertGreater(len(sell_prices), 0)
        
        # Verify API was called
        mock_api_client.get_market_depth.assert_called_once()


class TestAPIClientMarketDepth(unittest.TestCase):
    """Test enhanced market depth functionality in API client."""
    
    def setUp(self):
        """Set up test environment."""
        self.config = Mock()
        self.config.BASE_URL = "https://api.test.com"
        self.config.API_KEY = "test_key"
        self.config.API_SECRET = "test_secret"
        
        self.security_manager = Mock()
        self.security_manager.create_secure_headers.return_value = {"Authorization": "Bearer test"}
        self.security_manager.validate_api_response.return_value = True
        
        self.api_client = APIClient(self.config, self.security_manager)
        
    def test_validate_market_depth_response_valid(self):
        """Test market depth response validation with valid data."""
        valid_response = {
            'bids': [[99.5, 1000.0], [99.0, 800.0]],
            'asks': [[100.5, 900.0], [101.0, 700.0]]
        }
        
        is_valid = self.api_client._validate_market_depth_response(valid_response)
        self.assertTrue(is_valid)
        
    def test_validate_market_depth_response_invalid(self):
        """Test market depth response validation with invalid data."""
        invalid_responses = [
            {},  # Missing required fields
            {'bids': [], 'asks': 'invalid'},  # Invalid asks format
            {'bids': [[99.5]], 'asks': []},  # Missing volume in bid
            {'bids': [['invalid', 1000]], 'asks': []},  # Invalid price type
        ]
        
        for response in invalid_responses:
            is_valid = self.api_client._validate_market_depth_response(response)
            self.assertFalse(is_valid, f"Response should be invalid: {response}")
            
    @patch('api_client.APIClient.get_market_price')
    def test_fallback_market_depth_generation(self, mock_price):
        """Test fallback market depth generation."""
        mock_price.return_value = 100.0
        
        fallback_data = self.api_client._get_fallback_market_depth('SOL/USDC', 5)
        
        self.assertIn('bids', fallback_data)
        self.assertIn('asks', fallback_data)
        self.assertIn('source', fallback_data)
        self.assertEqual(fallback_data['source'], 'fallback_generated')
        self.assertGreater(len(fallback_data['bids']), 0)
        self.assertGreater(len(fallback_data['asks']), 0)


class TestIntegrationScenarios(unittest.TestCase):
    """Test complete integration scenarios for P1+P2+P3."""
    
    def setUp(self):
        """Set up integration test environment."""
        self.config = {
            'capital': 250.0,
            'grid_levels': 5,
            'price_range_percent': 0.10,
            'risk_per_trade': 0.02,
            'micro_grid_mode': True,
            'dynamic_sizing': True,
            'volume_weighted_grids': True,
            'market_depth_analysis': True,
            'small_capital_threshold': 1000,
            'micro_capital_threshold': 500,
            'grid_density_multiplier': 2.0,
            'min_volume_strength': 0.3,
            'min_depth_quality': 0.3,
            'volume_adjustment_tolerance': 0.02,
            'trading_pair': 'SOL/USDC'
        }
        
    def test_micro_account_complete_workflow(self):
        """Test complete workflow for micro account ($250)."""
        risk_manager = RiskManager(self.config)
        current_price = 50.0  # SOL price
        
        # Test position sizing (P2)
        position_size = risk_manager.calculate_position_size(current_price, 0.02)
        self.assertGreater(position_size, 0)
        
        # Test grid calculation (P1 + P3)
        buy_prices, sell_prices = risk_manager.get_optimal_grid_levels(current_price)
        
        # Verify micro-grid optimizations
        total_levels = len(buy_prices) + len(sell_prices)
        self.assertGreaterEqual(total_levels, 10)  # Should have more levels for micro accounts
        
        # Verify spacing is tighter for micro accounts
        if len(buy_prices) >= 2:
            spacing = abs(buy_prices[0] - buy_prices[1]) / current_price
            self.assertLess(spacing, 0.02)  # Should be tight spacing
            
    def test_performance_scaling_integration(self):
        """Test integration of performance scaling with grid optimization."""
        risk_manager = RiskManager(self.config)
        
        # Simulate good performance
        risk_manager.risk_metrics.total_trades = 20
        risk_manager.risk_metrics.winning_trades = 16  # 80% win rate
        risk_manager.risk_metrics.win_rate = 0.8
        
        position_size = risk_manager.calculate_position_size(100.0, 0.02)
        self.assertGreater(position_size, 0)
        
    def test_fallback_behavior(self):
        """Test system behavior when volume weighting fails."""
        risk_manager = RiskManager(self.config)
        
        # Disable volume weighting
        risk_manager.market_analyzer = None
        
        buy_prices, sell_prices = risk_manager.get_optimal_grid_levels(100.0)
        
        # Should still work with P1+P2
        self.assertGreater(len(buy_prices), 0)
        self.assertGreater(len(sell_prices), 0)


class TestPerformanceAndStress(unittest.TestCase):
    """Test performance and stress scenarios."""
    
    def test_large_order_book_processing(self):
        """Test processing of large order books."""
        config = {'min_volume_strength': 0.3, 'volume_adjustment_tolerance': 0.02}
        analyzer = MarketAnalyzer(config)
        
        # Generate large order book (1000 orders per side)
        large_bids = [[100 - i * 0.01, 1000 - i] for i in range(1000)]
        large_asks = [[100 + i * 0.01, 1000 - i] for i in range(1000)]
        
        order_book = {'bids': large_bids, 'asks': large_asks}
        
        start_time = time.time()
        analysis = analyzer.analyze_market_depth(order_book, 100.0)
        processing_time = time.time() - start_time
        
        # Should complete within reasonable time (< 1 second)
        self.assertLess(processing_time, 1.0)
        self.assertIsNotNone(analysis)
        
    def test_cache_performance(self):
        """Test caching performance improvement."""
        config = {'market_analysis_cache_duration': 30}
        analyzer = MarketAnalyzer(config)
        
        order_book = {
            'bids': [[99.5, 1000.0]] * 100,
            'asks': [[100.5, 1000.0]] * 100
        }
        
        # First call (no cache)
        start_time = time.time()
        analysis1 = analyzer.analyze_market_depth(order_book, 100.0)
        first_call_time = time.time() - start_time
        
        # Second call (cached)
        start_time = time.time()
        analysis2 = analyzer.analyze_market_depth(order_book, 100.0)
        second_call_time = time.time() - start_time
        
        # Cached call should be faster
        self.assertLess(second_call_time, first_call_time)
        self.assertEqual(analysis1.timestamp, analysis2.timestamp)


def run_comprehensive_tests():
    """Run all test suites and provide summary."""
    test_suites = [
        TestMarketAnalyzer,
        TestRiskManagerIntegration,
        TestAPIClientMarketDepth,
        TestIntegrationScenarios,
        TestPerformanceAndStress
    ]
    
    total_tests = 0
    total_failures = 0
    
    for suite_class in test_suites:
        print(f"\n{'='*50}")
        print(f"Running {suite_class.__name__}")
        print(f"{'='*50}")
        
        suite = unittest.TestLoader().loadTestsFromTestCase(suite_class)
        result = unittest.TextTestRunner(verbosity=2).run(suite)
        
        total_tests += result.testsRun
        total_failures += len(result.failures) + len(result.errors)
        
    print(f"\n{'='*50}")
    print(f"SUMMARY")
    print(f"{'='*50}")
    print(f"Total tests run: {total_tests}")
    print(f"Total failures: {total_failures}")
    print(f"Success rate: {((total_tests - total_failures) / total_tests * 100):.1f}%")
    
    return total_failures == 0


if __name__ == '__main__':
    # Run comprehensive test suite
    success = run_comprehensive_tests()
    
    if success:
        print("\n✅ All tests passed! Volume-weighted grid implementation is ready.")
    else:
        print("\n❌ Some tests failed. Please review and fix issues before deployment.")
        exit(1)