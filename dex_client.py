import requests
import json
import time
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from solana.rpc.api import Client
from solana.transaction import Transaction
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
        
    def get_quote(self, input_mint: str, output_mint: str, amount: float, slippage: float = 0.5) -> Optional[DEXPrice]:
        """Get a price quote for a swap."""
        try:
            url = f"{self.base_url}/quote"
            params = {
                "inputMint": input_mint,
                "outputMint": output_mint,
                "amount": str(int(amount)),
                "slippageBps": int(slippage * 100),
                "feeBps": 4
            }
            
            response = self.session.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            
            return DEXPrice(
                input_mint=input_mint,
                output_mint=output_mint,
                input_amount=float(data['inputAmount']) / (10 ** data['inputDecimals']),
                output_amount=float(data['outputAmount']) / (10 ** data['outputDecimals']),
                price=float(data['outputAmount']) / float(data['inputAmount']),
                fee=float(data.get('otherAmountThreshold', 0)),
                route=data.get('routePlan', [])
            )
            
        except Exception as e:
            logger.error(f"Failed to get Jupiter quote: {e}")
            return None
    
    def get_swap_transaction(self, quote: DEXPrice) -> Optional[Transaction]:
        """Get swap transaction from quote."""
        try:
            url = f"{self.base_url}/swap"
            
            payload = {
                "quoteResponse": quote,
                "userPublicKey": str(self.wallet.public_key),
                "wrapUnwrapSOL": True
            }
            
            response = self.session.post(url, json=payload)
            response.raise_for_status()
            data = response.json()
            
            # Deserialize transaction
            transaction_data = data['swapTransaction']
            transaction = Transaction.deserialize(bytes(transaction_data))
            
            return transaction
            
        except Exception as e:
            logger.error(f"Failed to get swap transaction: {e}")
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
            
            # Try Jupiter first (aggregator)
            quote = self.jupiter.get_quote(input_mint, output_mint, amount)
            if quote:
                logger.info(f"Jupiter quote: {quote.price:.6f}")
                return quote
            
            # Fallback to direct DEX queries
            logger.warning("Jupiter quote failed, trying direct DEX queries")
            return None
            
        except Exception as e:
            logger.error(f"Failed to get best price: {e}")
            return None
    
    def execute_swap(self, quote: DEXPrice) -> Optional[str]:
        """Execute a swap using the best available route."""
        try:
            # Get swap transaction from Jupiter
            transaction = self.jupiter.get_swap_transaction(quote)
            if not transaction:
                logger.error("Failed to get swap transaction")
                return None
            
            # Send transaction
            signature = self.wallet.send_transaction(transaction)
            logger.info(f"Swap executed: {signature}")
            return signature
            
        except Exception as e:
            logger.error(f"Failed to execute swap: {e}")
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