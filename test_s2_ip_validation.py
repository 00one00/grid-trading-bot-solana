#!/usr/bin/env python3
"""
Test suite for Phase 1 S2: External IP Validation Fix
Validates enhanced IP detection with security standards.
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
import requests
from security import SecurityManager
import logging

# Configure logging for tests
logging.basicConfig(level=logging.DEBUG)

class TestEnhancedIPValidation(unittest.TestCase):
    """Test enhanced IP validation functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.security_manager = SecurityManager()
        self.test_whitelist = ["192.168.1.100", "203.0.113.45"]
        
    def test_empty_whitelist_bypass(self):
        """Test that empty whitelist returns True (bypass)."""
        result = self.security_manager.validate_ip([])
        self.assertTrue(result)
        
    def test_valid_ip_in_whitelist(self):
        """Test successful validation with IP in whitelist."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = "192.168.1.100"
        
        with patch('requests.get', return_value=mock_response):
            result = self.security_manager.validate_ip(self.test_whitelist)
            self.assertTrue(result)
    
    def test_valid_ip_not_in_whitelist(self):
        """Test rejection when IP not in whitelist."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = "192.168.1.200"  # Not in whitelist
        
        with patch('requests.get', return_value=mock_response):
            result = self.security_manager.validate_ip(self.test_whitelist)
            self.assertFalse(result)
    
    def test_fallback_to_second_service(self):
        """Test fallback when first service fails."""
        # First call fails, second succeeds
        responses = [
            requests.exceptions.Timeout(),
            Mock(status_code=200, text="192.168.1.100")
        ]
        
        with patch('requests.get', side_effect=responses):
            result = self.security_manager.validate_ip(self.test_whitelist)
            self.assertTrue(result)
    
    def test_all_services_fail(self):
        """Test fail-secure behavior when all services fail."""
        with patch('requests.get', side_effect=requests.exceptions.Timeout()):
            result = self.security_manager.validate_ip(self.test_whitelist)
            self.assertFalse(result)  # Should fail secure
    
    def test_invalid_ip_format_rejection(self):
        """Test rejection of invalid IP format."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = "invalid.ip.format"
        
        with patch('requests.get', return_value=mock_response):
            result = self.security_manager.validate_ip(self.test_whitelist)
            self.assertFalse(result)  # Should fail due to invalid format
    
    def test_timeout_handling(self):
        """Test proper timeout handling."""
        with patch('requests.get', side_effect=requests.exceptions.Timeout()):
            # Should try all services and fail secure
            result = self.security_manager.validate_ip(self.test_whitelist)
            self.assertFalse(result)
    
    def test_network_error_handling(self):
        """Test handling of network errors."""
        with patch('requests.get', side_effect=requests.exceptions.ConnectionError()):
            result = self.security_manager.validate_ip(self.test_whitelist)
            self.assertFalse(result)  # Should fail secure
    
    def test_ipv4_format_validation(self):
        """Test IPv4 format validation."""
        # Valid IPv4 addresses
        valid_ips = ["192.168.1.1", "10.0.0.1", "255.255.255.255", "0.0.0.0"]
        for ip in valid_ips:
            self.assertTrue(self.security_manager._is_valid_ip_format(ip), f"Failed for valid IP: {ip}")
        
        # Invalid IPv4 addresses
        invalid_ips = ["256.1.1.1", "192.168.1", "192.168.1.1.1", "abc.def.ghi.jkl"]
        for ip in invalid_ips:
            self.assertFalse(self.security_manager._is_valid_ip_format(ip), f"Failed for invalid IP: {ip}")
    
    def test_ipv6_format_validation(self):
        """Test IPv6 format validation."""
        # Valid IPv6 addresses
        valid_ips = ["2001:0db8:85a3:0000:0000:8a2e:0370:7334", "::1", "::"]
        for ip in valid_ips:
            self.assertTrue(self.security_manager._is_valid_ip_format(ip), f"Failed for valid IPv6: {ip}")
        
        # Invalid IPv6 addresses
        invalid_ips = ["gggg::1", "2001:0db8:85a3::8a2e::7334", ""]
        for ip in invalid_ips:
            self.assertFalse(self.security_manager._is_valid_ip_format(ip), f"Failed for invalid IPv6: {ip}")
    
    def test_service_rotation(self):
        """Test that multiple services are attempted."""
        call_count = 0
        
        def mock_get(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 3:  # Third service succeeds
                response = Mock()
                response.status_code = 200
                response.text = "192.168.1.100"
                return response
            else:
                raise requests.exceptions.Timeout()
        
        with patch('requests.get', side_effect=mock_get):
            result = self.security_manager.validate_ip(self.test_whitelist)
            self.assertTrue(result)
            self.assertEqual(call_count, 3)  # Should have tried 3 services
    
    def test_security_headers(self):
        """Test that security headers are included in requests."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = "192.168.1.100"
        
        with patch('requests.get', return_value=mock_response) as mock_get:
            self.security_manager.validate_ip(self.test_whitelist)
            
            # Verify User-Agent header was included
            mock_get.assert_called_with(
                unittest.mock.ANY,
                timeout=5,
                headers={'User-Agent': 'TradingBot/1.0'}
            )


