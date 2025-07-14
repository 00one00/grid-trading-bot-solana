#!/usr/bin/env python3
"""
Test Suite for S4: Secure API Fallbacks
Tests encryption/decryption fail-secure behavior

Part of Phase 1 Critical Security Hardening
Created: July 13, 2025
"""

import unittest
import tempfile
import os
from unittest.mock import patch, mock_open
from security import SecurityManager


class TestS4SecureFallbacks(unittest.TestCase):
    """Test suite for S4 secure fallback behavior."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.test_data = "sensitive_test_data_123"
        self.encryption_key = "test_encryption_key_123"
        
    def test_encrypt_with_valid_setup(self):
        """Test encryption works with valid setup."""
        with patch('builtins.open', mock_open(read_data=b'test_salt_32_bytes_long_for_testing')):
            with patch('os.path.exists', return_value=True):
                security = SecurityManager(self.encryption_key)
                security._setup_encryption()
                
                encrypted = security.encrypt_data(self.test_data)
                self.assertNotEqual(encrypted, self.test_data)
                self.assertIsInstance(encrypted, str)
                
    def test_encrypt_without_fernet_raises_error(self):
        """Test encryption raises ValueError when fernet is not available."""
        security = SecurityManager()
        security.fernet = None  # Simulate no encryption available
        
        with self.assertRaises(ValueError) as context:
            security.encrypt_data(self.test_data)
            
        self.assertEqual(str(context.exception), "Encryption required but not available")
        
    def test_encrypt_failure_raises_error(self):
        """Test encryption raises ValueError on encryption failure."""
        security = SecurityManager(self.encryption_key)
        
        # Mock fernet to raise exception
        mock_fernet = unittest.mock.Mock()
        mock_fernet.encrypt.side_effect = Exception("Mock encryption error")
        security.fernet = mock_fernet
        
        with self.assertRaises(ValueError) as context:
            security.encrypt_data(self.test_data)
            
        self.assertEqual(str(context.exception), "Failed to encrypt sensitive data")
        
    def test_decrypt_with_valid_data(self):
        """Test decryption works with valid encrypted data."""
        with patch('builtins.open', mock_open(read_data=b'test_salt_32_bytes_long_for_testing')):
            with patch('os.path.exists', return_value=True):
                security = SecurityManager(self.encryption_key)
                security._setup_encryption()
                
                # First encrypt data
                encrypted = security.encrypt_data(self.test_data)
                
                # Then decrypt it
                decrypted = security.decrypt_data(encrypted)
                self.assertEqual(decrypted, self.test_data)
                
    def test_decrypt_without_fernet_raises_error(self):
        """Test decryption raises ValueError when fernet is not available."""
        security = SecurityManager()
        security.fernet = None  # Simulate no decryption available
        
        with self.assertRaises(ValueError) as context:
            security.decrypt_data("fake_encrypted_data")
            
        self.assertEqual(str(context.exception), "Decryption required but not available")
        
    def test_decrypt_failure_raises_error(self):
        """Test decryption raises ValueError on decryption failure."""
        security = SecurityManager(self.encryption_key)
        
        # Mock fernet to raise exception
        mock_fernet = unittest.mock.Mock()
        mock_fernet.decrypt.side_effect = Exception("Mock decryption error")
        security.fernet = mock_fernet
        
        with self.assertRaises(ValueError) as context:
            security.decrypt_data("invalid_encrypted_data")
            
        self.assertEqual(str(context.exception), "Failed to decrypt data")
        
    def test_no_data_leakage_on_encrypt_failure(self):
        """Test that no unencrypted data is returned on encryption failure."""
        security = SecurityManager()
        security.fernet = None
        
        # Ensure ValueError is raised, not data returned
        with self.assertRaises(ValueError):
            result = security.encrypt_data(self.test_data)
            # If we reach here, the test should fail
            self.fail("Expected ValueError but got result: " + str(result))
            
    def test_no_data_leakage_on_decrypt_failure(self):
        """Test that no encrypted data is returned as plaintext on decryption failure."""
        security = SecurityManager()
        security.fernet = None
        
        # Ensure ValueError is raised, not encrypted data returned
        with self.assertRaises(ValueError):
            result = security.decrypt_data("encrypted_data")
            # If we reach here, the test should fail
            self.fail("Expected ValueError but got result: " + str(result))
            
    def test_encryption_roundtrip_secure(self):
        """Test complete encryption/decryption cycle maintains security."""
        with patch('builtins.open', mock_open(read_data=b'test_salt_32_bytes_long_for_testing')):
            with patch('os.path.exists', return_value=True):
                security = SecurityManager(self.encryption_key)
                security._setup_encryption()
                
                # Test multiple rounds
                for i in range(5):
                    test_data = f"test_data_{i}_sensitive_info"
                    encrypted = security.encrypt_data(test_data)
                    decrypted = security.decrypt_data(encrypted)
                    
                    self.assertEqual(decrypted, test_data)
                    self.assertNotEqual(encrypted, test_data)
                    
    def test_fail_secure_behavior_consistency(self):
        """Test that all failure modes are consistent and secure."""
        security = SecurityManager()
        security.fernet = None
        
        # All operations should fail with ValueError
        with self.assertRaises(ValueError):
            security.encrypt_data("test1")
            
        with self.assertRaises(ValueError):
            security.decrypt_data("test2")
            
        # No data should ever be returned unencrypted
        security.encryption_key = self.encryption_key
        mock_fernet = unittest.mock.Mock()
        mock_fernet.encrypt.side_effect = Exception("Encryption failed")
        mock_fernet.decrypt.side_effect = Exception("Decryption failed")
        security.fernet = mock_fernet
        
        with self.assertRaises(ValueError):
            security.encrypt_data("test3")
            
        with self.assertRaises(ValueError):
            security.decrypt_data("test4")


def run_s4_tests():
    """Run S4 secure fallback tests with detailed output."""
    print("=" * 70)
    print("S4 SECURE API FALLBACKS - VALIDATION TEST SUITE")
    print("=" * 70)
    print("Testing fail-secure behavior for encryption/decryption methods")
    print()
    
    # Create test suite
    suite = unittest.TestLoader().loadTestsFromTestCase(TestS4SecureFallbacks)
    
    # Run tests with detailed output
    runner = unittest.TextTestRunner(verbosity=2, stream=None)
    result = runner.run(suite)
    
    # Summary
    print("\n" + "=" * 70)
    print("S4 SECURE FALLBACK TEST RESULTS")
    print("=" * 70)
    print(f"Tests Run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print(f"Success Rate: {((result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun * 100):.1f}%")
    
    if result.failures:
        print("\nFAILURES:")
        for test, traceback in result.failures:
            print(f"- {test}: {traceback}")
            
    if result.errors:
        print("\nERRORS:")
        for test, traceback in result.errors:
            print(f"- {test}: {traceback}")
    
    if not result.failures and not result.errors:
        print("\n✅ ALL S4 SECURE FALLBACK TESTS PASSED!")
        print("✅ Encryption/decryption methods now fail-secure")
        print("✅ No sensitive data can be accidentally exposed")
        print("✅ S4 implementation meets enterprise security standards")
    else:
        print("\n❌ SOME TESTS FAILED - S4 implementation needs review")
    
    print("=" * 70)
    
    return len(result.failures) == 0 and len(result.errors) == 0


if __name__ == "__main__":
    success = run_s4_tests()
    exit(0 if success else 1)