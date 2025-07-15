import requests
import json
import time
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from solana.rpc.api import Client
from solders.transaction import VersionedTransaction
from solders.pubkey import Pubkey as PublicKey
from solana.rpc.commitment import Commitment
import logging

from solana_wallet import SolanaWallet

logger = logging.getLogger(__name__)

@dataclass
class DEXToken:
    """Represents a token on a DEX."""
    mint: str
    symbol: str
    name: str
    decimals: int
    logo_uri: Optional[str] = None

@dataclass
class DEXPool:
    """Represents a liquidity pool."""
    pool_id: str
    token_a: str
    token_b: str
    token_a_symbol: str
    token_b_symbol: str
    liquidity: float
    fee_rate: float

@dataclass
class DEXPrice:
    """Represents a price quote."""
    input_mint: str
    output_mint: str
    input_amount: float
    output_amount: float
    price: float
    fee: float
    route: List[str]

class JupiterDEXClient:
    """Client for Jupiter DEX aggregator."""
    
    def __init__(self, wallet: SolanaWallet):
        self.wallet = wallet
        self.base_url = "https://quote-api.jup.ag/v6"
        self.session = requests.Session()
        self.session.headers.update({
            'Content-Type': 'application/json',
            'User-Agent': 'SolanaGridBot/1.0'
        })
        
    def get_quote(self, input_mint: str, output_mint: str, amount: int, slippage_bps: int = 50) -> Optional[DEXPrice]:
        """Get a price quote for a swap.
        
        Args:
            input_mint: Source token mint address
            output_mint: Destination token mint address  
            amount: Amount in smallest unit (lamports for SOL, etc.)
            slippage_bps: Slippage in basis points (50 = 0.5%)
        """
        max_retries = 3
        for attempt in range(max_retries):
            try:
                url = f"{self.base_url}/quote"
                params = {
                    "inputMint": input_mint,
                    "outputMint": output_mint,
                    "amount": str(amount),
                    "slippageBps": slippage_bps,
                    "restrictIntermediateTokens": "true"  # API expects string, not boolean
                }
                
                logger.debug(f"Jupiter quote request: {params}")
                response = self.session.get(url, params=params, timeout=10)
                response.raise_for_status()
                data = response.json()
                
                # Validate response structure - Jupiter v6 uses inAmount/outAmount
                if 'inAmount' not in data or 'outAmount' not in data:
                    logger.error(f"Invalid Jupiter response structure: {data}")
                    return None
                
                # Calculate display amounts (assuming 9 decimals for SOL, 6 for USDC)
                input_decimals = 9 if input_mint == "So11111111111111111111111111111111111111112" else 6
                output_decimals = 6 if output_mint == "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v" else 9
                
                input_amount_display = float(data['inAmount']) / (10 ** input_decimals)
                output_amount_display = float(data['outAmount']) / (10 ** output_decimals)
                
                # Calculate price (output per input unit)
                price = output_amount_display / input_amount_display if input_amount_display > 0 else 0
                
                route_info = []
                if 'routePlan' in data:
                    for step in data['routePlan']:
                        if 'swapInfo' in step:
                            route_info.append(step['swapInfo'].get('label', 'Unknown'))
                
                result = DEXPrice(
                    input_mint=input_mint,
                    output_mint=output_mint,
                    input_amount=input_amount_display,
                    output_amount=output_amount_display,
                    price=price,
                    fee=float(data.get('priceImpactPct', 0)),
                    route=route_info
                )
                
                logger.info(f"Jupiter quote: {input_amount_display:.4f} -> {output_amount_display:.4f} (price: {price:.6f})")
                return result
                
            except requests.exceptions.Timeout:
                logger.warning(f"Jupiter API timeout (attempt {attempt + 1}/{max_retries})")
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)  # Exponential backoff
                    continue
            except requests.exceptions.HTTPError as e:
                if e.response.status_code == 429:  # Rate limit
                    logger.warning(f"Jupiter API rate limit (attempt {attempt + 1}/{max_retries})")
                    if attempt < max_retries - 1:
                        time.sleep(5 * (attempt + 1))  # Longer wait for rate limits
                        continue
                else:
                    try:
                        error_text = e.response.text
                        logger.error(f"Jupiter API HTTP error {e.response.status_code}: {error_text}")
                    except:
                        logger.error(f"Jupiter API HTTP error: {e}")
                    break
            except Exception as e:
                logger.error(f"Jupiter quote failed (attempt {attempt + 1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    time.sleep(1)
                    continue
                
        return None
    
    def get_raw_quote(self, input_mint: str, output_mint: str, amount: int, slippage_bps: int = 50) -> Optional[dict]:
        """Get raw quote response from Jupiter API for use with swap transaction.
        
        Args:
            input_mint: Source token mint address
            output_mint: Destination token mint address  
            amount: Amount in smallest unit (lamports for SOL, etc.)
            slippage_bps: Slippage in basis points (50 = 0.5%)
            
        Returns:
            Raw Jupiter quote response dict or None if failed
        """
        max_retries = 3
        for attempt in range(max_retries):
            try:
                url = f"{self.base_url}/quote"
                params = {
                    "inputMint": input_mint,
                    "outputMint": output_mint,
                    "amount": str(amount),
                    "slippageBps": slippage_bps,
                    "restrictIntermediateTokens": "true"
                }
                
                logger.debug(f"Jupiter raw quote request: {params}")
                response = self.session.get(url, params=params, timeout=10)
                response.raise_for_status()
                data = response.json()
                
                # Validate response structure - Jupiter v6 uses inAmount/outAmount
                if 'inAmount' not in data or 'outAmount' not in data:
                    logger.error(f"Invalid Jupiter response structure: {data}")
                    return None
                
                logger.info(f"Jupiter raw quote successful")
                return data
                
            except requests.exceptions.Timeout:
                logger.warning(f"Jupiter raw quote timeout (attempt {attempt + 1}/{max_retries})")
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)
                    continue
            except requests.exceptions.HTTPError as e:
                if e.response.status_code == 429:
                    logger.warning(f"Jupiter raw quote rate limit (attempt {attempt + 1}/{max_retries})")
                    if attempt < max_retries - 1:
                        time.sleep(5 * (attempt + 1))
                        continue
                else:
                    try:
                        error_text = e.response.text
                        logger.error(f"Jupiter raw quote HTTP error {e.response.status_code}: {error_text}")
                    except:
                        logger.error(f"Jupiter raw quote HTTP error: {e}")
                    break
            except Exception as e:
                logger.error(f"Jupiter raw quote failed (attempt {attempt + 1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    time.sleep(1)
                    continue
                
        return None
    
    def get_swap_transaction(self, quote_response: dict, user_public_key: str) -> Optional[str]:
        """Get swap transaction from Jupiter quote response.
        
        Args:
            quote_response: Raw quote response from Jupiter API
            user_public_key: User's public key as string
            
        Returns:
            Base64 encoded serialized transaction or None if failed
        """
        max_retries = 3
        for attempt in range(max_retries):
            try:
                url = f"{self.base_url}/swap"
                
                payload = {
                    "quoteResponse": quote_response,
                    "userPublicKey": user_public_key,
                    "wrapAndUnwrapSol": True,
                    "dynamicComputeUnitLimit": True,
                    # CRITICAL FIX: Force Jupiter to NOT use address table lookups for devnet compatibility
                    "useVersionedTransactions": False,  # Use legacy transactions without address tables
                    "asLegacyTransaction": True,        # Force legacy format for devnet compatibility
                    "prioritizationFeeLamports": 1000,
                    "useTokenLedger": False
                }
                
                logger.debug(f"Jupiter swap request for user: {user_public_key}")
                response = self.session.post(url, json=payload, timeout=15)
                response.raise_for_status()
                data = response.json()
                
                # Validate response structure
                if 'swapTransaction' not in data:
                    logger.error(f"Invalid Jupiter swap response: missing swapTransaction")
                    return None
                
                transaction_base64 = data['swapTransaction']
                logger.info(f"Jupiter swap transaction prepared successfully")
                return transaction_base64
                
            except requests.exceptions.Timeout:
                logger.warning(f"Jupiter swap API timeout (attempt {attempt + 1}/{max_retries})")
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)
                    continue
            except requests.exceptions.HTTPError as e:
                if e.response.status_code == 429:
                    logger.warning(f"Jupiter swap API rate limit (attempt {attempt + 1}/{max_retries})")
                    if attempt < max_retries - 1:
                        time.sleep(5 * (attempt + 1))
                        continue
                else:
                    logger.error(f"Jupiter swap API HTTP error: {e}")
                    break
            except Exception as e:
                logger.error(f"Jupiter swap failed (attempt {attempt + 1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    time.sleep(1)
                    continue
                
        return None

class RaydiumDEXClient:
    """Client for Raydium DEX."""
    
    def __init__(self, wallet: SolanaWallet):
        self.wallet = wallet
        self.base_url = "https://api.raydium.io/v2"
        self.session = requests.Session()
    
    def get_pools(self) -> List[DEXPool]:
        """Get all Raydium pools."""
        try:
            response = self.session.get(f"{self.base_url}/main/pools")
            response.raise_for_status()
            data = response.json()
            
            pools = []
            for pool in data:
                pools.append(DEXPool(
                    pool_id=pool['id'],
                    token_a=pool['baseMint'],
                    token_b=pool['quoteMint'],
                    token_a_symbol=pool['baseSymbol'],
                    token_b_symbol=pool['quoteSymbol'],
                    liquidity=float(pool.get('liquidity', 0)),
                    fee_rate=float(pool.get('feeRate', 0.0025))
                ))
            
            return pools
            
        except Exception as e:
            logger.error(f"Failed to get Raydium pools: {e}")
            return []
    
    def get_pool_price(self, pool_id: str) -> Optional[float]:
        """Get price for a specific pool."""
        try:
            response = self.session.get(f"{self.base_url}/main/pool/{pool_id}")
            response.raise_for_status()
            data = response.json()
            
            if 'price' in data:
                return float(data['price'])
            return None
            
        except Exception as e:
            logger.error(f"Failed to get pool price: {e}")
            return None

class OrcaDEXClient:
    """Client for Orca DEX."""
    
    def __init__(self, wallet: SolanaWallet):
        self.wallet = wallet
        self.base_url = "https://api.orca.so"
        self.session = requests.Session()
    
    def get_pools(self) -> List[DEXPool]:
        """Get all Orca pools."""
        try:
            response = self.session.get(f"{self.base_url}/v1/pools")
            response.raise_for_status()
            data = response.json()
            
            pools = []
            for pool in data:
                pools.append(DEXPool(
                    pool_id=pool['address'],
                    token_a=pool['tokenA'],
                    token_b=pool['tokenB'],
                    token_a_symbol=pool['tokenASymbol'],
                    token_b_symbol=pool['tokenBSymbol'],
                    liquidity=float(pool.get('liquidity', 0)),
                    fee_rate=float(pool.get('fee', 0.003))
                ))
            
            return pools
            
        except Exception as e:
            logger.error(f"Failed to get Orca pools: {e}")
            return []

class DEXManager:
    """Manages multiple DEX clients for optimal trading."""
    
    def __init__(self, wallet: SolanaWallet):
        self.wallet = wallet
        self.jupiter = JupiterDEXClient(wallet)
        self.raydium = RaydiumDEXClient(wallet)
        self.orca = OrcaDEXClient(wallet)
        
        # Common token mints
        self.tokens = {
            "SOL": "So11111111111111111111111111111111111111112",
            "USDC": "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
            "USDT": "Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB",
            "ETH": "7vfCXTUXx5WJV5JADk17DUJ4ksgau7utNKj4b963voxs",
            "BONK": "DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB263",
            "RAY": "4k3Dyjzvzp8eMZWUXbBCjEvwSkkk59S5iCNLY3QrkX6R",
            "SRM": "SRMuApVNdxXokk5GT7XD5cUUgXMBCoAz2LHeuAoKWRt",
            "ORCA": "orcaEKTdK7LKz57vaAYr9QeNsVEPfiu6QeMU1kektZE",
        }
    
    def get_best_price(self, input_token: str, output_token: str, amount: float) -> Optional[DEXPrice]:
        """Get the best price across all DEXs."""
        try:
            input_mint = self.tokens.get(input_token, input_token)
            output_mint = self.tokens.get(output_token, output_token)
            
            # Convert amount to smallest unit (lamports/smallest token unit)
            if input_token == "SOL":
                amount_smallest = int(amount * 1e9)  # SOL has 9 decimals
            else:
                amount_smallest = int(amount * 1e6)  # Most tokens have 6 decimals
            
            # Try Jupiter first (aggregator)
            quote = self.jupiter.get_quote(input_mint, output_mint, amount_smallest)
            if quote:
                logger.info(f"Jupiter quote: {quote.price:.6f}")
                return quote
            
            # Fallback to direct DEX queries
            logger.warning("Jupiter quote failed, trying direct DEX queries")
            return None
            
        except Exception as e:
            logger.error(f"Failed to get best price: {e}")
            return None
    
    def execute_swap(self, input_token: str, output_token: str, amount: float, slippage_bps: int = 50) -> Optional[str]:
        """Execute a complete swap workflow using Jupiter.
        
        Args:
            input_token: Source token symbol (e.g., 'SOL')
            output_token: Destination token symbol (e.g., 'USDC')
            amount: Amount to swap in token units
            slippage_bps: Slippage tolerance in basis points
            
        Returns:
            Transaction signature if successful, None otherwise
        """
        try:
            # Log swap attempt
            self.log_swap_attempt(input_token, output_token, amount, slippage_bps)
            
            input_mint = self.tokens.get(input_token, input_token)
            output_mint = self.tokens.get(output_token, output_token)
            
            # Convert amount to smallest unit
            if input_token == "SOL":
                amount_smallest = int(amount * 1e9)
            else:
                amount_smallest = int(amount * 1e6)
            
            # Step 1: Get raw quote from Jupiter
            logger.info(f"Getting quote for {amount} {input_token} -> {output_token}")
            quote_response = self.jupiter.get_raw_quote(input_mint, output_mint, amount_smallest, slippage_bps)
            if not quote_response:
                logger.error("Failed to get quote from Jupiter")
                return None
            
            # Step 2: Get swap transaction
            user_public_key = str(self.wallet.public_key)
            transaction_b64 = self.jupiter.get_swap_transaction(quote_response, user_public_key)
            if not transaction_b64:
                logger.error("Failed to get swap transaction")
                return None
            
            # Step 3: Sign and send transaction
            signature = self.sign_and_send_transaction(transaction_b64)
            if not signature:
                logger.error("Failed to sign and send transaction")
                return None
            
            # Step 4: Wait for confirmation
            confirmed = self.wait_for_confirmation(signature)
            if confirmed:
                # Log detailed transaction success info
                self.log_transaction_success(signature, input_token, output_token, amount, quote_response)
                return signature
            else:
                logger.error(f"Transaction failed to confirm: {signature}")
                logger.error(f"Explorer: https://explorer.solana.com/tx/{signature}?cluster=devnet")
                return None
            
        except Exception as e:
            logger.error(f"Failed to execute swap: {e}")
            return None
    
    def execute_swap_with_quote_response(self, quote_response: dict) -> Optional[str]:
        """Execute swap using raw Jupiter quote response.
        
        Args:
            quote_response: Raw quote response from Jupiter API
            
        Returns:
            Transaction signature if successful, None otherwise
        """
        try:
            user_public_key = str(self.wallet.public_key)
            
            # Step 1: Get serialized transaction from Jupiter
            transaction_b64 = self.jupiter.get_swap_transaction(quote_response, user_public_key)
            if not transaction_b64:
                logger.error("Failed to get swap transaction")
                return None
            
            # Step 2: Deserialize and send transaction
            import base64
            from solders.transaction import VersionedTransaction
            
            transaction_bytes = base64.b64decode(transaction_b64)
            transaction = VersionedTransaction.from_bytes(transaction_bytes)
            
            # CRITICAL FIX: Use fresh blockhash reconstruction for network compatibility
            # Jupiter transactions contain wrong network blockhashes - reconstruct for proper network
            logger.info("🔧 Reconstructing transaction with fresh network blockhash...")
            signed_tx = self.wallet.sign_transaction_with_fresh_blockhash(transaction)
            signature = self.wallet.send_transaction(signed_tx)
            
            logger.info(f"Swap executed successfully: {signature}")
            return signature
            
        except Exception as e:
            logger.error(f"Failed to execute swap with quote response: {e}")
            return None
    
    def get_market_price(self, token_pair: str) -> Optional[float]:
        """Get current market price for a token pair."""
        try:
            # Parse token pair (e.g., "SOL/USDC")
            tokens = token_pair.split('/')
            if len(tokens) != 2:
                logger.error(f"Invalid token pair format: {token_pair}")
                return None
            
            input_token, output_token = tokens
            input_mint = self.tokens.get(input_token, input_token)
            output_mint = self.tokens.get(output_token, output_token)
            
            # Use 1 SOL as base amount for price calculation
            base_amount = 1_000_000_000  # 1 SOL in lamports
            
            quote = self.jupiter.get_quote(input_mint, output_mint, base_amount)
            if quote:
                return quote.price
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to get market price: {e}")
            return None
    
    def sign_and_send_transaction(self, transaction_b64: str) -> Optional[str]:
        """Sign transaction with wallet and broadcast to Solana network.
        
        Args:
            transaction_b64: Base64 encoded serialized transaction
            
        Returns:
            Transaction signature if successful, None otherwise
        """
        try:
            import base64
            from solders.transaction import VersionedTransaction
            from solana.rpc.commitment import Commitment
            
            # Deserialize transaction from base64
            transaction_bytes = base64.b64decode(transaction_b64)
            
            # Try to parse as VersionedTransaction first, then fall back to legacy Transaction
            try:
                transaction = VersionedTransaction.from_bytes(transaction_bytes)
                logger.debug("Parsed as VersionedTransaction")
            except Exception as e:
                logger.debug(f"Failed to parse as VersionedTransaction: {e}")
                from solders.transaction import Transaction
                transaction = Transaction.from_bytes(transaction_bytes)
                logger.debug("Parsed as legacy Transaction")
            
            logger.info("Signing transaction...")
            
            # CRITICAL FIX: Use fresh blockhash reconstruction to fix network mismatch
            # Jupiter provides transactions with mainnet blockhashes - reconstruct with devnet blockhash
            logger.info("🔧 Reconstructing transaction with fresh devnet blockhash...")
            signed_tx = self.wallet.sign_transaction_with_fresh_blockhash(transaction)
            
            logger.info("Broadcasting transaction to Solana network...")
            
            # Broadcast transaction
            # Use wallet's send_transaction method which handles options properly
            signature = self.wallet.send_transaction(signed_tx)
            # Create response object for compatibility
            response = type('Response', (), {'value': signature})()
            
            if response.value:
                signature = response.value
                logger.info(f"Transaction broadcasted: {signature}")
                return signature
            else:
                logger.error("Failed to broadcast transaction: no signature returned")
                return None
                
        except Exception as e:
            logger.error(f"Failed to sign and send transaction: {e}")
            return None
    
    def execute_swap_with_fresh_transaction(self, input_token: str, output_token: str, 
                                          amount: float, slippage_bps: int = 50) -> Optional[str]:
        """Phase 1B: Execute swap with true fresh transaction pipeline to eliminate blockhash staleness.
        
        This method implements a completely fresh transaction workflow:
        1. Get fresh quote from Jupiter API
        2. Immediately request fresh transaction with current blockhash
        3. Sign and broadcast with minimal delay
        
        Args:
            input_token: Input token symbol (e.g., 'SOL')
            output_token: Output token symbol (e.g., 'USDC') 
            amount: Amount to swap
            slippage_bps: Slippage tolerance in basis points (50 = 0.5%)
            
        Returns:
            Transaction signature if successful, None otherwise
        """
        try:
            import time
            start_time = time.time()
            
            self.log_transaction_pipeline("PHASE_1B", "INITIATED", {
                "input_token": input_token,
                "output_token": output_token, 
                "amount": amount,
                "slippage_bps": slippage_bps
            })
            
            input_mint = self.tokens.get(input_token, input_token)
            output_mint = self.tokens.get(output_token, output_token)
            
            # Convert amount to smallest unit
            if input_token == "SOL":
                amount_smallest = int(amount * 1_000_000_000)  # 9 decimals
            else:
                amount_smallest = int(amount * 1_000_000)      # 6 decimals
            
            # Step 1: Get fresh raw quote (required for transaction creation)
            quote_start = time.time()
            self.log_transaction_pipeline("QUOTE", "REQUESTING", {
                "amount_raw": amount_smallest,
                "slippage_bps": slippage_bps
            })
            
            raw_quote = self.jupiter.get_raw_quote(input_mint, output_mint, amount_smallest, slippage_bps)
            if not raw_quote:
                self.log_transaction_pipeline("QUOTE", "FAILED", {"reason": "No quote received"})
                logger.error("❌ Failed to get Jupiter raw quote")
                return None
            
            quote_elapsed = time.time() - quote_start
            self.log_transaction_pipeline("QUOTE", "READY", {
                "elapsed": f"{quote_elapsed:.3f}s",
                "input_amount": raw_quote.get('inAmount'),
                "output_amount": raw_quote.get('outAmount')
            })
            
            # Minimal delay before transaction creation (let network stabilize)
            time.sleep(0.1)  # 100ms minimal delay
            
            # Step 2: Immediately get fresh transaction with current blockhash
            tx_start = time.time()
            user_public_key = str(self.wallet.public_key)
            
            self.log_transaction_pipeline("TRANSACTION", "REQUESTING", {
                "user_key": user_public_key[:8] + "...",
                "quote_age": f"{time.time() - quote_start:.3f}s"
            })
            
            fresh_transaction_b64 = self.jupiter.get_swap_transaction(raw_quote, user_public_key)
            if not fresh_transaction_b64:
                self.log_transaction_pipeline("TRANSACTION", "FAILED", {"reason": "No transaction received"})
                logger.error("❌ Failed to get fresh swap transaction")
                return None
            
            tx_elapsed = time.time() - tx_start
            self.log_transaction_pipeline("TRANSACTION", "READY", {
                "elapsed": f"{tx_elapsed:.3f}s"
            })
            
            # Step 3: Immediate execution with fresh blockhash handling
            exec_start = time.time()
            signature = self.execute_fresh_transaction_immediate(fresh_transaction_b64)
            
            exec_elapsed = time.time() - exec_start
            total_elapsed = time.time() - start_time
            
            if signature:
                self.log_transaction_pipeline("PHASE_1B", "SUCCESS", {
                    "signature": signature,
                    "exec_time": f"{exec_elapsed:.3f}s",
                    "total_time": f"{total_elapsed:.3f}s",
                    "explorer": f"https://explorer.solana.com/tx/{signature}?cluster=devnet"
                })
                logger.info(f"✅ Phase 1B execution successful: {signature}")
                return signature
            else:
                self.log_transaction_pipeline("PHASE_1B", "FAILED", {
                    "exec_time": f"{exec_elapsed:.3f}s",
                    "total_time": f"{total_elapsed:.3f}s"
                })
                logger.error(f"❌ Phase 1B execution failed")
                return None
            
        except Exception as e:
            logger.error(f"❌ Phase 1B transaction execution failed: {e}")
            return None
    
    def execute_fresh_transaction_immediate(self, transaction_b64: str) -> Optional[str]:
        """Phase 1B: Network-compatible transaction execution with fresh blockhash reconstruction.
        
        CRITICAL FIX: This method solves the "Blockhash not found" issue by reconstructing
        Jupiter transactions with fresh devnet blockhashes instead of using mainnet blockhashes.
        
        Root Cause Fixed: Jupiter API provides transactions with mainnet blockhashes that
        don't exist on devnet, causing "SendTransactionPreflightFailureMessage" errors.
        
        Implementation:
        1. Parse Jupiter transaction (contains wrong network blockhash)
        2. Reconstruct with fresh devnet blockhash immediately before signing
        3. Sign with network-compatible blockhash
        4. Broadcast to correct network
        
        Args:
            transaction_b64: Base64 encoded serialized transaction from Jupiter
            
        Returns:
            Transaction signature if successful, None otherwise
        """
        try:
            import base64
            import time
            from solders.transaction import VersionedTransaction, Transaction
            from solders.message import MessageV0
            from solders.hash import Hash
            
            execution_start = time.time()
            
            # Step 1: Parse transaction bytes
            transaction_bytes = base64.b64decode(transaction_b64)
            
            # Try to parse as VersionedTransaction first, then fall back to legacy Transaction
            try:
                original_transaction = VersionedTransaction.from_bytes(transaction_bytes)
                is_versioned = True
                logger.debug("🔄 Parsed as VersionedTransaction")
            except Exception as e:
                logger.debug(f"🔄 VersionedTransaction parse failed: {e}, trying legacy Transaction")
                original_transaction = Transaction.from_bytes(transaction_bytes)
                is_versioned = False
                logger.debug("🔄 Parsed as legacy Transaction")
            
            # Step 2: Get fresh blockhash immediately
            blockhash_start = time.time()
            recent_blockhash_response = self.wallet.rpc_client.get_latest_blockhash()
            fresh_blockhash = recent_blockhash_response.value.blockhash
            blockhash_elapsed = time.time() - blockhash_start
            
            self.log_transaction_pipeline("BLOCKHASH", "FRESH", {
                "elapsed": f"{blockhash_elapsed:.3f}s",
                "blockhash": str(fresh_blockhash)[:8] + "..."
            })
            
            # Step 3: Create transaction with fresh blockhash
            sign_start = time.time()
            
            if is_versioned:
                # For VersionedTransaction, create new message with fresh blockhash
                message = original_transaction.message
                
                # Create new message with fresh blockhash
                if isinstance(message, MessageV0):
                    # For V0 message, use try_compile to reconstruct with fresh blockhash
                    # Extract payer (first account key)
                    payer = message.account_keys[0] if message.account_keys else self.wallet.public_key
                    
                    # Reconstruct with fresh blockhash using proper API
                    new_message = MessageV0.try_compile(
                        payer=payer,
                        instructions=message.instructions,
                        address_lookup_table_accounts=message.address_table_lookups,
                        recent_blockhash=fresh_blockhash
                    )
                    
                    # Create new VersionedTransaction with fresh blockhash
                    fresh_transaction = VersionedTransaction(new_message, [])
                else:
                    # Fallback: Use original transaction but sign with fresh blockhash manually
                    logger.warning("🔄 VersionedTransaction with non-V0 message, using original with fresh signing")
                    fresh_transaction = original_transaction
            else:
                # For legacy Transaction, use the original transaction but update blockhash through signing
                logger.debug("🔄 Using legacy Transaction with fresh blockhash through signing")
                fresh_transaction = original_transaction
            
            # Step 4: Sign with fresh transaction and blockhash
            signed_tx = self.wallet.sign_transaction_with_fresh_blockhash(fresh_transaction)
            sign_elapsed = time.time() - sign_start
            
            self.log_transaction_pipeline("SIGNING", "COMPLETED", {
                "elapsed": f"{sign_elapsed:.3f}s",
                "transaction_type": "VersionedTransaction" if is_versioned else "Transaction"
            })
            
            # Step 5: Broadcast immediately
            broadcast_start = time.time()
            signature = self.wallet.send_transaction(signed_tx)
            broadcast_elapsed = time.time() - broadcast_start
            
            total_elapsed = time.time() - execution_start
            
            if signature:
                self.log_transaction_pipeline("BROADCAST", "SUCCESS", {
                    "signature": signature,
                    "broadcast_time": f"{broadcast_elapsed:.3f}s",
                    "total_execution": f"{total_elapsed:.3f}s"
                })
                logger.info(f"✅ Phase 1B fresh transaction executed: {signature}")
                return signature
            else:
                self.log_transaction_pipeline("BROADCAST", "FAILED", {
                    "broadcast_time": f"{broadcast_elapsed:.3f}s",
                    "total_execution": f"{total_elapsed:.3f}s"
                })
                logger.error("❌ Phase 1B broadcast failed: no signature returned")
                return None
                
        except Exception as e:
            error_msg = str(e)
            total_elapsed = time.time() - execution_start if 'execution_start' in locals() else 0
            
            self.log_transaction_pipeline("EXECUTION", "ERROR", {
                "error": error_msg,
                "total_time": f"{total_elapsed:.3f}s"
            })
            
            # Check for specific error types
            if "too large" in error_msg.lower():
                logger.error(f"❌ Phase 1B transaction size error: {error_msg}")
                logger.error("💡 Consider using smaller amounts or simpler routing")
            elif self.detect_blockhash_errors(error_msg):
                logger.error(f"❌ Phase 1B blockhash error: {error_msg}")
            else:
                logger.error(f"❌ Phase 1B execution failed: {error_msg}")
            return None
    
    def sign_and_send_transaction_fast(self, transaction_b64: str) -> Optional[str]:
        """Fast-path transaction signing and broadcasting (legacy method).
        
        Args:
            transaction_b64: Base64 encoded serialized transaction
            
        Returns:
            Transaction signature if successful, None otherwise
        """
        try:
            import base64
            from solders.transaction import VersionedTransaction
            
            # Parse transaction (no blockhash modification)
            transaction_bytes = base64.b64decode(transaction_b64)
            
            # Try to parse as VersionedTransaction first, then fall back to legacy Transaction
            try:
                transaction = VersionedTransaction.from_bytes(transaction_bytes)
                logger.debug("Parsed as VersionedTransaction")
            except Exception as e:
                logger.debug(f"Failed to parse as VersionedTransaction: {e}")
                from solders.transaction import Transaction
                transaction = Transaction.from_bytes(transaction_bytes)
                logger.debug("Parsed as legacy Transaction")
            
            # CRITICAL FIX: Use fresh blockhash reconstruction for network compatibility
            # This ensures devnet transactions use devnet blockhashes, not mainnet ones from Jupiter
            logger.info("🔧 Reconstructing with fresh devnet blockhash...")
            signed_tx = self.wallet.sign_transaction_with_fresh_blockhash(transaction)
            
            # Broadcast immediately
            signature = self.wallet.send_transaction(signed_tx)
            
            if signature:
                logger.info(f"Fast transaction executed: {signature}")
                return signature
            else:
                logger.error("Fast transaction execution failed: no signature returned")
                return None
                
        except Exception as e:
            error_msg = str(e)
            if self.detect_blockhash_errors(error_msg):
                logger.error(f"❌ Blockhash-related error detected: {error_msg}")
            else:
                logger.error(f"❌ Fast transaction execution failed: {error_msg}")
            return None
    
    def detect_blockhash_errors(self, error_message: str) -> bool:
        """Detect various forms of blockhash-related errors.
        
        Args:
            error_message: Error message to analyze
            
        Returns:
            True if error is blockhash-related, False otherwise
        """
        blockhash_indicators = [
            "recent_blockhash",
            "Blockhash not found", 
            "Transaction has expired",
            "Blockhash not recognized",
            "blockhash not found",
            "transaction has expired"
        ]
        error_str = str(error_message).lower()
        return any(indicator.lower() in error_str for indicator in blockhash_indicators)
    
    def execute_swap_optimized_phase1b(self, input_token: str, output_token: str, 
                                      amount: float, slippage_bps: int = 50) -> Optional[str]:
        """Optimized Phase 1B swap execution with minimal timing delays.
        
        This method combines the best of Phase 1B improvements:
        - Immediate fresh transaction request
        - Zero-delay execution pipeline  
        - Comprehensive error handling
        - Performance monitoring
        
        Args:
            input_token: Input token symbol
            output_token: Output token symbol
            amount: Amount to swap
            slippage_bps: Slippage in basis points
            
        Returns:
            Transaction signature if successful, None otherwise
        """
        try:
            import time
            
            total_start = time.time()
            
            self.log_transaction_pipeline("OPTIMIZED_PHASE1B", "STARTED", {
                "pair": f"{input_token}/{output_token}",
                "amount": amount,
                "slippage_bps": slippage_bps
            })
            
            # Step 1: Get fresh quote and transaction in rapid succession
            input_mint = self.tokens.get(input_token, input_token)
            output_mint = self.tokens.get(output_token, output_token)
            amount_smallest = int(amount * (1e9 if input_token == "SOL" else 1e6))
            
            # Get quote
            quote_start = time.time()
            raw_quote = self.jupiter.get_raw_quote(input_mint, output_mint, amount_smallest, slippage_bps)
            if not raw_quote:
                self.log_transaction_pipeline("QUOTE", "FAILED", {"reason": "No quote received"})
                return None
            quote_elapsed = time.time() - quote_start
            
            # Immediate transaction request (no delay)
            tx_start = time.time()
            user_public_key = str(self.wallet.public_key)
            transaction_b64 = self.jupiter.get_swap_transaction(raw_quote, user_public_key)
            if not transaction_b64:
                self.log_transaction_pipeline("TRANSACTION", "FAILED", {"reason": "No transaction received"})
                return None
            tx_elapsed = time.time() - tx_start
            
            self.log_transaction_pipeline("PIPELINE_TIMING", "ANALYSIS", {
                "quote_time": f"{quote_elapsed:.3f}s",
                "tx_time": f"{tx_elapsed:.3f}s",
                "total_prep": f"{time.time() - total_start:.3f}s"
            })
            
            # Step 2: Immediate execution with fresh blockhash
            exec_start = time.time()
            signature = self.execute_fresh_transaction_immediate(transaction_b64)
            exec_elapsed = time.time() - exec_start
            total_elapsed = time.time() - total_start
            
            if signature:
                self.log_transaction_pipeline("OPTIMIZED_PHASE1B", "SUCCESS", {
                    "signature": signature,
                    "exec_time": f"{exec_elapsed:.3f}s",
                    "total_time": f"{total_elapsed:.3f}s",
                    "performance": "excellent" if total_elapsed < 2.0 else "good" if total_elapsed < 3.0 else "needs_improvement"
                })
                return signature
            else:
                self.log_transaction_pipeline("OPTIMIZED_PHASE1B", "FAILED", {
                    "exec_time": f"{exec_elapsed:.3f}s",
                    "total_time": f"{total_elapsed:.3f}s"
                })
                return None
                
        except Exception as e:
            self.log_transaction_pipeline("OPTIMIZED_PHASE1B", "ERROR", {
                "error": str(e),
                "error_type": type(e).__name__
            })
            logger.error(f"❌ Optimized Phase 1B execution failed: {e}")
            return None
    
    def log_transaction_pipeline(self, stage: str, status: str, details: dict = None):
        """Log detailed transaction pipeline progress.
        
        Args:
            stage: Pipeline stage (e.g., 'QUOTE', 'TRANSACTION', 'EXECUTION')
            status: Status of the stage (e.g., 'READY', 'CREATED', 'COMPLETED', 'FAILED')
            details: Optional dictionary of additional details to log
        """
        logger.info(f"🔄 TRANSACTION PIPELINE: {stage} - {status}")
        if details:
            for key, value in details.items():
                logger.info(f"   📊 {key}: {value}")
    
    def wait_for_confirmation(self, signature: str, timeout: int = 60) -> bool:
        """Monitor transaction until confirmed or timeout.
        
        Args:
            signature: Transaction signature to monitor
            timeout: Maximum wait time in seconds
            
        Returns:
            True if confirmed, False if timeout or failed
        """
        try:
            from solana.rpc.commitment import Commitment
            import time
            
            start_time = time.time()
            logger.info(f"Waiting for confirmation: {signature}")
            
            while time.time() - start_time < timeout:
                try:
                    # Check transaction status
                    response = self.wallet.rpc_client.get_signature_statuses([signature])
                    
                    if response.value and len(response.value) > 0:
                        status = response.value[0]
                        
                        if status is not None:
                            if status.err is None:
                                # Transaction succeeded
                                confirmation_status = getattr(status, 'confirmation_status', None)
                                if confirmation_status in ['confirmed', 'finalized']:
                                    logger.info(f"Transaction confirmed: {signature} ({confirmation_status})")
                                    return True
                                else:
                                    logger.debug(f"Transaction status: {confirmation_status}")
                            else:
                                # Transaction failed
                                logger.error(f"Transaction failed: {signature}, error: {status.err}")
                                return False
                    
                    # Wait before next check
                    time.sleep(2)
                    
                except Exception as e:
                    logger.warning(f"Error checking transaction status: {e}")
                    time.sleep(2)
                    continue
            
            logger.warning(f"Transaction confirmation timeout: {signature}")
            return False
            
        except Exception as e:
            logger.error(f"Failed to wait for confirmation: {e}")
            return False
    
    def get_transaction_status(self, signature: str) -> Dict:
        """Get detailed transaction status and information.
        
        Args:
            signature: Transaction signature to check
            
        Returns:
            Dictionary with transaction status details
        """
        try:
            from solana.rpc.commitment import Commitment
            
            # Get signature status
            sig_response = self.wallet.rpc_client.get_signature_statuses([signature])
            
            # Get full transaction details
            tx_response = self.wallet.rpc_client.get_transaction(
                signature,
                commitment=Commitment("confirmed"),
                encoding="json",
                max_supported_transaction_version=0
            )
            
            status_info = {
                'signature': signature,
                'status': 'unknown',
                'confirmation_status': None,
                'slot': None,
                'block_time': None,
                'fee': None,
                'error': None,
                'explorer_url': f"https://explorer.solana.com/tx/{signature}?cluster=devnet"
            }
            
            # Parse signature status
            if sig_response.value and len(sig_response.value) > 0:
                sig_status = sig_response.value[0]
                if sig_status is not None:
                    status_info['confirmation_status'] = getattr(sig_status, 'confirmation_status', None)
                    status_info['slot'] = getattr(sig_status, 'slot', None)
                    
                    if sig_status.err is None:
                        status_info['status'] = 'success'
                    else:
                        status_info['status'] = 'failed'
                        status_info['error'] = str(sig_status.err)
            
            # Parse transaction details
            if tx_response.value:
                tx_data = tx_response.value
                status_info['block_time'] = getattr(tx_data, 'block_time', None)
                
                # Extract fee information
                if hasattr(tx_data, 'transaction') and hasattr(tx_data.transaction, 'meta'):
                    meta = tx_data.transaction.meta
                    if meta and hasattr(meta, 'fee'):
                        status_info['fee'] = meta.fee
            
            return status_info
            
        except Exception as e:
            logger.error(f"Failed to get transaction status: {e}")
            return {
                'signature': signature,
                'status': 'error',
                'error': str(e),
                'explorer_url': f"https://explorer.solana.com/tx/{signature}?cluster=devnet"
            }
    
    def get_token_balance(self, token_symbol: str) -> float:
        """Get token balance."""
        try:
            balances = self.wallet.get_token_balances()
            token_mint = self.tokens.get(token_symbol)
            
            if token_symbol == "SOL":
                return self.wallet.get_balance()
            
            for balance in balances:
                if balance.mint == token_mint:
                    return balance.balance
            
            return 0.0
            
        except Exception as e:
            logger.error(f"Failed to get token balance: {e}")
            return 0.0
    
    def log_transaction_success(self, signature: str, input_token: str, output_token: str, amount: float, quote_response: dict):
        """Log detailed transaction success information.
        
        Args:
            signature: Transaction signature
            input_token: Source token symbol
            output_token: Destination token symbol
            amount: Input amount
            quote_response: Original quote response from Jupiter
        """
        try:
            # Extract amounts from quote response
            input_decimals = 9 if input_token == "SOL" else 6
            output_decimals = 6 if output_token == "USDC" else 9
            
            input_amount_display = float(quote_response['inAmount']) / (10 ** input_decimals)
            output_amount_display = float(quote_response['outAmount']) / (10 ** output_decimals)
            
            # Calculate effective price
            price = output_amount_display / input_amount_display if input_amount_display > 0 else 0
            
            # Get transaction status for fee information
            tx_status = self.get_transaction_status(signature)
            fee_sol = tx_status.get('fee', 0) / 1e9 if tx_status.get('fee') else 0
            
            # Create comprehensive log entry
            logger.info("="*60)
            logger.info(f"🎉 SWAP EXECUTED SUCCESSFULLY")
            logger.info(f"📝 Transaction: {signature}")
            logger.info(f"🔗 Explorer: {tx_status.get('explorer_url', f'https://explorer.solana.com/tx/{signature}?cluster=devnet')}")
            logger.info(f"💱 Swap: {input_amount_display:.4f} {input_token} → {output_amount_display:.4f} {output_token}")
            logger.info(f"💰 Price: {price:.6f} {output_token}/{input_token}")
            logger.info(f"💸 Fee: {fee_sol:.6f} SOL")
            logger.info(f"⏱️  Status: {tx_status.get('confirmation_status', 'confirmed')}")
            
            # Extract route information if available
            if 'routePlan' in quote_response:
                route_info = []
                for step in quote_response['routePlan']:
                    if 'swapInfo' in step:
                        route_info.append(step['swapInfo'].get('label', 'Unknown'))
                if route_info:
                    logger.info(f"🛤️  Route: {' → '.join(route_info)}")
            
            logger.info("="*60)
            
        except Exception as e:
            logger.error(f"Failed to log transaction success details: {e}")
            # Fallback to basic logging
            logger.info(f"Swap executed successfully: {signature}")
            logger.info(f"Explorer: https://explorer.solana.com/tx/{signature}?cluster=devnet")
    
    def log_swap_attempt(self, input_token: str, output_token: str, amount: float, slippage_bps: int):
        """Log swap attempt details.
        
        Args:
            input_token: Source token symbol
            output_token: Destination token symbol
            amount: Amount to swap
            slippage_bps: Slippage tolerance in basis points
        """
        logger.info("🚀 INITIATING SWAP")
        logger.info(f"📊 Pair: {input_token}/{output_token}")
        logger.info(f"💵 Amount: {amount} {input_token}")
        logger.info(f"🎯 Slippage: {slippage_bps/100:.2f}%")
        logger.info(f"👤 Wallet: {str(self.wallet.public_key)[:8]}...")
        logger.info("-"*40) 