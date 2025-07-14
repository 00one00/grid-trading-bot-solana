"""
Hardware Wallet Manager for Solana Grid Trading Bot
Provides secure hardware wallet integration for Ledger devices.
"""

import logging
from typing import Optional, Dict, Any
from solders.pubkey import Pubkey as PublicKey
from solders.transaction import Transaction
from solders.keypair import Keypair
import time

logger = logging.getLogger(__name__)

class HardwareWalletManager:
    """Manages hardware wallet operations for secure trading."""
    
    def __init__(self, derivation_path: str = "44'/501'/0'/0'", device_type: str = "ledger"):
        """
        Initialize hardware wallet manager.
        
        Args:
            derivation_path: BIP44 derivation path for Solana
            device_type: Type of hardware wallet ('ledger' or 'trezor')
        """
        self.derivation_path = derivation_path
        self.device_type = device_type.lower()
        self.client = None
        self.public_key = None
        self.connected = False
        
        logger.info(f"Initializing {device_type} hardware wallet with path: {derivation_path}")
        
    def connect(self) -> bool:
        """
        Connect to hardware wallet device.
        
        Returns:
            bool: True if connection successful, False otherwise
        """
        try:
            if self.device_type == "ledger":
                return self._connect_ledger()
            elif self.device_type == "trezor":
                return self._connect_trezor()
            else:
                logger.error(f"Unsupported device type: {self.device_type}")
                return False
        except Exception as e:
            logger.error(f"Failed to connect to hardware wallet: {e}")
            return False
    
    def _connect_ledger(self) -> bool:
        """Connect to Ledger device."""
        try:
            from ledgerblue.comm import getDongle
            from ledgerblue.commException import CommException
            
            # Try to connect to Ledger
            self.client = getDongle(debug=False)
            
            # Get public key to verify connection
            self.public_key = self._get_ledger_public_key()
            if self.public_key:
                self.connected = True
                logger.info(f"Connected to Ledger. Public key: {self.public_key}")
                return True
            
            return False
            
        except ImportError:
            logger.error("Ledger dependencies not installed. Run: pip install ledgerblue")
            return False
        except Exception as e:
            logger.error(f"Failed to connect to Ledger: {e}")
            return False
    
    def _connect_trezor(self) -> bool:
        """Connect to Trezor device (placeholder for future implementation)."""
        logger.warning("Trezor support not yet implemented")
        return False
    
    def _get_ledger_public_key(self) -> Optional[PublicKey]:
        """Get public key from Ledger device."""
        try:
            # Solana app APDU command to get public key
            # CLA=0xE0, INS=0x01 (GET_PUBLIC_KEY), P1=0x00, P2=0x00
            apdu = bytearray([0xE0, 0x01, 0x00, 0x00])
            
            # Add derivation path length and path
            path_bytes = self._encode_derivation_path()
            apdu.append(len(path_bytes))
            apdu.extend(path_bytes)
            
            response = self.client.exchange(bytes(apdu))
            
            # Parse response (first 32 bytes are the public key)
            if len(response) >= 32:
                public_key_bytes = response[:32]
                return PublicKey(public_key_bytes)
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to get public key from Ledger: {e}")
            return None
    
    def _encode_derivation_path(self) -> bytes:
        """Encode derivation path for Ledger communication."""
        try:
            # Parse derivation path like "44'/501'/0'/0'"
            path_parts = self.derivation_path.replace("'", "").split("/")
            path_ints = []
            
            for part in path_parts:
                if part.isdigit():
                    # Add hardened bit (0x80000000) for hardened derivation
                    if "'" in self.derivation_path.split("/")[len(path_ints)]:
                        path_ints.append(int(part) | 0x80000000)
                    else:
                        path_ints.append(int(part))
            
            # Encode as bytes (4 bytes per path element, big endian)
            encoded = bytearray()
            encoded.append(len(path_ints))  # Number of path elements
            
            for path_int in path_ints:
                encoded.extend(path_int.to_bytes(4, 'big'))
            
            return bytes(encoded)
            
        except Exception as e:
            logger.error(f"Failed to encode derivation path: {e}")
            return b""
    
    def get_public_key(self) -> Optional[PublicKey]:
        """
        Get public key from hardware wallet.
        
        Returns:
            PublicKey: The wallet's public key or None if failed
        """
        if not self.connected:
            if not self.connect():
                return None
        
        return self.public_key
    
    def sign_transaction(self, transaction: Transaction) -> Optional[Transaction]:
        """
        Sign transaction with hardware wallet.
        
        Args:
            transaction: Transaction to sign
            
        Returns:
            Transaction: Signed transaction or None if failed
        """
        if not self.connected:
            if not self.connect():
                logger.error("Cannot sign transaction: hardware wallet not connected")
                return None
        
        try:
            if self.device_type == "ledger":
                return self._sign_with_ledger(transaction)
            elif self.device_type == "trezor":
                return self._sign_with_trezor(transaction)
            else:
                logger.error(f"Unsupported device type for signing: {self.device_type}")
                return None
                
        except Exception as e:
            logger.error(f"Failed to sign transaction with hardware wallet: {e}")
            return None
    
    def _sign_with_ledger(self, transaction: Transaction) -> Optional[Transaction]:
        """Sign transaction with Ledger device."""
        try:
            # Serialize transaction for signing
            message = transaction.compile_message()
            message_bytes = message.serialize()
            
            # Solana app APDU command to sign transaction
            # CLA=0xE0, INS=0x02 (SIGN_TRANSACTION), P1=0x00, P2=0x00
            apdu = bytearray([0xE0, 0x02, 0x00, 0x00])
            
            # Add derivation path
            path_bytes = self._encode_derivation_path()
            apdu.append(len(path_bytes))
            apdu.extend(path_bytes)
            
            # Add message length and data
            apdu.extend(len(message_bytes).to_bytes(2, 'big'))
            apdu.extend(message_bytes)
            
            # Request user confirmation on device
            logger.info("Please confirm transaction on your Ledger device...")
            
            response = self.client.exchange(bytes(apdu))
            
            # Parse signature from response
            if len(response) >= 64:
                signature = response[:64]
                
                # Add signature to transaction
                transaction.add_signature(self.public_key, signature)
                
                logger.info("Transaction signed successfully with Ledger")
                return transaction
            
            logger.error("Invalid signature response from Ledger")
            return None
            
        except Exception as e:
            logger.error(f"Failed to sign with Ledger: {e}")
            return None
    
    def _sign_with_trezor(self, transaction: Transaction) -> Optional[Transaction]:
        """Sign transaction with Trezor device (placeholder)."""
        logger.warning("Trezor signing not yet implemented")
        return None
    
    def disconnect(self):
        """Disconnect from hardware wallet."""
        try:
            if self.client:
                if self.device_type == "ledger":
                    self.client.close()
                
            self.client = None
            self.connected = False
            self.public_key = None
            
            logger.info("Disconnected from hardware wallet")
            
        except Exception as e:
            logger.error(f"Error disconnecting from hardware wallet: {e}")
    
    def is_connected(self) -> bool:
        """Check if hardware wallet is connected."""
        return self.connected and self.client is not None
    
    def get_device_info(self) -> Dict[str, Any]:
        """Get hardware wallet device information."""
        if not self.connected:
            return {"connected": False}
        
        return {
            "connected": True,
            "device_type": self.device_type,
            "public_key": str(self.public_key) if self.public_key else None,
            "derivation_path": self.derivation_path
        }

class HardwareWalletError(Exception):
    """Custom exception for hardware wallet operations."""
    pass