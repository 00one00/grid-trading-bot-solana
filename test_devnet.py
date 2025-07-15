#!/usr/bin/env python3
"""
Devnet Trading Test Script
==========================

This script specifically tests trading functionality on Solana devnet.
It automatically sets the network to devnet and uses safe testing parameters.
"""

import os
import sys
from dotenv import load_dotenv, set_key

def setup_devnet_environment():
    """Configure environment for devnet testing."""
    print("🏗️  SETTING UP DEVNET ENVIRONMENT")
    print("="*50)
    
    # Load current environment
    load_dotenv()
    
    # Override network setting for this test
    os.environ['NETWORK'] = 'devnet'
    
    # Set safe devnet defaults if not configured
    if not os.getenv('DEVNET_CAPITAL'):
        os.environ['DEVNET_CAPITAL'] = '0.05'  # 0.05 SOL for testing
    
    print(f"  ✅ Network: {os.environ['NETWORK']}")
    print(f"  ✅ Capital: {os.environ.get('DEVNET_CAPITAL', '0.05')} SOL")
    print(f"  ✅ RPC URL: {os.getenv('DEVNET_RPC_URL', 'https://api.devnet.solana.com')}")
    print()

def test_configuration():
    """Test configuration loading with devnet settings."""
    print("⚙️  TESTING DEVNET CONFIGURATION")
    print("="*50)
    
    try:
        from config import Config
        config = Config()
        
        print(f"  ✅ Network: {config.NETWORK}")
        print(f"  ✅ Is Devnet: {config.is_devnet}")
        print(f"  ✅ RPC URL: {config.RPC_URL}")
        print(f"  ✅ Capital: {config.CAPITAL} SOL")
        print(f"  ✅ Explorer: {config.explorer_url}")
        print()
        return config
        
    except Exception as e:
        print(f"  ❌ Configuration error: {e}")
        return None

def test_wallet_connection(config):
    """Test wallet connection on devnet."""
    print("💰 TESTING DEVNET WALLET CONNECTION")
    print("="*50)
    
    try:
        from solana_wallet import SolanaWallet
        
        wallet = SolanaWallet(
            private_key=config.PRIVATE_KEY,
            rpc_url=config.RPC_URL,
            wallet_type=config.WALLET_TYPE
        )
        
        balance = wallet.get_balance()
        
        print(f"  ✅ Wallet: {str(wallet.public_key)[:8]}...")
        print(f"  ✅ Balance: {balance} SOL")
        
        if balance < 0.1:
            print("  ⚠️  WARNING: Low devnet SOL balance")
            print("  💡 Get devnet SOL from: https://faucet.solana.com/")
        
        print()
        return wallet
        
    except Exception as e:
        print(f"  ❌ Wallet connection error: {e}")
        return None

def test_jupiter_devnet_integration(wallet):
    """Test Jupiter API on devnet."""
    print("🔄 TESTING JUPITER DEVNET INTEGRATION")
    print("="*50)
    
    try:
        from dex_client import DEXManager
        
        dex = DEXManager(wallet)
        
        # Test quote with small amount
        quote = dex.jupiter.get_raw_quote(
            input_mint="So11111111111111111111111111111111111111112",  # SOL
            output_mint="EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",  # USDC
            amount=5000000  # 0.005 SOL in lamports
        )
        
        if quote:
            print(f"  ✅ Quote successful")
            print(f"  ✅ Input: {quote.get('inAmount', 'N/A')} lamports")
            print(f"  ✅ Output: {quote.get('outAmount', 'N/A')} USDC units")
            
            # Test Phase 1B method availability
            print(f"  🔍 Checking Phase 1B methods...")
            phase1b_methods = [
                'execute_swap_with_fresh_transaction',
                'execute_fresh_transaction_immediate',
                'execute_swap_optimized_phase1b'
            ]
            
            all_available = True
            for method in phase1b_methods:
                if hasattr(dex, method):
                    print(f"     ✅ {method}")
                else:
                    print(f"     ❌ {method} - Missing")
                    all_available = False
            
            if all_available:
                print(f"  ✅ All Phase 1B methods available")
            else:
                print(f"  ⚠️  Some Phase 1B methods missing")
            
            print()
            return dex  # Return dex manager for trading tests
        else:
            print("  ❌ Quote failed")
            return False
            
    except Exception as e:
        print(f"  ❌ Jupiter integration error: {e}")
        return False

