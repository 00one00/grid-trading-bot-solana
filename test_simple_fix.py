#!/usr/bin/env python3
"""
Simple test to verify basic transaction execution works with normal signing.
"""

import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config import Config
from solana_wallet import SolanaWallet
from dex_client import DEXManager

def test_simple_transaction():
    """Test simple transaction execution."""
    
    print("🧪 SIMPLE TRANSACTION TEST")
    print("=" * 50)
    
    # Load config
    config = Config()
    print(f"Network: {config.NETWORK}")
    
    # Initialize wallet
    wallet = SolanaWallet(config.PRIVATE_KEY, config.RPC_URL, config.WALLET_TYPE)
    print(f"Wallet: {str(wallet.get_public_key())[:8]}...")
    print(f"Balance: {wallet.get_balance():.4f} SOL")
    
    # Initialize DEX manager
    dex_manager = DEXManager(wallet)
    
    # Get quote
    quote = dex_manager.get_best_price("SOL", "USDC", 0.001)
    if not quote:
        print("❌ Quote failed")
        return False
    print(f"Quote: {quote.input_amount} SOL → {quote.output_amount} USDC")
    
    # Get raw transaction and try simple execution
    amount_lamports = int(0.001 * 1e9)
    raw_quote = dex_manager.jupiter.get_raw_quote("So11111111111111111111111111111111111111112", "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v", amount_lamports)
    if not raw_quote:
        print("❌ Raw quote failed")
        return False
    
    transaction_b64 = dex_manager.jupiter.get_swap_transaction(raw_quote, str(wallet.get_public_key()))
    if not transaction_b64:
        print("❌ Transaction creation failed")
        return False
    print(f"Transaction length: {len(transaction_b64)} chars")
    
    # Parse and inspect the transaction
    import base64
    from solders.transaction import VersionedTransaction
    
    transaction_bytes = base64.b64decode(transaction_b64)
    transaction = VersionedTransaction.from_bytes(transaction_bytes)
    
    print(f"Transaction blockhash: {str(transaction.message.recent_blockhash)[:8]}...")
    
    # Check if this blockhash exists on our network
    try:
        # Try to validate the blockhash
        latest_blockhash = wallet.rpc_client.get_latest_blockhash()
        current_blockhash = latest_blockhash.value.blockhash
        
        print(f"Current network blockhash: {str(current_blockhash)[:8]}...")
        
        if transaction.message.recent_blockhash == current_blockhash:
            print("✅ Transaction blockhash matches current network blockhash!")
        else:
            print("❌ Transaction blockhash does NOT match network - this will fail")
            print("🔍 This confirms the network mismatch issue")
            
        # Try to execute anyway to see the error
        print("\n🚀 Attempting execution...")
        signed_tx = wallet.sign_transaction(transaction)
        signature = wallet.send_transaction(signed_tx)
        
        if signature:
            print(f"✅ SUCCESS: {signature}")
            return True
        else:
            print("❌ Failed to execute")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    test_simple_transaction()