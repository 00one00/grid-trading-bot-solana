#!/usr/bin/env python3
"""
Phase 1B Implementation Test Suite

Tests the improved transaction execution system with:
- Fresh blockhash handling
- Immediate transaction execution
- Comprehensive error detection
- Real devnet transaction validation
"""

import sys
import time
import logging
from typing import Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_phase1b_infrastructure():
    """Test Phase 1B infrastructure and method availability."""
    print("\n" + "="*60)
    print("🧪 PHASE 1B INFRASTRUCTURE TESTS")
    print("="*60)
    
    try:
        from config import Config
        from solana_wallet import SolanaWallet
        from dex_client import DEXManager
        
        config = Config()
        wallet = SolanaWallet(config.PRIVATE_KEY, config.RPC_URL, config.WALLET_TYPE)
        dex_manager = DEXManager(wallet)
        
        # Test 1: Method availability
        print("1. Testing method availability...")
        methods_to_test = [
            'execute_swap_with_fresh_transaction',
            'execute_fresh_transaction_immediate',
            'sign_and_send_transaction_fast',
            'detect_blockhash_errors',
            'log_transaction_pipeline'
        ]
        
        for method_name in methods_to_test:
            if hasattr(dex_manager, method_name):
                print(f"   ✅ {method_name} - Available")
            else:
                print(f"   ❌ {method_name} - Missing")
                return False
        
        # Test 2: Wallet method availability
        print("2. Testing wallet method availability...")
        wallet_methods = [
            'sign_transaction',
            'sign_transaction_with_fresh_blockhash',
            'send_transaction'
        ]
        
        for method_name in wallet_methods:
            if hasattr(wallet, method_name):
                print(f"   ✅ {method_name} - Available")
            else:
                print(f"   ❌ {method_name} - Missing")
                return False
        
        # Test 3: Error detection functionality
        print("3. Testing error detection...")
        test_errors = [
            "Blockhash not found",
            "Transaction has expired",
            "recent_blockhash not found",
            "Normal error message"
        ]
        
        for error_msg in test_errors:
            is_blockhash_error = dex_manager.detect_blockhash_errors(error_msg)
            expected = "blockhash" in error_msg.lower() or "expired" in error_msg.lower()
            
            if is_blockhash_error == expected:
                print(f"   ✅ Error detection: '{error_msg[:30]}...' -> {is_blockhash_error}")
            else:
                print(f"   ❌ Error detection failed: '{error_msg[:30]}...' -> {is_blockhash_error} (expected {expected})")
                return False
        
        # Test 4: Pipeline logging
        print("4. Testing pipeline logging...")
        try:
            dex_manager.log_transaction_pipeline("TEST", "SUCCESS", {"test_param": "value"})
            print("   ✅ Pipeline logging functional")
        except Exception as e:
            print(f"   ❌ Pipeline logging failed: {e}")
            return False
        
        # Test 5: Network connectivity
        print("5. Testing network connectivity...")
        try:
            balance = wallet.get_balance()
            print(f"   ✅ Wallet balance: {balance:.6f} SOL")
            
            if balance < 0.1:
                print(f"   ⚠️  Warning: Low balance ({balance:.6f} SOL) - may affect transaction tests")
        except Exception as e:
            print(f"   ❌ Network connectivity failed: {e}")
            return False
        
        print("\n✅ All infrastructure tests passed!")
        return True
        
    except Exception as e:
        print(f"\n❌ Infrastructure test failed: {e}")
        return False

