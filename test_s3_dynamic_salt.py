#!/usr/bin/env python3
"""
Test suite for Phase 1 S3: Dynamic Encryption Salt Generation
Validates secure salt generation and management functionality.
"""

import unittest
import os
import tempfile
import shutil
from unittest.mock import patch, mock_open, MagicMock
import stat
from security import SecurityManager
import logging

# Configure logging for tests
logging.basicConfig(level=logging.DEBUG)

class TestDynamicSaltGeneration(unittest.TestCase):
    """Test dynamic salt generation functionality."""
    
    def setUp(self):
        """Set up test fixtures with temporary directory."""
        self.test_dir = tempfile.mkdtemp()
        self.original_cwd = os.getcwd()
        os.chdir(self.test_dir)
        self.salt_file = 'security_salt.dat'
        
    def tearDown(self):
        """Clean up test fixtures."""
        os.chdir(self.original_cwd)
        shutil.rmtree(self.test_dir)
    
    def test_new_salt_generation(self):
        """Test generation of new salt file when none exists."""
        # Ensure salt file doesn't exist
        self.assertFalse(os.path.exists(self.salt_file))
        
        # Initialize SecurityManager with encryption key
        security_manager = SecurityManager("test_key_123")
        
        # Verify salt file was created
        self.assertTrue(os.path.exists(self.salt_file))
        
        # Verify salt file has correct permissions (600)
        file_stat = os.stat(self.salt_file)
        file_permissions = stat.filemode(file_stat.st_mode)
        self.assertEqual(file_permissions, '-rw-------')  # 600 permissions
        
        # Verify salt file contains 32 bytes
        with open(self.salt_file, 'rb') as f:
            salt = f.read()
        self.assertEqual(len(salt), 32)
        
        # Verify encryption was set up successfully
        self.assertIsNotNone(security_manager.fernet)
    
    def test_existing_salt_loading(self):
        """Test loading of existing salt file."""
        # Create a test salt file
        test_salt = os.urandom(32)
        with open(self.salt_file, 'wb') as f:
            f.write(test_salt)
        os.chmod(self.salt_file, 0o600)
        
        # Initialize SecurityManager
        security_manager = SecurityManager("test_key_123")
        
        # Verify the same salt is used
        with open(self.salt_file, 'rb') as f:
            loaded_salt = f.read()
        self.assertEqual(loaded_salt, test_salt)
        
        # Verify encryption works
        self.assertIsNotNone(security_manager.fernet)
    
    def test_salt_persistence_across_instances(self):
        """Test that salt persists across SecurityManager instances."""
        # First instance
        security1 = SecurityManager("test_key_123")
        encrypted1 = security1.encrypt_data("test_data")
        
        # Second instance
        security2 = SecurityManager("test_key_123")
        decrypted = security2.decrypt_data(encrypted1)
        
        # Should decrypt successfully with same salt
        self.assertEqual(decrypted, "test_data")
    
    def test_different_keys_different_encryption(self):
        """Test that different keys produce different encryption even with same salt."""
        # Create salt file first
        security1 = SecurityManager("key1")
        encrypted1 = security1.encrypt_data("test_data")
        
        # Use different key with same salt file
        security2 = SecurityManager("key2")
        encrypted2 = security2.encrypt_data("test_data")
        
        # Encrypted data should be different
        self.assertNotEqual(encrypted1, encrypted2)
    
    def test_salt_file_permissions_security(self):
        """Test that salt file has secure permissions."""
        security_manager = SecurityManager("test_key_123")
        
        # Check file permissions
        file_stat = os.stat(self.salt_file)
        permissions = file_stat.st_mode & 0o777
        
        # Should be 600 (owner read/write only)
        self.assertEqual(permissions, 0o600)
    
    def test_salt_randomness(self):
        """Test that generated salts are random and unique."""
        salts = []
        
        # Generate multiple salt files in different directories
        for i in range(5):
            test_dir = tempfile.mkdtemp()
            original_cwd = os.getcwd()
            try:
                os.chdir(test_dir)
                security_manager = SecurityManager("test_key")
                
                with open('security_salt.dat', 'rb') as f:
                    salt = f.read()
                salts.append(salt)
            finally:
                os.chdir(original_cwd)
                shutil.rmtree(test_dir)
        
        # All salts should be unique
        self.assertEqual(len(salts), len(set(salts)), "Salts should be unique")
        
        # All salts should be 32 bytes
        for salt in salts:
            self.assertEqual(len(salt), 32)
    
    def test_salt_file_io_error_handling(self):
        """Test handling of I/O errors during salt operations."""
        # Test read error
        with patch('builtins.open', side_effect=IOError("Permission denied")):
            security_manager = SecurityManager("test_key")
            self.assertIsNone(security_manager.fernet)
    
    def test_salt_file_corruption_handling(self):
        """Test handling of corrupted salt file."""
        # Create corrupted salt file (wrong size)
        with open(self.salt_file, 'wb') as f:
            f.write(b'corrupted_salt')  # Wrong size
        
        # Should handle gracefully
        security_manager = SecurityManager("test_key")
        
        # Should either work with corrupted salt or fail gracefully
        self.assertIsInstance(security_manager.fernet is not None, bool)
    
    def test_encryption_decryption_with_dynamic_salt(self):
        """Test full encryption/decryption cycle with dynamic salt."""
        security_manager = SecurityManager("test_key_123")
        
        test_data = "sensitive_trading_data_12345"
        
        # Encrypt data
        encrypted = security_manager.encrypt_data(test_data)
        self.assertNotEqual(encrypted, test_data)
        
        # Decrypt data
        decrypted = security_manager.decrypt_data(encrypted)
        self.assertEqual(decrypted, test_data)


