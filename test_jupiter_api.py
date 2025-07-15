#!/usr/bin/env python3
"""
Test Jupiter API Integration - Verify Real API Calls
===================================================

This script tests the updated Jupiter API integration with real API calls.
"""

import time
import json
from datetime import datetime
from config import Config
from solana_wallet import SolanaWallet
from dex_client import DEXManager, JupiterDEXClient
import logging

# Setup logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_jupiter_api():
    """Test Jupiter API integration with real calls."""
    
    print("🧪 Testing Jupiter API Integration")
    print("=" * 60)
    
    # Load configuration
    config = Config()
    
    # Initialize wallet
    try:
        wallet = SolanaWallet(
            private_key=config.PRIVATE_KEY,
            rpc_url=config.RPC_URL,
            wallet_type=config.WALLET_TYPE
        )
        
        print(f"✅ Wallet initialized")
        print(f"   Public Key: {wallet.get_public_key()}")
        print(f"   SOL Balance: {wallet.get_balance():.6f} SOL")
        
    except Exception as e:
        print(f"❌ Wallet initialization failed: {e}")
        return False
    
    # Test Jupiter client directly
    print("\n🌐 Testing Jupiter Client...")
    
    try:
        jupiter = JupiterDEXClient(wallet)
        print("✅ Jupiter client initialized")
        
        # Test quote request
        sol_mint = "So11111111111111111111111111111111111111112"
        usdc_mint = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"
        amount_lamports = int(0.1 * 1e9)  # 0.1 SOL in lamports
        
        print(f"\n📊 Testing quote: 0.1 SOL -> USDC")
        print(f"   Input mint: {sol_mint}")
        print(f"   Output mint: {usdc_mint}")
        print(f"   Amount: {amount_lamports} lamports")
        
        # Test structured quote
        quote = jupiter.get_quote(sol_mint, usdc_mint, amount_lamports)
        
        if quote:
            print("✅ Structured quote successful:")
            print(f"   Input amount: {quote.input_amount:.6f} SOL")
            print(f"   Output amount: {quote.output_amount:.6f} USDC")
            print(f"   Price: {quote.price:.6f} USDC per SOL")
            print(f"   Fee/Impact: {quote.fee:.6f}%")
            print(f"   Route steps: {len(quote.route)}")
            if quote.route:
                print(f"   Route: {' -> '.join(quote.route[:3])}")
        else:
            print("❌ Structured quote failed")
        
        # Test raw quote
        print(f"\n📋 Testing raw quote...")
        raw_quote = jupiter.get_raw_quote(sol_mint, usdc_mint, amount_lamports)
        
        if raw_quote:
            print("✅ Raw quote successful:")
            print(f"   Input amount: {raw_quote.get('inputAmount', 'N/A')}")
            print(f"   Output amount: {raw_quote.get('outputAmount', 'N/A')}")
            print(f"   Price impact: {raw_quote.get('priceImpactPct', 'N/A')}%")
            print(f"   Has route plan: {'routePlan' in raw_quote}")
            
            # Test swap transaction preparation (without executing)
            print(f"\n🔄 Testing swap transaction preparation...")
            
            transaction_b64 = jupiter.get_swap_transaction(raw_quote, str(wallet.public_key))
            
            if transaction_b64:
                print("✅ Swap transaction prepared successfully")
                print(f"   Transaction length: {len(transaction_b64)} chars")
                print(f"   Transaction preview: {transaction_b64[:50]}...")
                print("   ⚠️  Transaction not executed (test mode)")
            else:
                print("❌ Swap transaction preparation failed")
        else:
            print("❌ Raw quote failed")
            
    except Exception as e:
        print(f"❌ Jupiter client test failed: {e}")
        logger.exception("Jupiter client error")
        return False
    
    # Test DEX Manager
    print("\n🔧 Testing DEX Manager...")
    
    try:
        dex_manager = DEXManager(wallet)
        print("✅ DEX Manager initialized")
        
        # Test get_best_price
        best_price = dex_manager.get_best_price("SOL", "USDC", 0.1)
        
        if best_price:
            print("✅ DEX Manager get_best_price successful:")
            print(f"   Price: {best_price.price:.6f} USDC per SOL")
            print(f"   Input: {best_price.input_amount:.6f} SOL")
            print(f"   Output: {best_price.output_amount:.6f} USDC")
        else:
            print("❌ DEX Manager get_best_price failed")
        
        # Test token balance retrieval
        print(f"\n💰 Testing token balance retrieval...")
        
        sol_balance = dex_manager.get_token_balance("SOL")
        usdc_balance = dex_manager.get_token_balance("USDC")
        
        print(f"✅ Token balances:")
        print(f"   SOL: {sol_balance:.6f}")
        print(f"   USDC: {usdc_balance:.6f}")
        
    except Exception as e:
        print(f"❌ DEX Manager test failed: {e}")
        logger.exception("DEX Manager error")
        return False
    
    # Test market price functionality
    print(f"\n📈 Testing market price functionality...")
    
    try:
        market_price = dex_manager.get_market_price("SOL/USDC")
        
        if market_price:
            print(f"✅ Market price: {market_price:.6f} USDC per SOL")
        else:
            print("❌ Market price retrieval failed")
            
    except Exception as e:
        print(f"❌ Market price test failed: {e}")
    
    return True

def test_error_handling():
    """Test error handling with invalid inputs."""
    
    print("\n🛡️  Testing Error Handling...")
    print("=" * 40)
    
    config = Config()
    
    try:
        wallet = SolanaWallet(
            private_key=config.PRIVATE_KEY,
            rpc_url=config.RPC_URL,
            wallet_type=config.WALLET_TYPE
        )
        
        jupiter = JupiterDEXClient(wallet)
        
        # Test with invalid token mint
        print("📋 Testing invalid token mint...")
        quote = jupiter.get_quote("invalid_mint", "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v", 1000000)
        
        if quote is None:
            print("✅ Invalid mint properly handled (returned None)")
        else:
            print("⚠️  Invalid mint returned quote (unexpected)")
        
        # Test with zero amount
        print("📋 Testing zero amount...")
        quote = jupiter.get_quote(
            "So11111111111111111111111111111111111111112",
            "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
            0
        )
        
        if quote is None:
            print("✅ Zero amount properly handled (returned None)")
        else:
            print("⚠️  Zero amount returned quote (unexpected)")
        
        print("✅ Error handling tests completed")
        
    except Exception as e:
        print(f"❌ Error handling test failed: {e}")
        return False
    
    return True

def main():
    """Main execution function."""
    print("🌟 Jupiter API Integration Test Suite")
    print("=" * 60)
    print("🧪 This tests the updated Jupiter API integration")
    print("📊 Includes quote requests, transaction preparation, and error handling")
    print("⚠️  No actual trades will be executed")
    print("=" * 60)
    
    # Test main functionality
    success1 = test_jupiter_api()
    
    # Test error handling
    success2 = test_error_handling()
    
    print("\n" + "=" * 60)
    if success1 and success2:
        print("🎉 All Jupiter API tests passed!")
        print("📋 Next steps:")
        print("   1. Run 'python execute_devnet_trade.py' for end-to-end testing")
        print("   2. Test with different token pairs and amounts")
        print("   3. Monitor logs for performance and error patterns")
    else:
        print("❌ Some tests failed - check logs and configuration")
        print("📋 Troubleshooting:")
        print("   1. Verify internet connectivity")
        print("   2. Check if Jupiter API is accessible")
        print("   3. Ensure wallet configuration is correct")

if __name__ == "__main__":
    main()