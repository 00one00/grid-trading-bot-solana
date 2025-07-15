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
            self.public_key = self.keypair.pubkey()
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
            if len(private_key) == 44:  # Base58 encoded
                private_key_bytes = base58.b58decode(private_key)
            else:
                # Try as JSON array or hex string
                if private_key.startswith('['):
                    private_key_bytes = bytes(json.loads(private_key))
                else:
                    private_key_bytes = bytes.fromhex(private_key)
            
            return Keypair.from_seed(private_key_bytes)
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
    
    def get_public_key(self) -> str:
        """Get public key as string."""
        return str(self.public_key)
    
    
    def get_token_balances(self) -> List[TokenBalance]:
        """Get all token balances."""
        try:
            from solders.pubkey import Pubkey
            token_program_id = Pubkey.from_string("TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA")
            
            response = self.rpc_client.get_token_accounts_by_owner(
                self.public_key,
                {"programId": token_program_id}
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
    
    def sign_transaction(self, transaction) -> any:
        """Sign a transaction with either software or hardware wallet.
        
        For software wallets, this method handles both VersionedTransaction and legacy Transaction
        with proper fresh blockhash handling.
        """
        try:
            if self.wallet_type == "software":
                from solders.transaction import VersionedTransaction
                
                if isinstance(transaction, VersionedTransaction):
                    # For VersionedTransaction, sign the message directly
                    # The transaction should already have a fresh blockhash in its message
                    message_bytes = bytes(transaction.message)
                    signature = self.keypair.sign_message(message_bytes)
                    
                    # Create new VersionedTransaction with signature
                    transaction.signatures = [signature]
                    logger.debug(f"✅ Signed VersionedTransaction with signature: {signature}")
                    return transaction
                else:
                    # For legacy Transaction, it should already have the correct blockhash
                    # Just sign with the keypair
                    transaction.sign([self.keypair])
                    logger.debug(f"✅ Signed legacy Transaction")
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
    
    def sign_transaction_with_fresh_blockhash(self, transaction) -> any:
        """Sign a transaction with a fresh blockhash (for legacy support).
        
        This method gets a fresh blockhash and signs the transaction with it.
        Used as fallback when the transaction's blockhash is stale.
        """
        try:
            if self.wallet_type == "software":
                from solders.transaction import VersionedTransaction
                from solders.message import MessageV0, Message
                from solders.transaction import Transaction
                from solders.instruction import Instruction
                from solders.hash import Hash
                
                # Always get fresh blockhash
                recent_blockhash_response = self.rpc_client.get_latest_blockhash()
                fresh_blockhash = recent_blockhash_response.value.blockhash
                
                logger.debug(f"🔄 Using fresh blockhash: {str(fresh_blockhash)[:8]}...")
                
                if isinstance(transaction, VersionedTransaction):
                    # For VersionedTransaction with fresh blockhash already set, just sign
                    if hasattr(transaction.message, 'recent_blockhash') and transaction.message.recent_blockhash == fresh_blockhash:
                        message_bytes = bytes(transaction.message)
                        signature = self.keypair.sign_message(message_bytes)
                        transaction.signatures = [signature]
                        return transaction
                    else:
                        # Need to create new message with fresh blockhash
                        message = transaction.message
                        if isinstance(message, MessageV0):
                            # For V0 message, use try_compile to create new one with fresh blockhash
                            # Extract payer (first account key)
                            payer = message.account_keys[0] if message.account_keys else self.public_key
                            
                            # Reconstruct with fresh blockhash
                            new_message = MessageV0.try_compile(
                                payer=payer,
                                instructions=message.instructions,
                                address_lookup_table_accounts=message.address_table_lookups,
                                recent_blockhash=fresh_blockhash
                            )
                            new_transaction = VersionedTransaction(new_message, [])
                            message_bytes = bytes(new_transaction.message)
                            signature = self.keypair.sign_message(message_bytes)
                            new_transaction.signatures = [signature]
                            return new_transaction
                        else:
                            # For non-V0 VersionedTransaction, we CANNOT modify the message
                            # This is the critical issue - Jupiter sends non-V0 messages we can't fix
                            logger.error("🚨 CRITICAL: Cannot reconstruct non-V0 VersionedTransaction with fresh blockhash")
                            logger.error("🚨 Jupiter provided incompatible transaction type")
                            logger.error("🚨 This transaction will fail with stale blockhash")
                            
                            # Sign the original (will fail, but at least we know why)
                            message_bytes = bytes(transaction.message)
                            signature = self.keypair.sign_message(message_bytes)
                            transaction.signatures = [signature]
                            return transaction
                else:
                    # For legacy Transaction, create fresh signed copy
                    try:
                        # Create fresh transaction with new blockhash
                        new_transaction = Transaction.new_with_payer(
                            instructions=[Instruction.from_bytes(bytes(inst)) for inst in transaction.message.instructions],
                            payer=transaction.message.account_keys[0]
                        )
                        new_transaction.sign([self.keypair], fresh_blockhash)
                        return new_transaction
                    except Exception as e:
                        # Fallback: modify the existing transaction (if possible)
                        logger.warning(f"🔄 Fresh transaction creation failed, using fallback signing: {e}")
                        transaction.sign([self.keypair], fresh_blockhash)
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
            logger.error(f"Failed to sign transaction with fresh blockhash: {e}")
            raise
    
    def send_transaction(self, signed_transaction) -> str:
        """Send a pre-signed transaction to the network.
        
        Args:
            signed_transaction: Already signed transaction
            
        Returns:
            Transaction signature
        """
        try:
            # Send the transaction via RPC
            response = self.rpc_client.send_transaction(signed_transaction)
            
            if response.value:
                logger.info(f"Transaction sent: {response.value}")
                return response.value
            else:
                raise Exception("Failed to send transaction: no signature returned")
                
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