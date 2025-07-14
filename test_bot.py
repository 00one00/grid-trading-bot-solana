#!/usr/bin/env python3
"""
Test script for Solana Grid Trading Bot
=======================================

This script tests all components of the trading bot without making real API calls.
Useful for validating configuration and logic before live trading.
"""

import sys
import os
import unittest
from unittest.mock import Mock, patch, MagicMock
import tempfile
import json

# Add current directory to path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config import Config
from security import SecurityManager
from risk_manager import RiskManager, Position
from api_client import APIClient
from grid_trading_bot import GridTradingBot, GridLevel

class TestConfig(unittest.TestCase):
    """Test configuration management."""
    
    def setUp(self):
        """Set up test environment."""
        # Create temporary environment variables
        os.environ['API_KEY'] = 'test_api_key'
        os.environ['API_SECRET'] = 'test_api_secret'
        os.environ['CAPITAL'] = '250.0'
        os.environ['TRADING_PAIR'] = 'SOL/USDC'
        os.environ['RISK_PER_TRADE'] = '0.02'

    def test_config_validation(self):
        """Test configuration validation."""
        config = Config()
        self.assertTrue(config.validate())
    
    def test_config_invalid_capital(self):
        """Test invalid capital configuration."""
        os.environ['CAPITAL'] = '0'
        config = Config()
        with self.assertRaises(ValueError):
            config.validate()
    
    def test_config_invalid_risk(self):
        """Test invalid risk configuration."""
        os.environ['RISK_PER_TRADE'] = '0.15'  # 15% - too high
        config = Config()
        with self.assertRaises(ValueError):
            config.validate()

class TestSecurityManager(unittest.TestCase):
    """Test security manager functionality."""
    
    def setUp(self):
        """Set up test environment."""
        self.security_manager = SecurityManager("test_encryption_key")
    
    def test_signature_generation(self):
        """Test HMAC signature generation."""
        params = {"test": "value", "timestamp": "1234567890"}
        signature = self.security_manager.generate_signature(
            "test_secret", "1234567890", "/test/endpoint", params
        )
        self.assertIsInstance(signature, str)
        self.assertEqual(len(signature), 64)  # SHA256 hex length
    
    def test_secure_headers(self):
        """Test secure header generation."""
        headers = self.security_manager.create_secure_headers(
            "test_key", "test_secret", "/test/endpoint", {"test": "value"}
        )
        required_fields = ["API-Key", "Timestamp", "Signature", "Content-Type"]
        for field in required_fields:
            self.assertIn(field, headers)
    
    def test_data_sanitization(self):
        """Test data sanitization for logging."""
        test_data = {
            "api_key": "secret_key",
            "normal_field": "normal_value",
            "api_secret": "secret_value"
        }
        sanitized = self.security_manager.sanitize_log_data(test_data)
        
        self.assertEqual(sanitized["api_key"], "***REDACTED***")
        self.assertEqual(sanitized["api_secret"], "***REDACTED***")
        self.assertEqual(sanitized["normal_field"], "normal_value")

class TestRiskManager(unittest.TestCase):
    """Test risk manager functionality."""
    
    def setUp(self):
        """Set up test environment."""
        self.config = {
            'capital': 250.0,
            'risk_per_trade': 0.02,
            'max_daily_loss': 0.05,
            'stop_loss_percent': 0.05,
            'profit_target_percent': 0.02,
            'grid_levels': 5,
            'price_range_percent': 0.10
        }
        self.risk_manager = RiskManager(self.config)
    
    def test_position_size_calculation(self):
        """Test position size calculation."""
        current_price = 100.0
        position_size = self.risk_manager.calculate_position_size(
            current_price, 0.02
        )
        
        # Expected: (250 * 0.02) / 100 = 0.05
        expected_size = (250.0 * 0.02) / 100.0
        self.assertAlmostEqual(position_size, expected_size, places=6)
    
    def test_daily_loss_limit(self):
        """Test daily loss limit checking."""
        # Should allow trading initially
        self.risk_manager.risk_metrics.daily_pnl = -5.0  # -$5 loss
        self.assertTrue(self.risk_manager.check_daily_loss_limit())
        
        # Simulate excessive loss
        self.risk_manager.risk_metrics.daily_pnl = -15.0  # -$15 loss
        # Should stop trading (loss > 5% of $250 = $12.5)
        self.assertFalse(self.risk_manager.check_daily_loss_limit())
    
    def test_stop_loss_checking(self):
        """Test stop loss checking."""
        # Add a buy position
        position = Position(
            id="test_buy",
            side="buy",
            quantity=1.0,
            price=100.0,
            timestamp=1234567890,
            status="open"
        )
        self.risk_manager.add_position(position)
        
        # Check stop loss at 95% of buy price (should trigger)
        positions_to_close = self.risk_manager.check_stop_loss(94.0)
        self.assertIn("test_buy", positions_to_close)
        
        # Check stop loss at 96% of buy price (should not trigger)
        positions_to_close = self.risk_manager.check_stop_loss(96.0)
        self.assertNotIn("test_buy", positions_to_close)
    
    def test_grid_level_calculation(self):
        """Test optimal grid level calculation."""
        current_price = 100.0
        buy_prices, sell_prices = self.risk_manager.get_optimal_grid_levels(current_price)
        
        # Should have correct number of levels
        self.assertEqual(len(buy_prices), 5)
        self.assertEqual(len(sell_prices), 5)
        
        # Buy prices should be below current price
        for price in buy_prices:
            self.assertLess(price, current_price)
        
        # Sell prices should be above current price
        for price in sell_prices:
            self.assertGreater(price, current_price)

