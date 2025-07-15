#!/usr/bin/env python3
"""
Signature Verification Diagnostic Script
=======================================

This script systematically tests each component of the transaction pipeline
to identify the root cause of the signature verification failure.
"""

import os
import sys
import json
import base64
import logging
from typing import Dict, Any, Optional
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_environment_setup():
    """Test environment configuration."""
    print("🔧 TESTING ENVIRONMENT SETUP")
    print("="*50)
    
    # Load environment
    load_dotenv()
    
    required_vars = [
        'PRIVATE_KEY',
        'WALLET_TYPE'
    ]
    
    missing_vars = []
    for var in required_vars:
        value = os.getenv(var)
        if not value:
            missing_vars.append(var)
        else:
            # Mask sensitive data
            display_value = value[:8] + "..." if var == 'PRIVATE_KEY' else value
            print(f"  ✅ {var}: {display_value}")
    
    # Check network configuration
    network = os.getenv('NETWORK', 'devnet')
    print(f"  ✅ NETWORK: {network}")
    
    # RPC URL is determined by config, not environment directly
    try:
        from config import Config
        config = Config()
        print(f"  ✅ RPC_URL: {config.RPC_URL}")
    except Exception as e:
        print(f"  ⚠️  RPC_URL: Error loading config - {e}")
    
    if missing_vars:
        print(f"  ❌ Missing variables: {missing_vars}")
        return False
    
    print("  ✅ Environment configuration complete")
    return True

def test_wallet_initialization():
    """Test wallet initialization and basic functions."""
    print("\n💰 TESTING WALLET INITIALIZATION")
    print("="*50)
    
    try:
        from solana_wallet import SolanaWallet
        from config import Config
        
        # Load config
        config = Config()
        
        # Initialize wallet
        wallet = SolanaWallet(
            private_key=config.PRIVATE_KEY,
            rpc_url=config.RPC_URL,
            wallet_type=config.WALLET_TYPE
        )
        
        print(f"  ✅ Wallet initialized: {str(wallet.public_key)[:8]}...")
        print(f"  ✅ Wallet type: {wallet.wallet_type}")
        print(f"  ✅ RPC URL: {wallet.rpc_client._provider.endpoint_uri}")
        
        # Test balance
        balance = wallet.get_balance()
        print(f"  ✅ SOL balance: {balance} SOL")
        
        if balance < 0.01:
            print("  ⚠️  WARNING: Low SOL balance for testing")
        
        return wallet
        
    except Exception as e:
        print(f"  ❌ Wallet initialization failed: {e}")
        return None

def test_jupiter_quote(wallet):
    """Test Jupiter API quote functionality."""
    print("\n📊 TESTING JUPITER QUOTE")
    print("="*50)
    
    try:
        from dex_client import DEXManager
        
        # Initialize DEX manager
        dex = DEXManager(wallet)
        
        # Test quote
        quote = dex.jupiter.get_raw_quote(
            input_mint="So11111111111111111111111111111111111111112",  # SOL
            output_mint="EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",  # USDC
            amount=10000000  # 0.01 SOL in lamports
        )
        
        if quote:
            print(f"  ✅ Quote successful")
            print(f"  ✅ Input amount: {quote.get('inAmount', 'N/A')}")
            print(f"  ✅ Output amount: {quote.get('outAmount', 'N/A')}")
            print(f"  ✅ Route plan: {'Yes' if quote.get('routePlan') else 'No'}")
            return quote
        else:
            print("  ❌ Quote failed")
            return None
            
    except Exception as e:
        print(f"  ❌ Jupiter quote error: {e}")
        return None