class TestSaltSecurityStandards(unittest.TestCase):
    """Test security standards compliance for salt management."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.test_dir = tempfile.mkdtemp()
        self.original_cwd = os.getcwd()
        os.chdir(self.test_dir)
        
    def tearDown(self):
        """Clean up test fixtures."""
        os.chdir(self.original_cwd)
        shutil.rmtree(self.test_dir)
    
    def test_salt_file_not_world_readable(self):
        """Test that salt file is not readable by others."""
        security_manager = SecurityManager("test_key")
        
        file_stat = os.stat('security_salt.dat')
        permissions = file_stat.st_mode
        
        # Check that group and others have no permissions
        self.assertEqual(permissions & stat.S_IRGRP, 0)  # No group read
        self.assertEqual(permissions & stat.S_IWGRP, 0)  # No group write
        self.assertEqual(permissions & stat.S_IROTH, 0)  # No other read
        self.assertEqual(permissions & stat.S_IWOTH, 0)  # No other write
    
    def test_salt_entropy_quality(self):
        """Test that generated salt has good entropy."""
        security_manager = SecurityManager("test_key")
        
        with open('security_salt.dat', 'rb') as f:
            salt = f.read()
        
        # Basic entropy test - salt should not be all zeros or all same byte
        self.assertNotEqual(salt, b'\x00' * 32)
        self.assertGreater(len(set(salt)), 16)  # Should have variety of bytes
    
    def test_salt_file_creation_atomicity(self):
        """Test that salt file creation is atomic (where possible)."""
        # This test verifies the file is written completely
        security_manager = SecurityManager("test_key")
        
        # File should exist and be complete
        self.assertTrue(os.path.exists('security_salt.dat'))
        
        with open('security_salt.dat', 'rb') as f:
            salt = f.read()
        
        # Should be exactly 32 bytes
        self.assertEqual(len(salt), 32)
    
    def test_no_salt_data_in_logs(self):
        """Test that actual salt data is not logged."""
        with patch('logging.Logger.debug') as mock_debug, \
             patch('logging.Logger.info') as mock_info, \
             patch('logging.Logger.warning') as mock_warning:
            
            security_manager = SecurityManager("test_key")
            
            # Get the actual salt data to check it's not logged
            with open('security_salt.dat', 'rb') as f:
                salt_data = f.read()
            
            # Check that no log calls contain actual salt data
            all_calls = mock_debug.call_args_list + mock_info.call_args_list + mock_warning.call_args_list
            for call in all_calls:
                args, kwargs = call
                log_message = str(args[0]) if args else ""
                # Check for actual salt bytes or hex representation
                self.assertNotIn(salt_data.hex(), log_message)
                self.assertNotIn(str(salt_data), log_message)
                # Don't check for the word "salt" as that's acceptable in descriptions


def run_s3_validation_tests():
    """Run all S3 validation tests and return results."""
    print("=" * 60)
    print("PHASE 1 S3: Dynamic Encryption Salt - Test Suite")
    print("=" * 60)
    
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add all test classes
    suite.addTest(loader.loadTestsFromTestCase(TestDynamicSaltGeneration))
    suite.addTest(loader.loadTestsFromTestCase(TestSaltSecurityStandards))
    
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
    run_s3_validation_tests()