def test_phase1b_transaction_pipeline():
    """Test the complete Phase 1B transaction pipeline without real execution."""
    print("\n" + "="*60)
    print("🧪 PHASE 1B TRANSACTION PIPELINE TESTS")
    print("="*60)
    
    try:
        from config import Config
        from solana_wallet import SolanaWallet
        from dex_client import DEXManager
        
        config = Config()
        wallet = SolanaWallet(config.PRIVATE_KEY, config.RPC_URL, config.WALLET_TYPE)
        dex_manager = DEXManager(wallet)
        
        # Test 1: Quote retrieval
        print("1. Testing quote retrieval...")
        try:
            quote = dex_manager.jupiter.get_raw_quote(
                "So11111111111111111111111111111111111111112",  # SOL
                "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",  # USDC
                100_000_000,  # 0.1 SOL
                50  # 0.5% slippage
            )
            
            if quote:
                print(f"   ✅ Quote received: {quote.get('inAmount')} -> {quote.get('outAmount')}")
            else:
                print("   ❌ Quote retrieval failed")
                return False
        except Exception as e:
            print(f"   ❌ Quote retrieval error: {e}")
            return False
        
        # Test 2: Transaction creation
        print("2. Testing transaction creation...")
        try:
            user_public_key = str(wallet.public_key)
            transaction_b64 = dex_manager.jupiter.get_swap_transaction(quote, user_public_key)
            
            if transaction_b64:
                print(f"   ✅ Transaction created (length: {len(transaction_b64)} chars)")
            else:
                print("   ❌ Transaction creation failed")
                return False
        except Exception as e:
            print(f"   ❌ Transaction creation error: {e}")
            return False
        
        # Test 3: Transaction parsing
        print("3. Testing transaction parsing...")
        try:
            import base64
            from solders.transaction import VersionedTransaction, Transaction
            
            transaction_bytes = base64.b64decode(transaction_b64)
            
            # Try both transaction types
            try:
                versioned_tx = VersionedTransaction.from_bytes(transaction_bytes)
                print(f"   ✅ Parsed as VersionedTransaction")
                tx_type = "VersionedTransaction"
                parsed_tx = versioned_tx
            except Exception:
                try:
                    legacy_tx = Transaction.from_bytes(transaction_bytes)
                    print(f"   ✅ Parsed as legacy Transaction")
                    tx_type = "Transaction"
                    parsed_tx = legacy_tx
                except Exception as e:
                    print(f"   ❌ Transaction parsing failed: {e}")
                    return False
        except Exception as e:
            print(f"   ❌ Transaction parsing error: {e}")
            return False
        
        # Test 4: Fresh blockhash retrieval
        print("4. Testing fresh blockhash retrieval...")
        try:
            start_time = time.time()
            recent_blockhash_response = wallet.rpc_client.get_latest_blockhash()
            elapsed = time.time() - start_time
            
            if recent_blockhash_response.value:
                fresh_blockhash = recent_blockhash_response.value.blockhash
                print(f"   ✅ Fresh blockhash: {str(fresh_blockhash)[:8]}... (took {elapsed:.3f}s)")
            else:
                print("   ❌ Fresh blockhash retrieval failed")
                return False
        except Exception as e:
            print(f"   ❌ Fresh blockhash error: {e}")
            return False
        
        print("\n✅ All pipeline tests passed!")
        return True
        
    except Exception as e:
        print(f"\n❌ Pipeline test failed: {e}")
        return False

