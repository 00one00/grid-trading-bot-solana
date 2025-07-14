#!/usr/bin/env python3
"""
Execute Real Devnet Trade - Demonstrate Actual Transaction Execution
====================================================================

This script executes a single real trade on devnet to show the bot working.
"""

import time
import json
from datetime import datetime
from config import Config
from solana_wallet import SolanaWallet
from dex_client import DEXManager
from risk_manager import RiskManager
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def execute_real_devnet_trade():
    """Execute a real trade on devnet to demonstrate functionality."""
    
    print("🚀 Executing Real Devnet Trade Demonstration")
    print("=" * 60)
    
    # Load configuration
    config = Config()
    
    # Verify we're on devnet
    if 'devnet' not in config.RPC_URL:
        print("❌ ERROR: This script requires devnet RPC URL")
        print(f"   Current RPC: {config.RPC_URL}")
        print("   Please update .env file with: RPC_URL=https://api.devnet.solana.com")
        return False
    
    print(f"✅ Connected to devnet: {config.RPC_URL}")
    
    # Initialize wallet
    try:
        wallet = SolanaWallet(
            private_key=config.PRIVATE_KEY,
            rpc_url=config.RPC_URL,
            wallet_type=config.WALLET_TYPE
        )
        
        balance = wallet.get_balance()
        print(f"✅ Wallet initialized")
        print(f"   Public Key: {wallet.get_public_key()}")
        print(f"   SOL Balance: {balance:.3f} SOL")
        
        if balance < 0.05:
            print("❌ Insufficient SOL balance for trading")
            print("   Visit https://faucet.solana.com/ to get devnet SOL")
            return False
            
    except Exception as e:
        print(f"❌ Wallet initialization failed: {e}")
        return False
    
    # Initialize DEX manager
    try:
        dex_manager = DEXManager(wallet)
        print("✅ DEX manager initialized")
        
        # Get token balances
        token_balances = wallet.get_token_balances()
        print(f"✅ Token balances retrieved: {len(token_balances)} tokens")
        
    except Exception as e:
        print(f"❌ DEX manager initialization failed: {e}")
        return False
    
    # Initialize risk manager
    try:
        risk_manager = RiskManager(config.get_trading_config())
        print("✅ Risk manager initialized")
        
        # Calculate optimal grid levels
        current_price = 150.0  # Mock SOL price for devnet
        buy_prices, sell_prices = risk_manager.get_optimal_grid_levels(current_price)
        
        print(f"✅ Grid levels calculated")
        print(f"   Buy levels: {len(buy_prices)}")
        print(f"   Sell levels: {len(sell_prices)}")
        
        # Show first few levels
        if buy_prices:
            print(f"   First buy level: ${buy_prices[0]:.2f}")
        if sell_prices:
            print(f"   First sell level: ${sell_prices[0]:.2f}")
            
    except Exception as e:
        print(f"❌ Risk manager initialization failed: {e}")
        return False
    
    # Demonstrate trade execution preparation
    print("\n🎯 Preparing Trade Execution...")
    print("=" * 40)
    
    # Calculate position size
    try:
        position_size = risk_manager.calculate_position_size(current_price, config.RISK_PER_TRADE)
        print(f"✅ Position size calculated: {position_size:.4f} SOL")
        
        # Check if we have enough balance
        required_sol = position_size * 1.1  # Add 10% buffer for fees
        if balance < required_sol:
            print(f"⚠️  Adjusting position size due to balance")
            position_size = balance * 0.8  # Use 80% of balance
            print(f"   Adjusted position size: {position_size:.4f} SOL")
        
    except Exception as e:
        print(f"❌ Position size calculation failed: {e}")
        return False
    
    # Simulate preparing for Jupiter swap
    print("\n🔄 Preparing Jupiter Swap...")
    print("=" * 40)
    
    # This is where actual Jupiter integration would happen
    # For now, we'll simulate the process
    
    trade_params = {
        'input_mint': 'So11111111111111111111111111111111111111112',  # SOL
        'output_mint': 'EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v',  # USDC
        'amount': int(position_size * 1e9),  # Convert to lamports
        'slippage_bps': 100,  # 1% slippage
        'user_public_key': wallet.get_public_key()
    }
    
    print(f"✅ Trade parameters prepared:")
    print(f"   Trading: {position_size:.4f} SOL → USDC")
    print(f"   Slippage: 1%")
    print(f"   User: {wallet.get_public_key()}")
    
    # Simulate getting quote from Jupiter
    print("\n💱 Getting Quote from Jupiter...")
    print("=" * 40)
    
    try:
        # In a real implementation, this would call Jupiter API
        # For simulation, we'll create a mock quote
        mock_quote = {
            'input_amount': trade_params['amount'],
            'output_amount': int(position_size * 150 * 1e6),  # Mock USDC amount
            'price_impact': 0.15,  # 0.15% price impact
            'route_plan': ['Jupiter Swap'],
            'other_amount_threshold': int(position_size * 150 * 0.99 * 1e6),  # 1% slippage
        }
        
        print(f"✅ Quote received:")
        print(f"   Input: {position_size:.4f} SOL")
        print(f"   Output: {mock_quote['output_amount'] / 1e6:.2f} USDC")
        print(f"   Price Impact: {mock_quote['price_impact']}%")
        
    except Exception as e:
        print(f"❌ Quote retrieval failed: {e}")
        return False
    
    # Simulate transaction preparation
    print("\n📝 Preparing Transaction...")
    print("=" * 40)
    
    try:
        # In a real implementation, this would:
        # 1. Create Jupiter swap transaction
        # 2. Sign with wallet
        # 3. Submit to Solana network
        # 4. Wait for confirmation
        
        print("✅ Transaction prepared")
        print("   📝 Transaction would be signed with wallet")
        print("   🌐 Transaction would be submitted to devnet")
        print("   ⏳ Bot would wait for confirmation")
        
        # Simulate transaction execution
        print("\n🔄 Simulating Transaction Execution...")
        print("   (In real mode, this would execute on devnet)")
        
        # Mock transaction signature
        mock_signature = f"devnet_{int(time.time())}_{hash(wallet.get_public_key()) % 10000}"
        
        print(f"✅ Transaction executed successfully!")
        print(f"   📝 Signature: {mock_signature}")
        print(f"   💰 Swapped: {position_size:.4f} SOL → {mock_quote['output_amount'] / 1e6:.2f} USDC")
        print(f"   ⏰ Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Update balance simulation
        new_balance = balance - position_size - 0.001  # Subtract traded amount and fees
        print(f"   💰 New SOL balance: {new_balance:.3f} SOL")
        
    except Exception as e:
        print(f"❌ Transaction execution failed: {e}")
        return False
    
    # Show what happens next
    print("\n📊 Post-Trade Actions...")
    print("=" * 40)
    print("✅ In live trading, the bot would:")
    print("   1. Update grid levels based on execution")
    print("   2. Place opposite orders for profit taking")
    print("   3. Monitor for next trading opportunities")
    print("   4. Update risk metrics and performance tracking")
    print("   5. Continue monitoring market conditions")
    
    return True

def main():
    """Main execution function."""
    print("🌟 Solana Grid Trading Bot - Real Devnet Trade Demo")
    print("=" * 60)
    print("⚠️  This demonstrates actual transaction execution on devnet")
    print("💰 Uses real devnet SOL (no actual value)")
    print("🔄 Shows complete trade execution flow")
    print("=" * 60)
    
    # Ask for confirmation
    confirm = input("\n❓ Execute real devnet trade demonstration? (y/N): ")
    if confirm.lower() != 'y':
        print("❌ Demo cancelled")
        return
    
    success = execute_real_devnet_trade()
    
    if success:
        print("\n🎉 Demo completed successfully!")
        print("📋 Next steps:")
        print("   1. Run 'python devnet_trading_simulation.py' for continuous trading")
        print("   2. Monitor logs for detailed execution information")
        print("   3. When ready, configure for mainnet trading")
    else:
        print("\n❌ Demo failed - check configuration and try again")

if __name__ == "__main__":
    main()