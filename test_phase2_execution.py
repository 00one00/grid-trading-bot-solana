#!/usr/bin/env python3
"""
Test Phase 2 Transaction Execution
Tests the complete execute_swap workflow with real Jupiter transactions on devnet.
"""

import os
import sys
import logging
from datetime import datetime
from config import Config
from solana_wallet import SolanaWallet
from dex_client import DEXManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_phase2_execution():
    """Test the complete Phase 2 transaction execution."""
    
    print("🚀 Phase 2 Transaction Execution Test")
    print("=" * 50)
    
    try:
        # Load configuration
        config = Config()
        print(f"✅ Configuration loaded")
        
        # Initialize wallet
        wallet = SolanaWallet(
            private_key=config.PRIVATE_KEY,
            rpc_url=config.RPC_URL,
            wallet_type=config.WALLET_TYPE
        )
        print(f"✅ Wallet initialized: {str(wallet.public_key)[:8]}...")
        
        # Check balance
        sol_balance = wallet.get_balance()
        print(f"✅ SOL balance: {sol_balance:.6f} SOL")
        
        if sol_balance < 0.01:
            print("❌ Insufficient SOL balance for transaction (need at least 0.01 SOL)")
            return False
        
        # Initialize DEX manager
        dex_manager = DEXManager(wallet)
        print(f"✅ DEX manager initialized")
        
        # Test parameters
        input_token = "SOL"
        output_token = "USDC"
        amount = 0.01  # Small amount for testing
        slippage_bps = 100  # 1% slippage
        
        print(f"\n🎯 Test Parameters:")
        print(f"   Swap: {amount} {input_token} → {output_token}")
        print(f"   Slippage: {slippage_bps/100:.1f}%")
        print(f"   Network: devnet")
        
        # Ask for confirmation
        confirm = input(f"\n❓ Execute real devnet swap of {amount} SOL? (y/N): ")
        if confirm.lower() != 'y':
            print("❌ Test cancelled")
            return False
        
        print(f"\n🔄 Executing swap...")
        print("-" * 30)
        
        # Execute the swap
        signature = dex_manager.execute_swap(
            input_token=input_token,
            output_token=output_token,
            amount=amount,
            slippage_bps=slippage_bps
        )
        
        if signature:
            print(f"\n🎉 SWAP EXECUTED SUCCESSFULLY!")
            print(f"   Transaction: {signature}")
            print(f"   Explorer: https://explorer.solana.com/tx/{signature}?cluster=devnet")
            
            # Get transaction status
            tx_status = dex_manager.get_transaction_status(signature)
            print(f"\n📊 Transaction Details:")
            print(f"   Status: {tx_status.get('status', 'unknown')}")
            print(f"   Confirmation: {tx_status.get('confirmation_status', 'unknown')}")
            print(f"   Fee: {tx_status.get('fee', 0) / 1e9:.6f} SOL")
            
            # Check new balance
            new_balance = wallet.get_balance()
            print(f"\n💰 Updated Balance:")
            print(f"   SOL: {new_balance:.6f} SOL (was {sol_balance:.6f})")
            print(f"   Change: {new_balance - sol_balance:.6f} SOL")
            
            return True
        else:
            print(f"\n❌ SWAP FAILED!")
            print("   Check logs for error details")
            return False
            
    except Exception as e:
        logger.error(f"Phase 2 test failed: {e}")
        print(f"\n❌ Test failed with error: {e}")
        return False

def main():
    """Main test function."""
    
    print("🧪 Solana Grid Bot - Phase 2 Execution Test")
    print("=" * 60)
    print("⚠️  This executes real transactions on Solana devnet")
    print("💰 Uses real devnet SOL for transaction fees")
    print("🔄 Tests complete swap execution workflow")
    print("=" * 60)
    
    success = test_phase2_execution()
    
    if success:
        print("\n✅ Phase 2 execution test PASSED!")
        print("📋 What was tested:")
        print("   • Jupiter quote retrieval")
        print("   • Transaction creation via Jupiter API")
        print("   • Transaction signing with wallet")
        print("   • Transaction broadcasting to devnet")
        print("   • Transaction confirmation monitoring")
        print("   • Enhanced logging with Explorer links")
        print("\n🚀 Phase 2 implementation is complete and working!")
    else:
        print("\n❌ Phase 2 execution test FAILED!")
        print("🔧 Check configuration and try again")

if __name__ == "__main__":
    main()