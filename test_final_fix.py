#!/usr/bin/env python3
"""
Final fix: Request multiple Jupiter transactions until we get one with a valid devnet blockhash.
"""

import os
import sys
import base64
import time
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config import Config
from solana_wallet import SolanaWallet
from dex_client import DEXManager
from solders.transaction import VersionedTransaction, Transaction

def test_final_fix():
    """Test the final fix - retry until valid blockhash."""
    
    print("🧪 FINAL BLOCKHASH FIX TEST")
    print("=" * 50)
    
    # Load config
    config = Config()
    wallet = SolanaWallet(config.PRIVATE_KEY, config.RPC_URL, config.WALLET_TYPE)
    dex_manager = DEXManager(wallet)
    
    print(f"Network: {config.NETWORK}")
    print(f"Balance: {wallet.get_balance():.4f} SOL")
    
    # Get quote once
    amount_lamports = int(0.001 * 1e9)
    raw_quote = dex_manager.jupiter.get_raw_quote("So11111111111111111111111111111111111111112", "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v", amount_lamports)
    if not raw_quote:
        print("❌ Quote failed")
        return False
    
    print("✅ Quote obtained")
    
    # Try up to 5 times to get a transaction with a valid blockhash
    max_attempts = 5
    for attempt in range(max_attempts):
        print(f"\n🔄 Attempt {attempt + 1}/{max_attempts}: Requesting transaction...")
        
        # Get transaction from Jupiter
        transaction_b64 = dex_manager.jupiter.get_swap_transaction(raw_quote, str(wallet.get_public_key()))
        if not transaction_b64:
            print(f"❌ Attempt {attempt + 1}: Transaction creation failed")
            continue
        
        # Parse transaction
        transaction_bytes = base64.b64decode(transaction_b64)
        try:
            # Try legacy transaction first
            transaction = Transaction.from_bytes(transaction_bytes)
            tx_type = "Legacy"
        except:
            # Fall back to versioned
            transaction = VersionedTransaction.from_bytes(transaction_bytes)
            tx_type = "Versioned"
        
        # Get current network blockhash
        latest_blockhash = wallet.rpc_client.get_latest_blockhash()
        current_blockhash = latest_blockhash.value.blockhash
        
        tx_blockhash = transaction.message.recent_blockhash
        
        print(f"  📊 Type: {tx_type}")
        print(f"  📊 Length: {len(transaction_b64)} chars")
        print(f"  📊 TX blockhash: {str(tx_blockhash)[:8]}...")
        print(f"  📊 Network blockhash: {str(current_blockhash)[:8]}...")
        
        # Always try with fresh blockhash signing (don't wait for match)
        print(f"  🔧 Attempt {attempt + 1}: Testing fresh blockhash signing...")
        
        # Execute the transaction with fresh blockhash signing
        try:
            signed_tx = wallet.sign_transaction_with_fresh_blockhash(transaction)
            signature = wallet.send_transaction(signed_tx)
            
            if signature:
                print(f"\n🎉 SUCCESS! Transaction executed: {signature}")
                print(f"🔗 Explorer: https://explorer.solana.com/tx/{signature}?cluster=devnet")
                return True
            else:
                print(f"  ❌ Attempt {attempt + 1}: Execution failed (no signature)")
        except Exception as e:
            print(f"  ❌ Attempt {attempt + 1}: Execution error: {e}")
        
        # Wait a bit before retry to let blockhash change
        if attempt < max_attempts - 1:
            print("  ⏱️  Waiting 2 seconds for blockhash to advance...")
            time.sleep(2)
    
    print(f"\n❌ All {max_attempts} attempts failed")
    return False

if __name__ == "__main__":
    test_final_fix()