def test_phase1b_performance_metrics():
    """Test Phase 1B performance and timing."""
    print("\n" + "="*60)
    print("🧪 PHASE 1B PERFORMANCE TESTS")
    print("="*60)
    
    try:
        from config import Config
        from solana_wallet import SolanaWallet
        from dex_client import DEXManager
        
        config = Config()
        wallet = SolanaWallet(config.PRIVATE_KEY, config.RPC_URL, config.WALLET_TYPE)
        dex_manager = DEXManager(wallet)
        
        # Test timing of individual components
        print("1. Testing component timing...")
        
        # Quote timing
        start_time = time.time()
        quote = dex_manager.jupiter.get_raw_quote(
            "So11111111111111111111111111111111111111112",  # SOL
            "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",  # USDC
            100_000_000,  # 0.1 SOL
            50  # 0.5% slippage
        )
        quote_time = time.time() - start_time
        print(f"   📊 Quote time: {quote_time:.3f}s")
        
        if not quote:
            print("   ❌ Quote failed, cannot continue performance tests")
            return False
        
        # Transaction creation timing
        start_time = time.time()
        user_public_key = str(wallet.public_key)
        transaction_b64 = dex_manager.jupiter.get_swap_transaction(quote, user_public_key)
        tx_time = time.time() - start_time
        print(f"   📊 Transaction creation time: {tx_time:.3f}s")
        
        if not transaction_b64:
            print("   ❌ Transaction creation failed, cannot continue performance tests")
            return False
        
        # Parsing timing
        start_time = time.time()
        import base64
        transaction_bytes = base64.b64decode(transaction_b64)
        
        try:
            from solders.transaction import VersionedTransaction
            parsed_tx = VersionedTransaction.from_bytes(transaction_bytes)
        except:
            from solders.transaction import Transaction
            parsed_tx = Transaction.from_bytes(transaction_bytes)
        
        parse_time = time.time() - start_time
        print(f"   📊 Transaction parsing time: {parse_time:.3f}s")
        
        # Blockhash timing
        start_time = time.time()
        recent_blockhash_response = wallet.rpc_client.get_latest_blockhash()
        blockhash_time = time.time() - start_time
        print(f"   📊 Fresh blockhash time: {blockhash_time:.3f}s")
        
        # Total pipeline estimate
        total_estimate = quote_time + tx_time + parse_time + blockhash_time + 0.2  # +200ms for signing/sending
        print(f"   📊 Estimated total pipeline time: {total_estimate:.3f}s")
        
        # Performance assessment
        print("\n2. Performance assessment...")
        
        if total_estimate < 2.0:
            print(f"   ✅ Excellent performance: {total_estimate:.3f}s < 2.0s target")
        elif total_estimate < 3.0:
            print(f"   ⚠️  Acceptable performance: {total_estimate:.3f}s (target: <2.0s)")
        else:
            print(f"   ❌ Poor performance: {total_estimate:.3f}s > 3.0s")
            return False
        
        # Individual component assessment
        if quote_time > 1.0:
            print(f"   ⚠️  Quote time high: {quote_time:.3f}s")
        if tx_time > 1.0:
            print(f"   ⚠️  Transaction creation time high: {tx_time:.3f}s")
        if blockhash_time > 0.5:
            print(f"   ⚠️  Blockhash retrieval time high: {blockhash_time:.3f}s")
        
        print("\n✅ Performance tests completed!")
        return True
        
    except Exception as e:
        print(f"\n❌ Performance test failed: {e}")
        return False

def test_phase1b_real_transaction():
    """Test Phase 1B with a real devnet transaction."""
    print("\n" + "="*60)
    print("🧪 PHASE 1B REAL TRANSACTION TEST")
    print("="*60)
    
    try:
        from config import Config
        from solana_wallet import SolanaWallet
        from dex_client import DEXManager
        
        config = Config()
        wallet = SolanaWallet(config.PRIVATE_KEY, config.RPC_URL, config.WALLET_TYPE)
        dex_manager = DEXManager(wallet)
        
        # Pre-flight checks
        print("1. Pre-flight checks...")
        
        balance = wallet.get_balance()
        print(f"   📊 Current SOL balance: {balance:.6f}")
        
        if balance < 0.01:
            print(f"   ❌ Insufficient balance for test transaction: {balance:.6f} SOL")
            print("   💡 Need at least 0.01 SOL for testing")
            return False
        
        network = config.RPC_URL
        if "devnet" not in network.lower():
            print(f"   ⚠️  Warning: Not on devnet ({network})")
            print("   💡 Recommend using devnet for testing")
        
        # Test small transaction
        print("2. Executing Phase 1B test transaction...")
        test_amount = 0.001  # Very small amount for testing
        
        print(f"   📋 Test parameters:")
        print(f"      Amount: {test_amount} SOL")
        print(f"      Pair: SOL -> USDC")
        print(f"      Slippage: 50 bps (0.5%)")
        print(f"      Method: execute_swap_with_fresh_transaction")
        
        start_time = time.time()
        
        try:
            signature = dex_manager.execute_swap_with_fresh_transaction(
                "SOL", "USDC", test_amount, 50
            )
            
            execution_time = time.time() - start_time
            
            if signature:
                print(f"\n   🎉 TRANSACTION SUCCESS!")
                print(f"   📝 Signature: {signature}")
                print(f"   ⏱️  Execution time: {execution_time:.3f}s")
                print(f"   🔗 Explorer: https://explorer.solana.com/tx/{signature}?cluster=devnet")
                
                # Wait for confirmation
                print(f"\n   ⏳ Waiting for confirmation...")
                confirmed = dex_manager.wait_for_confirmation(signature, timeout=60)
                
                if confirmed:
                    print(f"   ✅ Transaction confirmed!")
                    
                    # Get final status
                    tx_status = dex_manager.get_transaction_status(signature)
                    print(f"   📊 Final status: {tx_status.get('status')}")
                    print(f"   📊 Confirmation: {tx_status.get('confirmation_status')}")
                    
                    if tx_status.get('fee'):
                        fee_sol = tx_status.get('fee') / 1e9
                        print(f"   💸 Transaction fee: {fee_sol:.6f} SOL")
                    
                    return True
                else:
                    print(f"   ❌ Transaction failed to confirm within timeout")
                    return False
            else:
                print(f"\n   ❌ TRANSACTION FAILED!")
                print(f"   ⏱️  Execution time: {execution_time:.3f}s")
                return False
                
        except Exception as e:
            execution_time = time.time() - start_time
            print(f"\n   ❌ TRANSACTION ERROR!")
            print(f"   🐛 Error: {e}")
            print(f"   ⏱️  Execution time: {execution_time:.3f}s")
            
            # Detailed error analysis
            error_msg = str(e)
            if dex_manager.detect_blockhash_errors(error_msg):
                print(f"   🔍 Analysis: Blockhash-related error detected")
                print(f"   💡 Suggestion: Phase 1B blockhash handling needs improvement")
            else:
                print(f"   🔍 Analysis: Non-blockhash error")
                print(f"   💡 Suggestion: Check network, balance, or API connectivity")
            
            return False
        
    except Exception as e:
        print(f"\n❌ Real transaction test setup failed: {e}")
        return False

