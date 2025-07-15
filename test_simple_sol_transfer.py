#!/usr/bin/env python3
"""
Simple SOL transfer to test if our fresh blockhash signing works.
"""

import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config import Config
from solana_wallet import SolanaWallet
from solders.transaction import Transaction
from solders.instruction import Instruction, AccountMeta
from solders.pubkey import Pubkey
from solders.system_program import ID as SYSTEM_PROGRAM_ID
import struct

def test_simple_sol_transfer():
    """Test simple SOL transfer with fresh blockhash."""
    
    print("💰 SIMPLE SOL TRANSFER TEST")
    print("=" * 50)
    print("Testing basic SOL transfer with fresh blockhash signing")
    
    # Load config
    config = Config()
    wallet = SolanaWallet(config.PRIVATE_KEY, config.RPC_URL, config.WALLET_TYPE)
    
    print(f"Network: {config.NETWORK}")
    print(f"From: {str(wallet.get_public_key())[:8]}...")
    print(f"Balance: {wallet.get_balance():.4f} SOL")
    
    try:
        # Create a simple SOL transfer instruction
        # Transfer 0.001 SOL to ourselves (safe test)
        from_pubkey = Pubkey.from_string(str(wallet.get_public_key()))
        to_pubkey = Pubkey.from_string(str(wallet.get_public_key()))  # Send to ourselves for testing
        lamports = int(0.001 * 1e9)  # 0.001 SOL
        
        # Create transfer instruction
        transfer_instruction = Instruction(
            program_id=SYSTEM_PROGRAM_ID,
            accounts=[
                AccountMeta(from_pubkey, is_signer=True, is_writable=True),
                AccountMeta(to_pubkey, is_signer=False, is_writable=True),
            ],
            data=struct.pack('<LQ', 2, lamports)  # Transfer instruction (type 2)
        )
        
        print(f"📤 Transfer: 0.001 SOL from self to self")
        
        # Create transaction with invalid blockhash first
        from solders.hash import Hash
        invalid_blockhash = Hash.default()  # Invalid blockhash
        
        transaction = Transaction.new_with_payer(
            instructions=[transfer_instruction],
            payer=from_pubkey
        )
        
        print(f"🔧 Created transaction with invalid blockhash")
        print(f"   Original blockhash: {str(transaction.message.recent_blockhash)[:8]}...")
        
        # Test 1: Try with original invalid blockhash (should fail)
        print("\n📋 Test 1: Execute with invalid blockhash (expected to fail)")
        try:
            signed_tx_bad = wallet.sign_transaction(transaction)
            signature_bad = wallet.send_transaction(signed_tx_bad)
            if signature_bad:
                print(f"❌ UNEXPECTED: Invalid blockhash worked: {signature_bad}")
            else:
                print("✅ EXPECTED: Invalid blockhash failed as expected")
        except Exception as e:
            print(f"✅ EXPECTED: Invalid blockhash failed: {type(e).__name__}")
        
        # Test 2: Use fresh blockhash signing (should work)
        print("\n📋 Test 2: Execute with fresh blockhash signing (should work)")
        try:
            signed_tx_good = wallet.sign_transaction_with_fresh_blockhash(transaction)
            
            # Check that the blockhash was updated
            new_blockhash = signed_tx_good.message.recent_blockhash
            print(f"   Fresh blockhash: {str(new_blockhash)[:8]}...")
            
            if new_blockhash != transaction.message.recent_blockhash:
                print("✅ Blockhash was updated by fresh signing")
            else:
                print("⚠️  Blockhash was NOT updated")
            
            signature_good = wallet.send_transaction(signed_tx_good)
            if signature_good:
                print(f"\n🎉 SUCCESS! Fresh blockhash signing works!")
                print(f"💫 Signature: {signature_good}")
                print(f"🔗 Explorer: https://explorer.solana.com/tx/{signature_good}?cluster=devnet")
                print("\n✅ THE BLOCKHASH FIX IS WORKING!")
                print("✅ The issue was using mainnet token addresses on devnet")
                return True
            else:
                print("❌ Fresh blockhash signing failed to execute")
                return False
                
        except Exception as e:
            print(f"❌ Fresh blockhash signing error: {e}")
            return False
            
    except Exception as e:
        print(f"❌ Test setup error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    test_simple_sol_transfer()