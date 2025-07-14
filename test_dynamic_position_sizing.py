#!/usr/bin/env python3
"""
Test Suite for Dynamic Position Sizing (Phase 2 P2)
===================================================

Comprehensive testing for the dynamic position sizing implementation
with performance-based scaling, capital compounding, and small account optimizations.
"""

import unittest
import sys
import os

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from risk_manager import RiskManager, Position, RiskMetrics
from config import Config
import time


class TestDynamicPositionSizing(unittest.TestCase):
    """Test suite for dynamic position sizing functionality."""
    
    def setUp(self):
        """Set up test environment."""
        # Create test configuration for small capital account
        self.test_config = {
            'trading_pair': 'SOL/USDC',
            'capital': 400.0,  # Small capital for testing
            'grid_levels': 5,
            'price_range_percent': 0.10,
            'risk_per_trade': 0.02,
            'max_daily_loss': 0.05,
            'stop_loss_percent': 0.05,
            'profit_target_percent': 0.02,
            'micro_grid_mode': True,
            'adaptive_spacing': True,
            'min_grid_spacing': 0.005,
            'max_grid_spacing': 0.03,
            'volatility_lookback': 24,
            'small_capital_threshold': 1000,
            'micro_capital_threshold': 500,
            'grid_density_multiplier': 2.0,
            # Dynamic sizing parameters
            'dynamic_sizing': True,
            'min_risk_per_trade': 0.01,
            'max_risk_per_trade': 0.05,
            'performance_scaling': True,
            'compound_profits': True,
            'win_rate_threshold_high': 0.7,
            'win_rate_threshold_low': 0.5,
            'risk_scaling_factor': 1.5,
            'small_account_boost': 1.2
        }
        
        self.risk_manager = RiskManager(self.test_config)
        self.test_price = 100.0  # $100 per unit
        self.base_risk = 0.02  # 2% base risk
    
    def test_effective_capital_calculation(self):
        """Test effective capital calculation with profit compounding."""
        print("\n=== Testing Effective Capital Calculation ===")
        
        # Test base capital (no profits yet)
        effective_capital = self.risk_manager._get_effective_capital()
        self.assertEqual(effective_capital, 400.0)
        print(f"✓ Base capital: ${effective_capital:.2f}")
        
        # Add some profitable positions
        profitable_position = Position(
            id="test_1",
            side="buy",
            quantity=0.05,
            price=100.0,
            timestamp=time.time(),
            status="filled",
            profit_loss=20.0  # $20 profit
        )
        self.risk_manager.positions.append(profitable_position)
        
        # Test capital with compounded profits
        effective_capital = self.risk_manager._get_effective_capital()
        expected_capital = 400.0 + 20.0  # Base + profit
        self.assertEqual(effective_capital, expected_capital)
        print(f"✓ Capital with profits: ${effective_capital:.2f}")
        
        # Test capital compounding limit (should cap at 2x original)
        large_profit_position = Position(
            id="test_2",
            side="sell",
            quantity=0.1,
            price=95.0,
            timestamp=time.time(),
            status="filled",
            profit_loss=500.0  # Large $500 profit
        )
        self.risk_manager.positions.append(large_profit_position)
        
        effective_capital = self.risk_manager._get_effective_capital()
        max_expected_capital = 400.0 + 400.0  # Base + max 1x original capital
        self.assertEqual(effective_capital, max_expected_capital)
        print(f"✓ Capital with large profits (capped): ${effective_capital:.2f}")
    
    def test_dynamic_risk_calculation(self):
        """Test dynamic risk calculation based on performance."""
        print("\n=== Testing Dynamic Risk Calculation ===")
        
        # Test with insufficient trades (should return base risk)
        dynamic_risk = self.risk_manager._calculate_dynamic_risk(self.base_risk)
        self.assertEqual(dynamic_risk, self.base_risk)
        print(f"✓ Insufficient trades: {dynamic_risk:.1%} (base risk)")
        
        # Simulate high performance (80% win rate)
        self.risk_manager.risk_metrics.total_trades = 20
        self.risk_manager.risk_metrics.winning_trades = 16
        self.risk_manager.risk_metrics.win_rate = 0.8
        
        # Add recent profitable positions for performance trend
        for i in range(10):
            position = Position(
                id=f"win_{i}",
                side="buy",
                quantity=0.02,
                price=100.0,
                timestamp=time.time(),
                status="filled",
                profit_loss=5.0  # Profitable
            )
            self.risk_manager.positions.append(position)
        
        dynamic_risk = self.risk_manager._calculate_dynamic_risk(self.base_risk)
        self.assertGreater(dynamic_risk, self.base_risk)
        self.assertLessEqual(dynamic_risk, self.test_config['max_risk_per_trade'])
        print(f"✓ High performance (80% win rate): {dynamic_risk:.1%}")
        
        # Test low performance (30% win rate)
        self.risk_manager.risk_metrics.winning_trades = 6
        self.risk_manager.risk_metrics.win_rate = 0.3
        
        # Add recent losing positions
        for i in range(10):
            position = Position(
                id=f"loss_{i}",
                side="sell",
                quantity=0.02,
                price=100.0,
                timestamp=time.time(),
                status="filled",
                profit_loss=-3.0  # Loss
            )
            self.risk_manager.positions.append(position)
        
        dynamic_risk = self.risk_manager._calculate_dynamic_risk(self.base_risk)
        self.assertLess(dynamic_risk, self.base_risk)
        self.assertGreaterEqual(dynamic_risk, self.test_config['min_risk_per_trade'])
        print(f"✓ Low performance (30% win rate): {dynamic_risk:.1%}")
    
    def test_small_account_optimizations(self):
        """Test position sizing optimizations for small accounts."""
        print("\n=== Testing Small Account Optimizations ===")
        
        # Test micro account (under $500)
        micro_config = self.test_config.copy()
        micro_config['capital'] = 300.0
        micro_risk_manager = RiskManager(micro_config)
        
        optimized_risk = micro_risk_manager._apply_small_account_optimizations(0.02, 300.0)
        self.assertGreaterEqual(optimized_risk, 0.02)  # Should be boosted
        print(f"✓ Micro account ($300): {optimized_risk:.1%} risk")
        
        # Test small account (under $1000 but over $500)
        optimized_risk = self.risk_manager._apply_small_account_optimizations(0.02, 600.0)
        expected_boost = 0.02 * self.test_config['small_account_boost']
        self.assertAlmostEqual(optimized_risk, expected_boost, places=4)
        print(f"✓ Small account ($600): {optimized_risk:.1%} risk")
        
        # Test that $400 is treated as micro account (under $500)
        optimized_risk_400 = self.risk_manager._apply_small_account_optimizations(0.02, 400.0)
        expected_micro_risk = max(0.02, 0.02 * 1.5)  # max(base, 1.5x base)
        self.assertAlmostEqual(optimized_risk_400, expected_micro_risk, places=4)
        print(f"✓ Account $400 (micro): {optimized_risk_400:.1%} risk")
        
        # Test regular account (over $1000)
        large_config = self.test_config.copy()
        large_config['capital'] = 1500.0
        large_risk_manager = RiskManager(large_config)
        
        optimized_risk = large_risk_manager._apply_small_account_optimizations(0.02, 1500.0)
        self.assertEqual(optimized_risk, 0.02)  # No boost for large accounts
        print(f"✓ Large account ($1500): {optimized_risk:.1%} risk (no boost)")
    
    def test_exposure_limits(self):
        """Test dynamic exposure limits based on account size."""
        print("\n=== Testing Dynamic Exposure Limits ===")
        
        # Test micro account (90% exposure limit)
        micro_config = self.test_config.copy()
        micro_config['capital'] = 300.0
        micro_risk_manager = RiskManager(micro_config)
        
        # Test position that would be within limits
        small_position_size = 0.5  # $50 value at $100 price
        within_limits = micro_risk_manager._check_exposure_limits(small_position_size, 100.0, 300.0)
        self.assertTrue(within_limits)
        print(f"✓ Micro account: ${small_position_size * 100:.0f} position within 90% limit")
        
        # Test position that would exceed limits
        large_position_size = 3.0  # $300 value at $100 price (100% of capital)
        exceeds_limits = micro_risk_manager._check_exposure_limits(large_position_size, 100.0, 300.0)
        self.assertFalse(exceeds_limits)
        print(f"✓ Micro account: ${large_position_size * 100:.0f} position exceeds 90% limit")
        
        # Test small account (85% exposure limit)
        medium_position_size = 3.2  # $320 value at $100 price (80% of $400 capital)
        within_limits = self.risk_manager._check_exposure_limits(medium_position_size, 100.0, 400.0)
        self.assertTrue(within_limits)
        print(f"✓ Small account: ${medium_position_size * 100:.0f} position within 85% limit")
    
    def test_minimum_position_calculation(self):
        """Test minimum viable position calculations."""
        print("\n=== Testing Minimum Position Calculation ===")
        
        # Test with normal price
        min_position = self.risk_manager._calculate_minimum_position(100.0, 400.0)
        expected_min_value = max(1.0, 400.0 * 0.001)  # $1 or 0.1% of capital
        expected_min_position = expected_min_value / 100.0
        self.assertAlmostEqual(min_position, expected_min_position, places=6)
        print(f"✓ Minimum position at $100: {min_position:.6f} units (${min_position * 100:.2f})")
        
        # Test with high price
        min_position_high_price = self.risk_manager._calculate_minimum_position(1000.0, 400.0)
        expected_min_position_high = expected_min_value / 1000.0
        self.assertAlmostEqual(min_position_high_price, expected_min_position_high, places=6)
        print(f"✓ Minimum position at $1000: {min_position_high_price:.6f} units (${min_position_high_price * 1000:.2f})")
    
    def test_full_position_sizing_integration(self):
        """Test complete position sizing with all components."""
        print("\n=== Testing Full Position Sizing Integration ===")
        
        # Test new account (no trading history)
        position_size = self.risk_manager.calculate_position_size(100.0, 0.02)
        self.assertGreater(position_size, 0)
        position_value = position_size * 100.0
        print(f"✓ New account position: {position_size:.6f} units (${position_value:.2f})")
        
        # Simulate successful trading history
        self.risk_manager.risk_metrics.total_trades = 15
        self.risk_manager.risk_metrics.winning_trades = 12
        self.risk_manager.risk_metrics.win_rate = 0.8
        
        # Add profitable positions for compounding
        for i in range(5):
            position = Position(
                id=f"profit_{i}",
                side="buy",
                quantity=0.03,
                price=100.0,
                timestamp=time.time(),
                status="filled",
                profit_loss=15.0
            )
            self.risk_manager.positions.append(position)
        
        # Test with high performance
        position_size_high_perf = self.risk_manager.calculate_position_size(100.0, 0.02)
        self.assertGreater(position_size_high_perf, position_size)
        position_value_high_perf = position_size_high_perf * 100.0
        print(f"✓ High performance position: {position_size_high_perf:.6f} units (${position_value_high_perf:.2f})")
        
        # Calculate improvement
        improvement = ((position_size_high_perf - position_size) / position_size) * 100
        print(f"✓ Performance improvement: {improvement:.1f}%")
        
        # Verify all safety checks
        effective_capital = self.risk_manager._get_effective_capital()
        max_risk = self.test_config['max_risk_per_trade']
        max_position_value = effective_capital * max_risk
        self.assertLessEqual(position_value_high_perf, max_position_value * 1.1)  # Allow small margin for boosts
        print(f"✓ Position stays within safety limits")
    
    def test_performance_scaling_boundaries(self):
        """Test performance scaling at boundary conditions."""
        print("\n=== Testing Performance Scaling Boundaries ===")
        
        # Test maximum performance multiplier
        self.risk_manager.risk_metrics.total_trades = 20
        self.risk_manager.risk_metrics.winning_trades = 20
        self.risk_manager.risk_metrics.win_rate = 1.0  # 100% win rate
        
        # Add all winning positions
        for i in range(20):
            position = Position(
                id=f"big_win_{i}",
                side="buy",
                quantity=0.02,
                price=100.0,
                timestamp=time.time(),
                status="filled",
                profit_loss=10.0
            )
            self.risk_manager.positions.append(position)
        
        multiplier = self.risk_manager._get_performance_multiplier(1.0, 1.0)
        self.assertLessEqual(multiplier, 2.0)  # Should not exceed 2x
        print(f"✓ Maximum performance multiplier: {multiplier:.2f}x (capped at 2.0x)")
        
        # Test minimum performance multiplier
        self.risk_manager.risk_metrics.winning_trades = 0
        self.risk_manager.risk_metrics.win_rate = 0.0  # 0% win rate
        
        multiplier_min = self.risk_manager._get_performance_multiplier(0.0, -1.0)
        self.assertGreaterEqual(multiplier_min, 0.5)  # Should not go below 0.5x
        print(f"✓ Minimum performance multiplier: {multiplier_min:.2f}x (floored at 0.5x)")
    
    def test_integration_with_existing_systems(self):
        """Test integration with existing micro-grid and risk management."""
        print("\n=== Testing Integration with Existing Systems ===")
        
        # Test that original risk management functions still work
        self.assertTrue(self.risk_manager.should_continue_trading())
        print("✓ Risk management integration: should_continue_trading() works")
        
        # Test that grid calculation still works (micro-grid P1)
        buy_prices, sell_prices = self.risk_manager.get_optimal_grid_levels(100.0)
        self.assertGreater(len(buy_prices), 0)
        self.assertGreater(len(sell_prices), 0)
        print(f"✓ Grid integration: {len(buy_prices)} buy levels, {len(sell_prices)} sell levels")
        
        # Test position management
        test_position = Position(
            id="integration_test",
            side="buy",
            quantity=0.05,
            price=100.0,
            timestamp=time.time(),
            status="open"
        )
        self.risk_manager.add_position(test_position)
        exposure = self.risk_manager.get_current_exposure()
        self.assertEqual(exposure, 5.0)  # 0.05 * 100.0
        print(f"✓ Position management integration: ${exposure:.2f} exposure calculated")
        
        # Test performance summary
        summary = self.risk_manager.get_performance_summary()
        self.assertIn('total_pnl', summary)
        self.assertIn('win_rate', summary)
        print("✓ Performance summary integration works")