def test_transaction_creation(wallet, quote):
    """Test transaction creation from Jupiter."""
    print("\n🔨 TESTING TRANSACTION CREATION")
    print("="*50)
    
    try:
        from dex_client import DEXManager
        import requests
        
        # Initialize DEX manager
        dex = DEXManager(wallet)
        
        # Prepare swap request
        swap_payload = {
            "userPublicKey": str(wallet.public_key),
            "quoteResponse": quote,
            "asLegacyTransaction": True,  # Force legacy transaction
            "prioritizationFeeLamports": "auto"
        }
        
        print(f"  📝 User public key: {str(wallet.public_key)[:8]}...")
        print(f"  📝 Legacy transaction: {swap_payload['asLegacyTransaction']}")
        print(f"  📝 Priority fee: {swap_payload['prioritizationFeeLamports']}")
        
        # Make request to Jupiter swap API
        response = requests.post(
            "https://quote-api.jup.ag/v6/swap",
            json=swap_payload,
            headers={"Content-Type": "application/json"},
            timeout=30
        )
        
        if response.status_code == 200:
            swap_data = response.json()
            transaction_b64 = swap_data.get('swapTransaction')
            
            print(f"  ✅ Transaction created successfully")
            print(f"  ✅ Transaction length: {len(transaction_b64)} characters")
            print(f"  ✅ Transaction preview: {transaction_b64[:50]}...")
            
            return transaction_b64
        else:
            print(f"  ❌ Transaction creation failed: {response.status_code}")
            print(f"  ❌ Response: {response.text}")
            return None
            
    except Exception as e:
        print(f"  ❌ Transaction creation error: {e}")
        return None

def test_transaction_parsing(transaction_b64):
    """Test transaction parsing and structure."""
    print("\n🔍 TESTING TRANSACTION PARSING")
    print("="*50)
    
    try:
        from solders.transaction import Transaction, VersionedTransaction
        
        # Decode base64
        transaction_bytes = base64.b64decode(transaction_b64)
        print(f"  ✅ Base64 decoded: {len(transaction_bytes)} bytes")
        
        # Try parsing as different transaction types
        try:
            # Try as Transaction first
            transaction = Transaction.from_bytes(transaction_bytes)
            print(f"  ✅ Parsed as Transaction")
            print(f"  ✅ Recent blockhash: {transaction.message.recent_blockhash}")
            print(f"  ✅ Instructions: {len(transaction.message.instructions)}")
            print(f"  ✅ Signatures: {len(transaction.signatures)}")
            
            return transaction, "Transaction"
            
        except Exception as e1:
            print(f"  ⚠️  Transaction parsing failed: {e1}")
            
            try:
                # Try as VersionedTransaction
                versioned_tx = VersionedTransaction.from_bytes(transaction_bytes)
                print(f"  ✅ Parsed as VersionedTransaction")
                print(f"  ✅ Message type: {type(versioned_tx.message)}")
                print(f"  ✅ Signatures: {len(versioned_tx.signatures)}")
                
                return versioned_tx, "VersionedTransaction"
                
            except Exception as e2:
                print(f"  ❌ VersionedTransaction parsing failed: {e2}")
                return None, None
            
    except Exception as e:
        print(f"  ❌ Transaction parsing error: {e}")
        return None, None

def test_transaction_signing(wallet, transaction, tx_type):
    """Test transaction signing."""
    print("\n✍️  TESTING TRANSACTION SIGNING")
    print("="*50)
    
    try:
        print(f"  📝 Transaction type: {tx_type}")
        print(f"  📝 Wallet type: {wallet.wallet_type}")
        
        # Test signing
        if tx_type == "Transaction":
            print("  🔧 Signing as Transaction...")
            # Get recent blockhash for legacy transactions
            recent_blockhash_response = wallet.rpc_client.get_latest_blockhash()
            transaction.sign([wallet.keypair], recent_blockhash_response.value.blockhash)
            print("  ✅ Transaction signed successfully")
            
        elif tx_type == "VersionedTransaction":
            print("  🔧 Signing as VersionedTransaction...")
            transaction.sign([wallet.keypair])
            print("  ✅ VersionedTransaction signed successfully")
        
        # Verify signature
        if len(transaction.signatures) > 0:
            print(f"  ✅ Signatures present: {len(transaction.signatures)}")
            signature_preview = str(transaction.signatures[0])[:16] + "..."
            print(f"  ✅ First signature: {signature_preview}")
        else:
            print("  ❌ No signatures found")
            return None
        
        return transaction
        
    except Exception as e:
        print(f"  ❌ Transaction signing error: {e}")
        return None

