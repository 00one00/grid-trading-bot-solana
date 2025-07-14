import hmac
import hashlib
import base64
import time
import hashlib
import os
import socket
import requests
from typing import Dict, Optional, List
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import logging

logger = logging.getLogger(__name__)

class SecurityManager:
    """Handles security operations for the trading bot."""
    
    def __init__(self, encryption_key: str = None):
        self.encryption_key = encryption_key or os.getenv('ENCRYPTION_KEY', '')
        self.fernet = None
        if self.encryption_key:
            self._setup_encryption()
    
    def _setup_encryption(self):
        """Setup encryption with dynamic salt generation."""
        try:
            # Generate or load salt
            salt_file = 'security_salt.dat'
            if os.path.exists(salt_file):
                with open(salt_file, 'rb') as f:
                    salt = f.read()
                logger.debug("Loaded existing encryption salt")
            else:
                # Generate new random salt
                salt = os.urandom(32)
                with open(salt_file, 'wb') as f:
                    f.write(salt)
                os.chmod(salt_file, 0o600)  # Restrict permissions to owner only
                logger.info("Generated new encryption salt with secure permissions")
            
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=salt,
                iterations=100000,
            )
            key = base64.urlsafe_b64encode(kdf.derive(self.encryption_key.encode()))
            self.fernet = Fernet(key)
            logger.debug("Encryption setup completed successfully")
            
        except Exception as e:
            logger.warning(f"Failed to setup encryption: {e}")
            self.fernet = None
    
    def encrypt_data(self, data: str) -> str:
        """Encrypt sensitive data."""
        if not self.fernet:
            logger.error("Encryption not available - cannot proceed with sensitive data")
            raise ValueError("Encryption required but not available")
        try:
            return self.fernet.encrypt(data.encode()).decode()
        except Exception as e:
            logger.error(f"Encryption failed: {e}")
            raise ValueError("Failed to encrypt sensitive data")
    
    def decrypt_data(self, encrypted_data: str) -> str:
        """Decrypt sensitive data."""
        if not self.fernet:
            logger.error("Decryption not available")
            raise ValueError("Decryption required but not available")
        try:
            return self.fernet.decrypt(encrypted_data.encode()).decode()
        except Exception as e:
            logger.error(f"Decryption failed: {e}")
            raise ValueError("Failed to decrypt data")
    
    def validate_ip(self, allowed_ips: Optional[List[str]]) -> bool:
        """Validate if current external IP is in whitelist with enhanced security."""
        if not allowed_ips:
            logger.info("IP whitelist empty - bypassing validation")
            return True
        
        try:
            # Multiple IP detection services for reliability and security
            ip_services = [
                'https://api.ipify.org',
                'https://ipinfo.io/ip', 
                'https://icanhazip.com',
                'https://checkip.amazonaws.com'
            ]
            
            current_ip = None
            service_used = None
            
            # Try each service with timeout protection
            for service in ip_services:
                try:
                    logger.debug(f"Attempting IP detection via: {service}")
                    response = requests.get(
                        service, 
                        timeout=5,
                        headers={'User-Agent': 'TradingBot/1.0'}
                    )
                    
                    if response.status_code == 200:
                        detected_ip = response.text.strip()
                        
                        # Basic IP format validation
                        if self._is_valid_ip_format(detected_ip):
                            current_ip = detected_ip
                            service_used = service
                            logger.debug(f"IP detected successfully via {service}: {current_ip}")
                            break
                        else:
                            logger.warning(f"Invalid IP format from {service}: {detected_ip}")
                            
                except requests.exceptions.Timeout:
                    logger.warning(f"Timeout connecting to IP service: {service}")
                    continue
                except requests.exceptions.RequestException as e:
                    logger.warning(f"Failed to connect to IP service {service}: {e}")
                    continue
                except Exception as e:
                    logger.warning(f"Unexpected error with IP service {service}: {e}")
                    continue
            
            # Fail secure if no IP could be determined
            if not current_ip:
                logger.error("Could not determine external IP from any service - failing secure")
                return False
                
            # Validate against whitelist
            is_allowed = current_ip in allowed_ips
            
            # Security audit logging
            if is_allowed:
                logger.info(f"IP validation PASSED: {current_ip} (via {service_used})")
            else:
                logger.warning(f"IP validation FAILED: {current_ip} not in whitelist (via {service_used})")
                
            return is_allowed
            
        except Exception as e:
            logger.error(f"IP validation system error: {e}")
            return False  # Fail secure on any unexpected error
    
    def _is_valid_ip_format(self, ip_string: str) -> bool:
        """Validate IP address format for security."""
        import re
        
        # IPv4 pattern validation
        ipv4_pattern = re.compile(
            r'^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}'
            r'(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$'
        )
        
        # IPv6 basic pattern validation  
        ipv6_pattern = re.compile(
            r'^(?:[0-9a-fA-F]{1,4}:){7}[0-9a-fA-F]{1,4}$|'
            r'^::1$|^::$'
        )
        
        if not ip_string or len(ip_string) > 45:  # Max IPv6 length
            return False
            
        return bool(ipv4_pattern.match(ip_string) or ipv6_pattern.match(ip_string))
    
    def generate_signature(self, api_secret: str, timestamp: str, endpoint: str, params: Dict) -> str:
        """Generate HMAC-SHA256 signature for API authentication."""
        try:
            # Create query string from sorted parameters
            query_string = "&".join([f"{k}={v}" for k, v in sorted(params.items())])
            message = f"{timestamp}{endpoint}{query_string}".encode('utf-8')
            
            # Generate signature
            signature = hmac.new(
                api_secret.encode('utf-8'),
                message,
                hashlib.sha256
            ).hexdigest()
            
            return signature
        except Exception as e:
            logger.error(f"Signature generation failed: {e}")
            raise
    
    def create_secure_headers(self, api_key: str, api_secret: str, endpoint: str, params: Dict) -> Dict[str, str]:
        """Create secure headers for API requests."""
        timestamp = str(int(time.time() * 1000))
        signature = self.generate_signature(api_secret, timestamp, endpoint, params)
        
        return {
            "API-Key": api_key,
            "Timestamp": timestamp,
            "Signature": signature,
            "Content-Type": "application/json",
            "User-Agent": "SolanaGridBot/1.0"
        }
    
    def validate_api_response(self, response_data: Dict) -> bool:
        """Validate API response for security issues."""
        # Check for common security issues in responses
        suspicious_fields = ['password', 'secret', 'private_key', 'token']
        
        def check_dict(data, path=""):
            if isinstance(data, dict):
                for key, value in data.items():
                    current_path = f"{path}.{key}" if path else key
                    if key.lower() in suspicious_fields:
                        logger.warning(f"Suspicious field detected: {current_path}")
                        return False
                    if not check_dict(value, current_path):
                        return False
            elif isinstance(data, list):
                for i, item in enumerate(data):
                    current_path = f"{path}[{i}]"
                    if not check_dict(item, current_path):
                        return False
            return True
        
        return check_dict(response_data)
    
    def sanitize_log_data(self, data: Dict) -> Dict:
        """Remove sensitive information from data before logging."""
        sensitive_fields = ['api_key', 'api_secret', 'signature', 'password', 'token']
        sanitized = data.copy()
        
        for field in sensitive_fields:
            if field in sanitized:
                sanitized[field] = '***REDACTED***'
        
        return sanitized 