def run_comprehensive_tests():
    """Run comprehensive test suite with detailed output."""
    print("=" * 70)
    print("DYNAMIC POSITION SIZING TEST SUITE (Phase 2 P2)")
    print("=" * 70)
    print("Testing performance-based scaling, capital compounding,")
    print("and small account optimizations for the grid trading bot.")
    print("=" * 70)
    
    # Create test suite
    suite = unittest.TestSuite()
    
    # Add all test methods
    test_methods = [
        'test_effective_capital_calculation',
        'test_dynamic_risk_calculation',
        'test_small_account_optimizations',
        'test_exposure_limits',
        'test_minimum_position_calculation',
        'test_full_position_sizing_integration',
        'test_performance_scaling_boundaries',
        'test_integration_with_existing_systems'
    ]
    
    for method in test_methods:
        suite.addTest(TestDynamicPositionSizing(method))
    
    # Run tests with detailed output
    runner = unittest.TextTestRunner(verbosity=2, stream=sys.stdout)
    result = runner.run(suite)
    
    # Print summary
    print("\n" + "=" * 70)
    print("TEST RESULTS SUMMARY")
    print("=" * 70)
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    
    if result.failures:
        print("\nFAILURES:")
        for test, traceback in result.failures:
            print(f"- {test}: {traceback}")
    
    if result.errors:
        print("\nERRORS:")
        for test, traceback in result.errors:
            print(f"- {test}: {traceback}")
    
    if result.wasSuccessful():
        print("\n🎉 ALL TESTS PASSED! Dynamic Position Sizing (P2) is working correctly.")
        print("\nKey Features Validated:")
        print("✓ Performance-based risk scaling (1-5% range)")
        print("✓ Automatic profit compounding (up to 2x capital)")
        print("✓ Small account optimizations (20-50% boost)")
        print("✓ Dynamic exposure limits (80-90% based on size)")
        print("✓ Integration with micro-grid strategy (P1)")
        print("✓ Comprehensive safety mechanisms")
    else:
        print("\n❌ SOME TESTS FAILED! Please review the implementation.")
    
    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_comprehensive_tests()
    sys.exit(0 if success else 1)