class TestAPIClient(unittest.TestCase):
    """Test API client functionality."""
    
    def setUp(self):
        """Set up test environment."""
        self.config = Config()
        self.security_manager = SecurityManager()
        self.api_client = APIClient(self.config, self.security_manager)
    
    @patch('requests.Session')
    def test_market_price_fetch(self, mock_session):
        """Test market price fetching."""
        # Mock successful response
        mock_response = Mock()
        mock_response.json.return_value = {"price": "100.50"}
        mock_response.raise_for_status.return_value = None
        
        mock_session_instance = Mock()
        mock_session_instance.get.return_value = mock_response
        mock_session.return_value = mock_session_instance
        
        # Test price fetching
        with patch.object(self.api_client, 'session', mock_session_instance):
            price = self.api_client.get_market_price("SOL/USDC")
            self.assertEqual(price, 100.50)
    
    @patch('requests.Session')
    def test_order_placement(self, mock_session):
        """Test order placement."""
        # Mock successful response
        mock_response = Mock()
        mock_response.json.return_value = {"id": "test_order_id", "status": "open"}
        mock_response.raise_for_status.return_value = None
        
        mock_session_instance = Mock()
        mock_session_instance.post.return_value = mock_response
        mock_session.return_value = mock_session_instance
        
        # Test order placement
        with patch.object(self.api_client, 'session', mock_session_instance):
            order = self.api_client.place_order(
                "SOL/USDC", "buy", "limit", 1.0, 100.0
            )
            self.assertEqual(order["id"], "test_order_id")

class TestGridTradingBot(unittest.TestCase):
    """Test grid trading bot functionality."""
    
    def setUp(self):
        """Set up test environment."""
        self.config = Config()
        self.bot = GridTradingBot(self.config)
    
    def test_grid_initialization(self):
        """Test grid initialization."""
        current_price = 100.0
        self.bot._initialize_grid(current_price)
        
        # Should have correct number of grid levels
        self.assertEqual(len(self.bot.grid_levels), 5)
        
        # Each level should have buy and sell prices
        for level in self.bot.grid_levels:
            self.assertIsInstance(level.buy_price, float)
            self.assertIsInstance(level.sell_price, float)
            self.assertLess(level.buy_price, current_price)
            self.assertGreater(level.sell_price, current_price)
    
    def test_grid_level_creation(self):
        """Test grid level creation."""
        level = GridLevel(
            level=1,
            buy_price=95.0,
            sell_price=105.0
        )
        
        self.assertEqual(level.level, 1)
        self.assertEqual(level.buy_price, 95.0)
        self.assertEqual(level.sell_price, 105.0)
        self.assertFalse(level.buy_filled)
        self.assertFalse(level.sell_filled)

def run_tests():
    """Run all tests."""
    print("🧪 Running Solana Grid Trading Bot Tests")
    print("=" * 50)
    
    # Create test suite
    test_suite = unittest.TestSuite()
    
    # Add test cases
    test_suite.addTest(unittest.TestLoader().loadTestsFromTestCase(TestConfig))
    test_suite.addTest(unittest.TestLoader().loadTestsFromTestCase(TestSecurityManager))
    test_suite.addTest(unittest.TestLoader().loadTestsFromTestCase(TestRiskManager))
    test_suite.addTest(unittest.TestLoader().loadTestsFromTestCase(TestAPIClient))
    test_suite.addTest(unittest.TestLoader().loadTestsFromTestCase(TestGridTradingBot))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(test_suite)
    
    # Print summary
    print("\n" + "=" * 50)
    print("📊 Test Results Summary")
    print("=" * 50)
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    
    if result.failures:
        print("\n❌ Failures:")
        for test, traceback in result.failures:
            print(f"  - {test}: {traceback}")
    
    if result.errors:
        print("\n❌ Errors:")
        for test, traceback in result.errors:
            print(f"  - {test}: {traceback}")
    
    if result.wasSuccessful():
        print("\n✅ All tests passed!")
        return True
    else:
        print("\n❌ Some tests failed!")
        return False

if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1) 