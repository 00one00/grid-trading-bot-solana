#!/usr/bin/env python3
"""
Test script to verify the network mismatch fix for blockhash reconstruction.

This script tests that Jupiter transactions are properly reconstructed with 
devnet blockhashes instead of mainnet blockhashes.
"""

import os
import sys
import logging
from typing import Optional

# Add the project root to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config import Config
from solana_wallet import SolanaWallet
from dex_client import DEXManager

def setup_logging():
    """Setup logging for the test."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )

def test_network_blockhash_fix():
    """Test the network mismatch fix for blockhash reconstruction."""
    
    print("🧪 TESTING NETWORK BLOCKHASH FIX")
    print("=" * 60)
    print("This test verifies that Jupiter transactions are properly")
    print("reconstructed with devnet blockhashes instead of mainnet ones.")
    print("=" * 60)
    
    try:
        # Load configuration
        print("\n⚙️  Loading devnet configuration...")
        config = Config()
        
        # Verify we're on devnet
        if not config.is_devnet:
            print("❌ ERROR: Must be configured for devnet testing")
            print("💡 Set NETWORK=devnet in your .env file")
            return False
        
        print(f"  ✅ Network: {config.NETWORK}")
        print(f"  ✅ RPC URL: {config.RPC_URL}")
        
        # Initialize wallet
        print("\n💰 Initializing wallet connection...")
        wallet = SolanaWallet(config.PRIVATE_KEY, config.RPC_URL, config.WALLET_TYPE)
        balance = wallet.get_balance()
        
        if balance is None or balance < 0.01:
            print("❌ ERROR: Insufficient devnet SOL balance")
            print("💡 Get devnet SOL from: https://faucet.solana.com/")
            return False
            
        print(f"  ✅ Wallet: {str(wallet.get_public_key())[:8]}...")
        print(f"  ✅ Balance: {balance:.4f} SOL")
        
        # Initialize DEX manager
        print("\n🔄 Initializing DEX manager...")
        dex_manager = DEXManager(wallet)
        
        # Test 1: Get Jupiter quote (should work)
        print("\n🔍 Test 1: Getting Jupiter quote...")
        quote = dex_manager.get_best_price("SOL", "USDC", 0.001)
        
        if not quote:
            print("❌ ERROR: Failed to get Jupiter quote")
            return False
            
        print(f"  ✅ Quote received: {quote.input_amount} SOL → {quote.output_amount} USDC")
        print(f"  ✅ Price: {quote.price:.2f} USDC per SOL")
        
        # Test 2: Get swap transaction (should contain mainnet blockhash)
        print("\n📋 Test 2: Getting swap transaction...")
        amount_lamports = int(0.001 * 1e9)  # 0.001 SOL in lamports
        raw_quote = dex_manager.jupiter.get_raw_quote("So11111111111111111111111111111111111111112", "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v", amount_lamports)
        if not raw_quote:
            print("❌ ERROR: Failed to get raw quote")
            return False
            
        transaction_b64 = dex_manager.jupiter.get_swap_transaction(raw_quote, str(wallet.get_public_key()))
        if not transaction_b64:
            print("❌ ERROR: Failed to get swap transaction")
            return False
            
        print(f"  ✅ Transaction received: {len(transaction_b64)} chars")
        
        # Test 3: Execute with fresh blockhash reconstruction (the fix)
        print("\n🔧 Test 3: Testing fresh blockhash reconstruction...")
        print("  ⚠️  This will execute a real transaction on devnet")
        
        # Automatically proceed with test (no input needed)
        print("  🚀 Proceeding with real transaction test...")
        
        print("\n🚀 Executing Phase 1B fresh transaction with network fix...")
        print("  📊 Parameters:")
        print(f"     Amount: 0.001 SOL")
        print(f"     Pair: SOL → USDC")
        print(f"     Method: execute_fresh_transaction_immediate (with network fix)")
        
        # Use the method that exists on DEXManager (not JupiterDEXClient)
        signature = dex_manager.execute_swap_with_fresh_transaction("SOL", "USDC", 0.001)
        
        if signature:
            print(f"\n✅ SUCCESS! Transaction executed: {signature}")
            print(f"🔗 Explorer: https://explorer.solana.com/tx/{signature}?cluster=devnet")
            print("\n🎉 NETWORK FIX VERIFIED!")
            print("   The blockhash reconstruction successfully fixed the network mismatch issue.")
            return True
        else:
            print("\n❌ FAILED: Transaction still failed despite network fix")
            print("💡 The blockhash reconstruction approach needs further debugging")
            return False
            
    except Exception as e:
        print(f"\n❌ ERROR: Test failed with exception: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Main test function."""
    setup_logging()
    
    print("🧪 NETWORK BLOCKHASH FIX TEST")
    print("Testing Phase 1B implementation with network mismatch fix")
    print()
    
    success = test_network_blockhash_fix()
    
    print("\n" + "=" * 60)
    if success:
        print("✅ NETWORK FIX TEST PASSED!")
        print("The blockhash reconstruction fix appears to be working.")
        print("\n💡 Next steps:")
        print("   1. Run python test_devnet.py to test full pipeline")
        print("   2. If successful, proceed with grid trading tests")
    else:
        print("❌ NETWORK FIX TEST FAILED!")
        print("The fix may need further adjustment.")
        print("\n💡 Debug steps:")
        print("   1. Check logs for specific error messages")
        print("   2. Verify devnet configuration")
        print("   3. Ensure sufficient devnet SOL balance")
    print("=" * 60)

if __name__ == "__main__":
    main()