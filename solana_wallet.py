import os
import base58
import json
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from solana.rpc.api import Client
from solders.transaction import Transaction
from solders.keypair import Keypair
from solders.pubkey import Pubkey as PublicKey
from solana.rpc.commitment import Commitment
import logging
from hardware_wallet import HardwareWalletManager

logger = logging.getLogger(__name__)

@dataclass
class TokenBalance:
    """Represents a token balance."""
    mint: str
    symbol: str
    balance: float
    decimals: int

class SolanaWallet:
    """Manages Solana wallet operations for DEX trading."""
    
    def __init__(self, private_key: str = None, rpc_url: str = "https://api.mainnet-beta.solana.com", 
                 wallet_type: str = "software", derivation_path: str = "44'/501'/0'/0'"):
        """
        Initialize wallet with either private key (software) or hardware wallet.
        
        Args:
            private_key: Private key for software wallet (optional if using hardware)
            rpc_url: Solana RPC endpoint
            wallet_type: 'software', 'ledger', or 'trezor'
            derivation_path: BIP44 derivation path for hardware wallets
        """
        self.rpc_client = Client(rpc_url, commitment=Commitment("confirmed"))
        self.wallet_type = wallet_type.lower()
        self.hardware_wallet = None
        self.keypair = None
        self.public_key = None
        
        if self.wallet_type == "software":
            if not private_key:
                raise ValueError("Private key required for software wallet")
            self.keypair = self._load_keypair(private_key)
            self.public_key = self.keypair.public_key
        elif self.wallet_type in ["ledger", "trezor"]:
            self.hardware_wallet = HardwareWalletManager(derivation_path, self.wallet_type)
            if not self.hardware_wallet.connect():
                raise RuntimeError(f"Failed to connect to {self.wallet_type} hardware wallet")
            self.public_key = self.hardware_wallet.get_public_key()
            if not self.public_key:
                raise RuntimeError(f"Failed to get public key from {self.wallet_type}")
        else:
            raise ValueError("wallet_type must be 'software', 'ledger', or 'trezor'")
        
        logger.info(f"{self.wallet_type.title()} wallet initialized: {self.public_key}")
    
    def _load_keypair(self, private_key: str) -> Keypair:
        """Load keypair from private key string."""
        try:
            # Try base58 encoded private key
            if len(private_key) == 88:  # Base58 encoded
                private_key_bytes = base58.b58decode(private_key)
            else:
                # Try as JSON array or hex string
                if private_key.startswith('['):
                    private_key_bytes = bytes(json.loads(private_key))
                else:
                    private_key_bytes = bytes.fromhex(private_key)
            
            return Keypair.from_bytes(private_key_bytes)
        except Exception as e:
            logger.error(f"Failed to load private key: {e}")
            raise ValueError("Invalid private key format")
    
    def get_balance(self) -> float:
        """Get SOL balance."""
        try:
            response = self.rpc_client.get_balance(self.public_key)
            if response.value is not None:
                return response.value / 1e9  # Convert lamports to SOL
            return 0.0
        except Exception as e:
            logger.error(f"Failed to get balance: {e}")
            return 0.0
    
    def get_token_balances(self) -> List[TokenBalance]:
        """Get all token balances."""
        try:
            response = self.rpc_client.get_token_accounts_by_owner(
                self.public_key,
                {"programId": PublicKey("TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA")}
            )
            
            balances = []
            for account in response.value:
                account_info = account.account.data
                if account_info:
                    # Parse token account data
                    mint = account_info['parsed']['info']['mint']
                    balance = int(account_info['parsed']['info']['tokenAmount']['uiAmount'])
                    decimals = account_info['parsed']['info']['tokenAmount']['decimals']
                    
                    # Get token symbol (you might want to maintain a mapping)
                    symbol = self._get_token_symbol(mint)
                    
                    if balance > 0:
                        balances.append(TokenBalance(
                            mint=mint,
                            symbol=symbol,
                            balance=balance,
                            decimals=decimals
                        ))
            
            return balances
        except Exception as e:
            logger.error(f"Failed to get token balances: {e}")
            return []
    
    def _get_token_symbol(self, mint: str) -> str:
        """Get token symbol from mint address."""
        # Common Solana tokens
        token_symbols = {
            "So11111111111111111111111111111111111111112": "SOL",
            "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v": "USDC",
            "Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB": "USDT",
            "7vfCXTUXx5WJV5JADk17DUJ4ksgau7utNKj4b963voxs": "ETH",
            "DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB263": "BONK",
            "7dHbWXmci3dT8UFYWYZweBLXgycu7Y3iL6trKn1Y7ARj": "stSOL",
        }
        return token_symbols.get(mint, mint[:8])
    
    def sign_transaction(self, transaction: Transaction) -> Transaction:
        """Sign a transaction with either software or hardware wallet."""
        try:
            if self.wallet_type == "software":
                transaction.sign(self.keypair)
                return transaction
            elif self.wallet_type in ["ledger", "trezor"]:
                if not self.hardware_wallet:
                    raise RuntimeError("Hardware wallet not initialized")
                signed_tx = self.hardware_wallet.sign_transaction(transaction)
                if not signed_tx:
                    raise RuntimeError("Failed to sign transaction with hardware wallet")
                return signed_tx
            else:
                raise ValueError(f"Unsupported wallet type: {self.wallet_type}")
        except Exception as e:
            logger.error(f"Failed to sign transaction: {e}")
            raise
    
    def send_transaction(self, transaction: Transaction) -> str:
        """Send a signed transaction."""
        try:
            # Sign the transaction
            signed_tx = self.sign_transaction(transaction)
            
            # Send the transaction (hardware wallets don't need keypair parameter)
            if self.wallet_type == "software":
                response = self.rpc_client.send_transaction(
                    signed_tx,
                    self.keypair,
                    opts={"skip_confirmation": False, "preflight_commitment": "confirmed"}
                )
            else:
                # For hardware wallets, transaction is already signed
                response = self.rpc_client.send_raw_transaction(
                    signed_tx.serialize(),
                    opts={"skip_confirmation": False, "preflight_commitment": "confirmed"}
                )
            
            if response.value:
                logger.info(f"Transaction sent: {response.value}")
                return response.value
            else:
                raise Exception("Failed to send transaction")
                
        except Exception as e:
            logger.error(f"Failed to send transaction: {e}")
            raise
    
    def get_recent_transactions(self, limit: int = 10) -> List[Dict]:
        """Get recent transactions."""
        try:
            response = self.rpc_client.get_signatures_for_address(
                self.public_key,
                limit=limit
            )
            
            transactions = []
            for sig_info in response.value:
                tx_response = self.rpc_client.get_transaction(
                    sig_info.signature,
                    commitment=Commitment("confirmed")
                )
                if tx_response.value:
                    transactions.append({
                        'signature': sig_info.signature,
                        'slot': sig_info.slot,
                        'block_time': sig_info.block_time,
                        'status': 'confirmed' if sig_info.confirmation_status == 'finalized' else 'pending'
                    })
            
            return transactions
        except Exception as e:
            logger.error(f"Failed to get recent transactions: {e}")
            return []
    
    def estimate_transaction_fee(self, transaction: Transaction) -> int:
        """Estimate transaction fee."""
        try:
            response = self.rpc_client.get_fee_for_message(
                transaction.compile_message(),
                commitment=Commitment("confirmed")
            )
            return response.value if response.value else 5000  # Default fee
        except Exception as e:
            logger.error(f"Failed to estimate fee: {e}")
            return 5000  # Default fee
    
    def get_account_info(self) -> Dict:
        """Get account information."""
        try:
            response = self.rpc_client.get_account_info(self.public_key)
            if response.value:
                return {
                    'lamports': response.value.lamports,
                    'owner': str(response.value.owner),
                    'executable': response.value.executable,
                    'rent_epoch': response.value.rent_epoch
                }
            return {}
        except Exception as e:
            logger.error(f"Failed to get account info: {e}")
            return {}
    
    def get_wallet_info(self) -> Dict:
        """Get wallet information including type and connection status."""
        info = {
            'wallet_type': self.wallet_type,
            'public_key': str(self.public_key),
            'connected': True
        }
        
        if self.hardware_wallet:
            hw_info = self.hardware_wallet.get_device_info()
            info.update(hw_info)
        
        return info
    
    def disconnect(self):
        """Disconnect from wallet (important for hardware wallets)."""
        try:
            if self.hardware_wallet:
                self.hardware_wallet.disconnect()
            logger.info(f"{self.wallet_type.title()} wallet disconnected")
        except Exception as e:
            logger.error(f"Error disconnecting wallet: {e}")
    
    def __del__(self):
        """Cleanup when wallet object is destroyed."""
        try:
            self.disconnect()
        except:
            pass 