def main():
    """Run complete Phase 1B test suite."""
    print("🚀 PHASE 1B IMPLEMENTATION TEST SUITE")
    print("Testing improved transaction execution with fresh blockhash handling")
    print(f"Started at: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    
    tests = [
        ("Infrastructure Tests", test_phase1b_infrastructure),
        ("Transaction Pipeline Tests", test_phase1b_transaction_pipeline),
        ("Performance Tests", test_phase1b_performance_metrics),
        ("Real Transaction Test", test_phase1b_real_transaction)
    ]
    
    results = {}
    
    for test_name, test_func in tests:
        print(f"\n{'='*80}")
        print(f"🧪 Starting: {test_name}")
        print(f"{'='*80}")
        
        try:
            start_time = time.time()
            result = test_func()
            elapsed = time.time() - start_time
            
            results[test_name] = {
                'passed': result,
                'duration': elapsed
            }
            
            status = "✅ PASSED" if result else "❌ FAILED"
            print(f"\n{status} - {test_name} (took {elapsed:.2f}s)")
            
        except Exception as e:
            results[test_name] = {
                'passed': False,
                'duration': 0,
                'error': str(e)
            }
            print(f"\n❌ FAILED - {test_name} (exception: {e})")
    
    # Summary
    print(f"\n{'='*80}")
    print("📋 PHASE 1B TEST SUMMARY")
    print(f"{'='*80}")
    
    total_tests = len(tests)
    passed_tests = sum(1 for r in results.values() if r['passed'])
    failed_tests = total_tests - passed_tests
    
    print(f"Total tests: {total_tests}")
    print(f"Passed: {passed_tests}")
    print(f"Failed: {failed_tests}")
    print(f"Success rate: {passed_tests/total_tests*100:.1f}%")
    
    for test_name, result in results.items():
        status = "✅" if result['passed'] else "❌"
        duration = result['duration']
        print(f"{status} {test_name}: {duration:.2f}s")
        
        if not result['passed'] and 'error' in result:
            print(f"   Error: {result['error']}")
    
    # Final assessment
    print(f"\n{'='*80}")
    if passed_tests == total_tests:
        print("🎉 ALL TESTS PASSED! Phase 1B implementation is ready.")
        print("✅ Blockhash staleness issue has been resolved.")
        print("🚀 Ready to proceed with Phase 2 optimizations.")
    elif passed_tests >= total_tests - 1:
        print("⚠️  MOSTLY SUCCESSFUL - Minor issues detected.")
        print("💡 Consider addressing remaining issues before Phase 2.")
    else:
        print("❌ SIGNIFICANT ISSUES DETECTED")
        print("🔧 Phase 1B implementation needs additional work.")
        print("❗ Do not proceed to Phase 2 until these issues are resolved.")
    
    print(f"Completed at: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    
    return passed_tests == total_tests

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)