def test_rpc_connection(wallet):
    """Test RPC connection and basic operations."""
    print("\n🌐 TESTING RPC CONNECTION")
    print("="*50)
    
    try:
        # Test basic connection
        response = wallet.rpc_client.get_slot()
        print(f"  ✅ RPC connection successful")
        print(f"  ✅ Current slot: {response.value}")
        
        # Test account info
        account_info = wallet.rpc_client.get_account_info(wallet.public_key)
        if account_info.value:
            print(f"  ✅ Account exists: {account_info.value.lamports} lamports")
        else:
            print("  ⚠️  Account not found or empty")
        
        # Test recent blockhash
        blockhash_response = wallet.rpc_client.get_latest_blockhash()
        print(f"  ✅ Recent blockhash: {str(blockhash_response.value.blockhash)[:16]}...")
        
        return True
        
    except Exception as e:
        print(f"  ❌ RPC connection error: {e}")
        return False

def test_transaction_simulation(wallet, signed_transaction):
    """Test transaction simulation before sending."""
    print("\n🎮 TESTING TRANSACTION SIMULATION")
    print("="*50)
    
    try:
        from solana.rpc.commitment import Commitment
        
        # Simulate transaction
        response = wallet.rpc_client.simulate_transaction(
            signed_transaction,
            commitment=Commitment("confirmed")
        )
        
        if response.value:
            result = response.value
            print(f"  ✅ Simulation successful")
            
            if result.err:
                print(f"  ❌ Simulation error: {result.err}")
                return False
            else:
                print(f"  ✅ No simulation errors")
                print(f"  ✅ Units consumed: {result.units_consumed}")
                
                if result.logs:
                    print(f"  ✅ Log entries: {len(result.logs)}")
                    for i, log in enumerate(result.logs[:3]):  # Show first 3 logs
                        print(f"    Log {i+1}: {log}")
                
                return True
        else:
            print("  ❌ Simulation failed: no response")
            return False
            
    except Exception as e:
        print(f"  ❌ Transaction simulation error: {e}")
        return False

def main():
    """Run comprehensive diagnostic tests."""
    print("🚀 SIGNATURE VERIFICATION DIAGNOSTIC")
    print("="*60)
    print("This script will systematically test each component")
    print("of the transaction pipeline to identify issues.")
    print("="*60)
    
    # Test 1: Environment setup
    if not test_environment_setup():
        print("\n❌ Environment setup failed. Check your .env file.")
        return False
    
    # Test 2: Wallet initialization
    wallet = test_wallet_initialization()
    if not wallet:
        print("\n❌ Wallet initialization failed.")
        return False
    
    # Test 3: RPC connection
    if not test_rpc_connection(wallet):
        print("\n❌ RPC connection failed.")
        return False
    
    # Test 4: Jupiter quote
    quote = test_jupiter_quote(wallet)
    if not quote:
        print("\n❌ Jupiter quote failed.")
        return False
    
    # Test 5: Transaction creation
    transaction_b64 = test_transaction_creation(wallet, quote)
    if not transaction_b64:
        print("\n❌ Transaction creation failed.")
        return False
    
    # Test 6: Transaction parsing
    transaction, tx_type = test_transaction_parsing(transaction_b64)
    if not transaction:
        print("\n❌ Transaction parsing failed.")
        return False
    
    # Test 7: Transaction signing
    signed_transaction = test_transaction_signing(wallet, transaction, tx_type)
    if not signed_transaction:
        print("\n❌ Transaction signing failed.")
        return False
    
    # Test 8: Transaction simulation
    if not test_transaction_simulation(wallet, signed_transaction):
        print("\n⚠️  Transaction simulation failed (this may indicate the issue)")
    
    print("\n" + "="*60)
    print("🎉 DIAGNOSTIC COMPLETE")
    print("="*60)
    print("All tests passed up to the signing stage.")
    print("If simulation failed, check the simulation logs above.")
    print("The issue may be with:")
    print("  1. Transaction format (legacy vs versioned)")
    print("  2. Address lookup tables on devnet")
    print("  3. Insufficient SOL for fees")
    print("  4. Devnet-specific Jupiter limitations")
    
    return True

if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⏸️  Diagnostic interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        sys.exit(1)