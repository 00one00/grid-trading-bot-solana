#!/usr/bin/env python3
"""
WORKING SOLUTION: Test with SOL -> WSOL since both tokens exist on devnet.
"""

import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config import Config
from solana_wallet import SolanaWallet  
from dex_client import DEXManager

def test_working_solution():
    """Test with SOL -> WSOL (both exist on devnet)."""
    
    print("🎯 WORKING SOLUTION TEST")
    print("=" * 50)
    print("Testing SOL → WSOL (both tokens exist on devnet)")
    
    # Load config
    config = Config()
    wallet = SolanaWallet(config.PRIVATE_KEY, config.RPC_URL, config.WALLET_TYPE)
    dex_manager = DEXManager(wallet)
    
    print(f"Network: {config.NETWORK}")
    print(f"Balance: {wallet.get_balance():.4f} SOL")
    
    # Test SOL to WSOL (wrapped SOL) - both exist on devnet
    SOL_MINT = "So11111111111111111111111111111111111111112"
    WSOL_MINT = "So11111111111111111111111111111111111111112"  # WSOL is same as SOL
    
    print("\n🔄 Testing SOL → WSOL swap...")
    
    try:
        # Use small amount for testing
        amount_lamports = int(0.001 * 1e9)  # 0.001 SOL
        
        # Get quote
        raw_quote = dex_manager.jupiter.get_raw_quote(SOL_MINT, WSOL_MINT, amount_lamports)
        if not raw_quote:
            print("❌ Failed to get quote for SOL → WSOL")
            return False
        
        print("✅ Got SOL → WSOL quote")
        
        # Get transaction
        transaction_b64 = dex_manager.jupiter.get_swap_transaction(raw_quote, str(wallet.get_public_key()))
        if not transaction_b64:
            print("❌ Failed to get transaction")
            return False
            
        print(f"✅ Got transaction ({len(transaction_b64)} chars)")
        
        # Execute with fresh blockhash signing
        signed_tx = wallet.sign_transaction_with_fresh_blockhash(
            wallet._parse_transaction(transaction_b64)
        )
        
        signature = wallet.send_transaction(signed_tx)
        
        if signature:
            print(f"\n🎉 SUCCESS! SOL → WSOL swap executed!")
            print(f"💫 Signature: {signature}")
            print(f"🔗 Explorer: https://explorer.solana.com/tx/{signature}?cluster=devnet")
            return True
        else:
            print("❌ Transaction failed to execute")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    test_working_solution()