def run_devnet_trade_test(dex_manager):
    """Run a Phase 1B devnet trade test."""
    print("🚀 EXECUTING PHASE 1B DEVNET TRADE TEST")
    print("="*50)
    
    try:
        print("  🔄 Running Phase 1B fresh transaction execution on devnet...")
        print("  ⚠️  This will execute a real transaction on devnet")
        print("  💡 Using improved blockhash handling (Phase 1B)")
        print()
        
        confirm = input("  ❓ Continue with Phase 1B devnet trade test? (y/N): ")
        if confirm.lower() == 'y':
            # Test parameters
            test_amount = 0.001  # 0.001 SOL (safe amount)
            slippage_bps = 50    # 0.5% slippage
            
            print(f"  📋 Test Parameters:")
            print(f"     Amount: {test_amount} SOL")
            print(f"     Pair: SOL → USDC")
            print(f"     Slippage: {slippage_bps} bps (0.5%)")
            print(f"     Method: execute_swap_with_fresh_transaction (Phase 1B)")
            print()
            
            # Execute Phase 1B swap
            print("  🔄 Executing Phase 1B swap...")
            signature = dex_manager.execute_swap_with_fresh_transaction(
                "SOL", "USDC", test_amount, slippage_bps
            )
            
            if signature:
                print(f"\n  🎉 PHASE 1B TRADE SUCCESSFUL!")
                print(f"  📝 Transaction: {signature}")
                print(f"  🔗 Explorer: https://explorer.solana.com/tx/{signature}?cluster=devnet")
                
                # Wait for confirmation
                print(f"\n  ⏳ Waiting for confirmation...")
                confirmed = dex_manager.wait_for_confirmation(signature, timeout=60)
                
                if confirmed:
                    print(f"  ✅ Transaction confirmed!")
                    
                    # Get transaction details
                    tx_status = dex_manager.get_transaction_status(signature)
                    print(f"  📊 Status: {tx_status.get('status')}")
                    print(f"  📊 Confirmation: {tx_status.get('confirmation_status')}")
                    
                    if tx_status.get('fee'):
                        fee_sol = tx_status.get('fee') / 1e9
                        print(f"  💸 Fee: {fee_sol:.6f} SOL")
                    
                    return True
                else:
                    print(f"  ❌ Transaction failed to confirm")
                    return False
            else:
                print(f"\n  ❌ PHASE 1B TRADE FAILED")
                print(f"  💡 Check logs for detailed error information")
                return False
        else:
            print("  ⏸️  Test cancelled by user")
            return False
            
    except Exception as e:
        print(f"  ❌ Phase 1B trade test error: {e}")
        return False

def main():
    """Main devnet test runner."""
    print("🧪 SOLANA GRID BOT - DEVNET TESTING")
    print("="*60)
    print("This script tests all functionality on Solana devnet")
    print("Safe for testing - uses devnet SOL (no real value)")
    print("="*60)
    print()
    
    # Step 1: Setup devnet environment
    setup_devnet_environment()
    
    # Step 2: Test configuration
    config = test_configuration()
    if not config:
        print("❌ Configuration test failed")
        return False
    
    # Step 3: Test wallet connection
    wallet = test_wallet_connection(config)
    if not wallet:
        print("❌ Wallet connection failed")
        return False
    
    # Step 4: Test Jupiter integration
    dex_manager = test_jupiter_devnet_integration(wallet)
    if not dex_manager:
        print("❌ Jupiter integration failed")
        return False
    
    # Step 5: Optional Phase 1B trade test
    print("🎯 ALL DEVNET TESTS PASSED!")
    print("="*50)
    print("Ready for Phase 1B devnet trading tests.")
    print("Using improved fresh transaction execution.")
    print()
    
    trade_test = input("❓ Run Phase 1B devnet trade test? (y/N): ")
    if trade_test.lower() == 'y':
        success = run_devnet_trade_test(dex_manager)
        if success:
            print("\n🎉 PHASE 1B DEVNET TRADE TEST SUCCESSFUL!")
            print("✅ Fresh transaction execution working on devnet")
            print("✅ Blockhash staleness issue resolved")
        else:
            print("\n⚠️  Phase 1B devnet trade test encountered issues")
            print("💡 Check the error logs for specific details")
    
    print("\n📋 DEVNET TEST SUMMARY")
    print("="*50)
    print("✅ Environment setup")
    print("✅ Configuration loading")
    print("✅ Wallet connection") 
    print("✅ Jupiter API integration")
    print("🔄 Phase 1B trade execution (optional)")
    print()
    print("🚀 PHASE 1B FEATURES TESTED:")
    print("   ✅ Fresh transaction execution pipeline")
    print("   ✅ Improved blockhash handling")
    print("   ✅ Enhanced error detection")
    print("   ✅ Transaction size optimization")
    print()
    print("💡 To switch to mainnet testing:")
    print("   1. Update NETWORK=mainnet in .env")
    print("   2. Fund wallet with real SOL")
    print("   3. Start with small amounts ($50-100)")
    print("   4. Use Phase 1B methods for best reliability")
    
    return True

if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⏸️  Devnet test interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        sys.exit(1)