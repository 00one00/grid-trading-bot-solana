#!/usr/bin/env python3
"""
Mainnet Trading Test Script
===========================

This script tests trading functionality on Solana mainnet with enhanced safety checks.
It includes multiple confirmation prompts and safety validations before executing real trades.
"""

import os
import sys
from dotenv import load_dotenv

def setup_mainnet_environment():
    """Configure environment for mainnet testing with safety checks."""
    print("🚨 SETTING UP MAINNET ENVIRONMENT")
    print("="*60)
    print("⚠️  WARNING: This will execute REAL trades with REAL money!")
    print("⚠️  Always start with small amounts ($50-$100) for testing")
    print("="*60)
    
    # Load current environment
    load_dotenv()
    
    # Override network setting for this test
    os.environ['NETWORK'] = 'mainnet'
    
    print(f"  ✅ Network: {os.environ['NETWORK']}")
    print(f"  ✅ Capital: {os.environ.get('MAINNET_CAPITAL', '250.0')} USD equiv")
    print(f"  ✅ RPC URL: {os.getenv('MAINNET_RPC_URL', 'https://api.mainnet-beta.solana.com')}")
    print()

def safety_checklist():
    """Run through mainnet safety checklist."""
    print("🛡️  MAINNET SAFETY CHECKLIST")
    print("="*50)
    
    checklist = [
        "✅ Devnet testing completed successfully",
        "✅ Private key is secure and backed up",
        "✅ Starting with small test amount ($50-$100)",
        "✅ Hardware wallet recommended for large amounts",
        "✅ Emergency stop procedure understood",
        "✅ Risk management limits configured"
    ]
    
    for item in checklist:
        print(f"  {item}")
    
    print()
    confirm = input("❓ Have you completed all safety checks? (y/N): ")
    if confirm.lower() != 'y':
        print("  ⚠️  Please complete safety checklist before proceeding")
        return False
    
    print()
    return True

def test_mainnet_configuration():
    """Test configuration loading with mainnet settings."""
    print("⚙️  TESTING MAINNET CONFIGURATION")
    print("="*50)
    
    try:
        from config import Config
        config = Config()
        
        print(f"  ✅ Network: {config.NETWORK}")
        print(f"  ✅ Is Mainnet: {config.is_mainnet}")
        print(f"  ✅ RPC URL: {config.RPC_URL}")
        print(f"  ✅ Capital: ${config.CAPITAL}")
        print(f"  ✅ Explorer: {config.explorer_url}")
        
        # Validate critical settings
        if config.CAPITAL > 500:
            print(f"  ⚠️  WARNING: High capital amount (${config.CAPITAL})")
            print("  💡 Consider starting with smaller amount for initial testing")
        
        print()
        return config
        
    except Exception as e:
        print(f"  ❌ Configuration error: {e}")
        return None

def test_mainnet_wallet_connection(config):
    """Test wallet connection on mainnet with balance validation."""
    print("💰 TESTING MAINNET WALLET CONNECTION")
    print("="*50)
    
    try:
        from solana_wallet import SolanaWallet
        
        wallet = SolanaWallet(
            private_key=config.PRIVATE_KEY,
            rpc_url=config.RPC_URL,
            wallet_type=config.WALLET_TYPE
        )
        
        balance = wallet.get_balance()
        balance_usd = balance * 160  # Approximate SOL price for estimation
        
        print(f"  ✅ Wallet: {str(wallet.public_key)[:8]}...")
        print(f"  ✅ Balance: {balance} SOL (~${balance_usd:.2f})")
        
        # Balance safety checks
        if balance < 0.1:
            print("  ❌ ERROR: Insufficient SOL balance for mainnet trading")
            print("  💡 Need at least 0.1 SOL for gas fees and minimum trades")
            return None
        elif balance < 0.5:
            print("  ⚠️  WARNING: Low SOL balance, may limit trading opportunities")
        
        # Capital vs balance validation
        required_sol = config.CAPITAL / 160  # Rough estimate
        if balance < required_sol * 1.2:  # 20% buffer for fees
            print(f"  ⚠️  WARNING: SOL balance may be insufficient for configured capital")
            print(f"  💡 Consider reducing CAPITAL or adding more SOL")
        
        print()
        return wallet
        
    except Exception as e:
        print(f"  ❌ Wallet connection error: {e}")
        return None

def test_jupiter_mainnet_integration(wallet):
    """Test Jupiter API on mainnet with real price validation."""
    print("🔄 TESTING JUPITER MAINNET INTEGRATION")
    print("="*50)
    
    try:
        from dex_client import DEXManager
        
        dex = DEXManager(wallet)
        
        # Test quote with very small amount first
        quote = dex.jupiter.get_raw_quote(
            input_mint="So11111111111111111111111111111111111111112",  # SOL
            output_mint="EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",  # USDC
            amount=1000000  # 0.001 SOL in lamports
        )
        
        if quote:
            in_amount = int(quote.get('inAmount', 0))
            out_amount = int(quote.get('outAmount', 0))
            
            # Calculate price (rough estimate)
            if in_amount > 0 and out_amount > 0:
                price = (out_amount / 1e6) / (in_amount / 1e9)  # USDC per SOL
                print(f"  ✅ Quote successful")
                print(f"  ✅ Price: ~${price:.2f} per SOL")
                print(f"  ✅ Input: {in_amount} lamports (0.001 SOL)")
                print(f"  ✅ Output: {out_amount} USDC units")
                
                # Sanity check on price
                if price < 50 or price > 1000:
                    print(f"  ⚠️  WARNING: Price seems unusual: ${price:.2f}")
                    print("  💡 Double-check market conditions")
            
            print()
            return True
        else:
            print("  ❌ Quote failed")
            return False
            
    except Exception as e:
        print(f"  ❌ Jupiter integration error: {e}")
        return False

