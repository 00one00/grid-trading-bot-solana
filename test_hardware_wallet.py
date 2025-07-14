#!/usr/bin/env python3
"""
Test script for hardware wallet integration
"""

import os
import sys
from config import Config
from solana_wallet import SolanaWallet

def test_config_validation():
    """Test configuration validation for hardware wallets."""
    print("Testing configuration validation...")
    
    # Test software wallet validation
    os.environ['WALLET_TYPE'] = 'software'
    os.environ['PRIVATE_KEY'] = 'test_key'
    try:
        Config.validate()
        print("✓ Software wallet config validation passed")
    except Exception as e:
        print(f"✗ Software wallet config validation failed: {e}")
    
    # Test hardware wallet validation
    os.environ['WALLET_TYPE'] = 'ledger'
    os.environ['HARDWARE_DERIVATION_PATH'] = "44'/501'/0'/0'"
    try:
        Config.validate()
        print("✓ Hardware wallet config validation passed")
    except Exception as e:
        print(f"✗ Hardware wallet config validation failed: {e}")
    
    # Test invalid wallet type
    os.environ['WALLET_TYPE'] = 'invalid'
    try:
        Config.validate()
        print("✗ Invalid wallet type should have failed")
    except Exception as e:
        print(f"✓ Invalid wallet type correctly rejected: {e}")

def test_software_wallet():
    """Test software wallet initialization."""
    print("\nTesting software wallet...")
    
    try:
        # Create a valid test keypair for testing
        from solders.keypair import Keypair
        import base58
        test_keypair = Keypair()
        # Get the private key bytes and encode as base58
        test_key = base58.b58encode(bytes(test_keypair)).decode('ascii')
        
        wallet = SolanaWallet(
            private_key=test_key,
            wallet_type="software"
        )
        
        info = wallet.get_wallet_info()
        print(f"✓ Software wallet initialized: {info['wallet_type']}")
        print(f"  Public key: {info['public_key'][:20]}...")
        
        wallet.disconnect()
        
    except Exception as e:
        print(f"✗ Software wallet test failed: {e}")

def test_hardware_wallet_simulation():
    """Test hardware wallet initialization (simulation mode)."""
    print("\nTesting hardware wallet simulation...")
    
    try:
        # This will fail to connect to actual hardware, but tests the code path
        wallet = SolanaWallet(
            wallet_type="ledger",
            derivation_path="44'/501'/0'/0'"
        )
        
        info = wallet.get_wallet_info()
        print(f"✓ Hardware wallet simulation: {info}")
        
    except RuntimeError as e:
        if "Failed to connect" in str(e):
            print("✓ Hardware wallet connection failed as expected (no device connected)")
        else:
            print(f"✗ Unexpected hardware wallet error: {e}")
    except Exception as e:
        print(f"✗ Hardware wallet test failed: {e}")

def main():
    """Run all tests."""
    print("Hardware Wallet Integration Test")
    print("=" * 40)
    
    # Store original env vars
    original_env = {}
    for key in ['WALLET_TYPE', 'PRIVATE_KEY', 'HARDWARE_DERIVATION_PATH']:
        original_env[key] = os.environ.get(key)
    
    try:
        test_config_validation()
        test_software_wallet()
        test_hardware_wallet_simulation()
        
        print("\n" + "=" * 40)
        print("Hardware wallet integration tests completed!")
        print("\nTo use hardware wallet:")
        print("1. Set WALLET_TYPE=ledger in .env")
        print("2. Set HARDWARE_DERIVATION_PATH=44'/501'/0'/0' in .env")
        print("3. Connect your Ledger device")
        print("4. Install Solana app on Ledger")
        print("5. Run the bot with hardware wallet support")
        
    finally:
        # Restore original env vars
        for key, value in original_env.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value

if __name__ == "__main__":
    main()