class TestSecurityStandards(unittest.TestCase):
    """Test security standards compliance."""
    
    def setUp(self):
        self.security_manager = SecurityManager()
    
    def test_fail_secure_behavior(self):
        """Test that system fails secure on all error conditions."""
        error_conditions = [
            requests.exceptions.Timeout(),
            requests.exceptions.ConnectionError(),
            requests.exceptions.HTTPError(),
            Exception("Unexpected error")
        ]
        
        for error in error_conditions:
            with patch('requests.get', side_effect=error):
                result = self.security_manager.validate_ip(["192.168.1.100"])
                self.assertFalse(result, f"Should fail secure for {type(error).__name__}")
    
    def test_input_validation(self):
        """Test input validation and sanitization."""
        # Test with None input (should be handled gracefully)
        result = self.security_manager.validate_ip(None)
        self.assertTrue(result)  # None should bypass validation
        
        # Test with string input (should convert to empty list behavior or handle gracefully)
        try:
            result = self.security_manager.validate_ip("192.168.1.100")
            # If no error, it should handle gracefully
            self.assertIsInstance(result, bool)
        except TypeError:
            # If TypeError is raised, that's also acceptable
            pass
    
    def test_timeout_enforcement(self):
        """Test that timeouts are properly enforced."""
        with patch('requests.get') as mock_get:
            self.security_manager.validate_ip(["192.168.1.100"])
            
            # Verify timeout parameter is set
            args, kwargs = mock_get.call_args
            self.assertEqual(kwargs['timeout'], 5)


def run_validation_tests():
    """Run all validation tests and return results."""
    print("=" * 60)
    print("PHASE 1 S2: IP Validation Enhancement - Test Suite")
    print("=" * 60)
    
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add all test classes
    suite.addTest(loader.loadTestsFromTestCase(TestEnhancedIPValidation))
    suite.addTest(loader.loadTestsFromTestCase(TestSecurityStandards))
    
    # Run tests with detailed output
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print(f"Success rate: {((result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun * 100):.1f}%")
    
    if result.failures:
        print(f"\nFAILURES:")
        for test, traceback in result.failures:
            print(f"- {test}: {traceback}")
    
    if result.errors:
        print(f"\nERRORS:")
        for test, traceback in result.errors:
            print(f"- {test}: {traceback}")
    
    success = len(result.failures) == 0 and len(result.errors) == 0
    print(f"\nOVERALL RESULT: {'PASS' if success else 'FAIL'}")
    
    return success


if __name__ == "__main__":
    run_validation_tests()