def mainnet_trade_confirmation():
    """Multi-step confirmation for mainnet trading."""
    print("🚨 MAINNET TRADE CONFIRMATION")
    print("="*60)
    print("⚠️  You are about to execute REAL trades on Solana mainnet")
    print("⚠️  This involves REAL money and REAL risk")
    print("="*60)
    
    confirmations = [
        "I understand this executes real trades with real money",
        "I have tested thoroughly on devnet first", 
        "I am starting with a small amount I can afford to lose",
        "I understand the risks of automated trading"
    ]
    
    for i, conf in enumerate(confirmations, 1):
        print(f"\n{i}. {conf}")
        confirm = input(f"   Confirm (y/N): ")
        if confirm.lower() != 'y':
            print("  ⏸️  Mainnet trading cancelled")
            return False
    
    print("\n🔴 FINAL CONFIRMATION")
    final = input("Type 'EXECUTE MAINNET' to proceed: ")
    if final != 'EXECUTE MAINNET':
        print("  ⏸️  Mainnet trading cancelled")
        return False
    
    return True

def run_mainnet_trade_test():
    """Run a single mainnet trade test with full safety protocols."""
    print("🚀 EXECUTING MAINNET TRADE TEST")
    print("="*50)
    
    if not mainnet_trade_confirmation():
        return False
    
    try:
        # Import and run the Phase 2 test with mainnet settings
        from test_phase2_execution import main as run_phase2_test
        
        print("  🔄 Running Phase 2 execution test on MAINNET...")
        print("  🚨 REAL TRANSACTION INCOMING!")
        print()
        
        # Final countdown
        for i in range(5, 0, -1):
            print(f"  ⏰ Starting in {i} seconds... (Ctrl+C to cancel)")
            import time
            time.sleep(1)
        
        print("  🚀 EXECUTING...")
        result = run_phase2_test()
        return result
        
    except KeyboardInterrupt:
        print("\n  ⏸️  Trade cancelled by user")
        return False
    except Exception as e:
        print(f"  ❌ Trade test error: {e}")
        return False

def main():
    """Main mainnet test runner with comprehensive safety checks."""
    print("🚨 SOLANA GRID BOT - MAINNET TESTING")
    print("="*70)
    print("⚠️  WARNING: This script executes REAL trades with REAL money!")
    print("⚠️  Only proceed if you understand the risks and have tested on devnet")
    print("="*70)
    print()
    
    # Initial safety confirmation
    proceed = input("❓ Do you want to proceed with mainnet testing? (y/N): ")
    if proceed.lower() != 'y':
        print("⏸️  Mainnet testing cancelled")
        return False
    
    # Step 1: Safety checklist
    if not safety_checklist():
        return False
    
    # Step 2: Setup mainnet environment
    setup_mainnet_environment()
    
    # Step 3: Test configuration
    config = test_mainnet_configuration()
    if not config:
        print("❌ Configuration test failed")
        return False
    
    # Step 4: Test wallet connection
    wallet = test_mainnet_wallet_connection(config)
    if not wallet:
        print("❌ Wallet connection failed")
        return False
    
    # Step 5: Test Jupiter integration
    if not test_jupiter_mainnet_integration(wallet):
        print("❌ Jupiter integration failed")
        return False
    
    # Step 6: Optional trade test with full safety protocols
    print("🎯 ALL MAINNET TESTS PASSED!")
    print("="*50)
    print("System ready for mainnet trading.")
    print()
    
    trade_test = input("❓ Proceed to mainnet trade test? (y/N): ")
    if trade_test.lower() == 'y':
        success = run_mainnet_trade_test()
        if success:
            print("\n🎉 MAINNET TRADE TEST SUCCESSFUL!")
            print("🚀 System is ready for live trading")
        else:
            print("\n⚠️  Mainnet trade test encountered issues")
            print("🔧 Review logs and configuration before proceeding")
    
    print("\n📋 MAINNET TEST SUMMARY")
    print("="*50)
    print("✅ Safety checklist completed")
    print("✅ Environment setup")
    print("✅ Configuration validation")
    print("✅ Wallet connection") 
    print("✅ Jupiter API integration")
    print("🔄 Trade execution (optional)")
    print()
    print("⚠️  IMPORTANT REMINDERS:")
    print("  • Monitor your bot continuously")
    print("  • Start with small amounts")
    print("  • Set appropriate stop losses")
    print("  • Have an emergency stop plan")
    
    return True

if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⏸️  Mainnet test interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        sys.exit(1)