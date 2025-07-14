import requests
import time
import json
from typing import Dict, List, Optional, Any
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import logging

from security import SecurityManager
from config import Config

logger = logging.getLogger(__name__)

class APIClient:
    """Handles all API interactions with the trading platform."""
    
    def __init__(self, config: Config, security_manager: SecurityManager):
        self.config = config
        self.security_manager = security_manager
        self.session = self._create_session()
        self.last_request_time = 0
        self.rate_limit_delay = 0.1  # 100ms between requests
    
    def _create_session(self) -> requests.Session:
        """Create a requests session with retry logic."""
        session = requests.Session()
        
        # Configure retry strategy
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        
        return session
    
    def _rate_limit(self):
        """Implement rate limiting to avoid API restrictions."""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        
        if time_since_last < self.rate_limit_delay:
            sleep_time = self.rate_limit_delay - time_since_last
            time.sleep(sleep_time)
        
        self.last_request_time = time.time()
    
    def _make_request(self, method: str, endpoint: str, params: Dict = None, 
                     data: Dict = None, requires_auth: bool = True) -> Dict:
        """Make an authenticated API request with error handling."""
        self._rate_limit()
        
        url = f"{self.config.BASE_URL}{endpoint}"
        headers = {}
        
        if requires_auth:
            headers = self.security_manager.create_secure_headers(
                self.config.API_KEY,
                self.config.API_SECRET,
                endpoint,
                params or {}
            )
        else:
            headers = {"Content-Type": "application/json"}
        
        try:
            if method.upper() == "GET":
                response = self.session.get(url, params=params, headers=headers, timeout=30)
            elif method.upper() == "POST":
                response = self.session.post(url, json=data, headers=headers, timeout=30)
            elif method.upper() == "DELETE":
                response = self.session.delete(url, params=params, headers=headers, timeout=30)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")
            
            response.raise_for_status()
            response_data = response.json()
            
            # Validate response for security
            if not self.security_manager.validate_api_response(response_data):
                logger.warning("API response validation failed")
            
            return response_data
            
        except requests.exceptions.RequestException as e:
            logger.error(f"API request failed: {e}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"Response status: {e.response.status_code}")
                logger.error(f"Response content: {e.response.text}")
            raise
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error in API request: {e}")
            raise
    
    def get_market_price(self, trading_pair: str) -> float:
        """Fetch current market price for the trading pair."""
        try:
            endpoint = f"/v1/market/{trading_pair}"
            response = self._make_request("GET", endpoint, requires_auth=False)
            
            if 'price' not in response:
                raise ValueError("Price not found in market data response")
            
            price = float(response['price'])
            logger.info(f"Current {trading_pair} price: {price:.6f}")
            return price
            
        except Exception as e:
            logger.error(f"Failed to fetch market price for {trading_pair}: {e}")
            raise
    
    def get_account_balance(self) -> Dict[str, float]:
        """Fetch account balances."""
        try:
            endpoint = "/v1/account/balance"
            response = self._make_request("GET", endpoint)
            
            balances = {}
            if 'balances' in response:
                for balance in response['balances']:
                    currency = balance.get('currency', '')
                    amount = float(balance.get('available', 0))
                    balances[currency] = amount
            
            logger.info(f"Account balances: {balances}")
            return balances
            
        except Exception as e:
            logger.error(f"Failed to fetch account balance: {e}")
            raise
    
    def place_order(self, trading_pair: str, side: str, order_type: str, 
                   quantity: float, price: float = None) -> Dict:
        """Place a new order."""
        try:
            endpoint = "/v1/orders"
            data = {
                "pair": trading_pair,
                "side": side,
                "type": order_type,
                "quantity": quantity
            }
            
            if price:
                data["price"] = price
            
            response = self._make_request("POST", endpoint, data=data)
            
            order_id = response.get('id', '')
            logger.info(f"Placed {side} order: {order_id} for {quantity} {trading_pair} at {price}")
            
            return response
            
        except Exception as e:
            logger.error(f"Failed to place {side} order: {e}")
            raise
    
    def get_open_orders(self, trading_pair: str = None) -> List[Dict]:
        """Fetch open orders."""
        try:
            endpoint = "/v1/orders/open"
            params = {}
            if trading_pair:
                params["pair"] = trading_pair
            
            response = self._make_request("GET", endpoint, params=params)
            
            orders = response.get('orders', [])
            logger.info(f"Found {len(orders)} open orders")
            return orders
            
        except Exception as e:
            logger.error(f"Failed to fetch open orders: {e}")
            raise
    
    def cancel_order(self, order_id: str) -> bool:
        """Cancel an open order."""
        try:
            endpoint = f"/v1/orders/{order_id}"
            response = self._make_request("DELETE", endpoint)
            
            logger.info(f"Cancelled order: {order_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to cancel order {order_id}: {e}")
            return False
    
    def get_order_status(self, order_id: str) -> Dict:
        """Get status of a specific order."""
        try:
            endpoint = f"/v1/orders/{order_id}"
            response = self._make_request("GET", endpoint)
            
            return response
            
        except Exception as e:
            logger.error(f"Failed to get order status for {order_id}: {e}")
            raise
    
    def get_trade_history(self, trading_pair: str = None, limit: int = 100) -> List[Dict]:
        """Fetch trade history."""
        try:
            endpoint = "/v1/trades"
            params = {"limit": limit}
            if trading_pair:
                params["pair"] = trading_pair
            
            response = self._make_request("GET", endpoint, params=params)
            
            trades = response.get('trades', [])
            logger.info(f"Retrieved {len(trades)} trades")
            return trades
            
        except Exception as e:
            logger.error(f"Failed to fetch trade history: {e}")
            raise
    
    def get_market_depth(self, trading_pair: str, limit: int = 100) -> Dict:
        """
        Fetch market depth (order book) for volume-weighted grid analysis.
        
        Args:
            trading_pair: Trading pair symbol (e.g., 'SOL/USDC')
            limit: Maximum number of orders per side (default 100 for P3 analysis)
            
        Returns:
            Dict containing bids, asks, and metadata for market analysis
        """
        try:
            # Try multiple endpoints for different exchange types
            endpoints_to_try = [
                f"/v1/market/{trading_pair}/depth",  # Primary CEX endpoint
                f"/v1/orderbook/{trading_pair}",     # Alternative CEX endpoint
                f"/dex/orderbook/{trading_pair}",    # DEX endpoint (Jupiter/Raydium)
            ]
            
            params = {"limit": limit}
            last_error = None
            
            for endpoint in endpoints_to_try:
                try:
                    logger.debug(f"Attempting market depth fetch from endpoint: {endpoint}")
                    response = self._make_request("GET", endpoint, params=params, requires_auth=False)
                    
                    # Validate response structure for market analysis
                    if self._validate_market_depth_response(response):
                        logger.debug(f"Successfully fetched market depth from {endpoint}")
                        return response
                    else:
                        logger.warning(f"Invalid market depth response structure from {endpoint}")
                        continue
                        
                except Exception as e:
                    last_error = e
                    logger.debug(f"Endpoint {endpoint} failed: {e}")
                    continue
            
            # If all endpoints failed, try fallback data sources
            logger.warning("Primary market depth sources failed, attempting fallback")
            return self._get_fallback_market_depth(trading_pair, limit)
            
        except Exception as e:
            logger.error(f"Failed to fetch market depth for {trading_pair}: {e}")
            # Return empty structure for graceful degradation
            return {
                'bids': [],
                'asks': [],
                'timestamp': time.time(),
                'symbol': trading_pair,
                'source': 'fallback_empty'
            }
    
    def _validate_market_depth_response(self, response: Dict) -> bool:
        """Validate market depth response structure."""
        required_fields = ['bids', 'asks']
        
        if not all(field in response for field in required_fields):
            return False
            
        # Check that bids and asks are lists with valid structure
        bids = response.get('bids', [])
        asks = response.get('asks', [])
        
        if not isinstance(bids, list) or not isinstance(asks, list):
            return False
            
        # Validate sample entries have price and volume
        for orders in [bids[:3], asks[:3]]:  # Check first 3 entries
            for order in orders:
                if not isinstance(order, list) or len(order) < 2:
                    return False
                try:
                    float(order[0])  # price
                    float(order[1])  # volume
                except (ValueError, TypeError):
                    return False
                    
        return True
        
    def _get_fallback_market_depth(self, trading_pair: str, limit: int) -> Dict:
        """
        Get fallback market depth data when primary sources fail.
        
        This could include:
        - Cached historical data
        - Simplified order book from ticker data
        - Mock data for testing (if in test mode)
        """
        try:
            # Try to get current price and build minimal order book
            current_price = self.get_market_price(trading_pair)
            
            # Create minimal order book with small spreads
            spread_percent = 0.001  # 0.1% spread
            spread = current_price * spread_percent
            
            # Generate simple order book structure
            bids = []
            asks = []
            
            # Create 5 levels on each side with decreasing volume
            base_volume = 100.0  # Base volume amount
            
            for i in range(min(5, limit)):
                # Bid side (buy orders below current price)
                bid_price = current_price - spread * (i + 1)
                bid_volume = base_volume * (1.0 - i * 0.1)  # Decreasing volume
                bids.append([bid_price, bid_volume])
                
                # Ask side (sell orders above current price)
                ask_price = current_price + spread * (i + 1)
                ask_volume = base_volume * (1.0 - i * 0.1)  # Decreasing volume
                asks.append([ask_price, ask_volume])
            
            return {
                'bids': bids,
                'asks': asks,
                'timestamp': time.time(),
                'symbol': trading_pair,
                'source': 'fallback_generated'
            }
            
        except Exception as e:
            logger.error(f"Fallback market depth generation failed: {e}")
            # Return minimal empty structure
            return {
                'bids': [],
                'asks': [],
                'timestamp': time.time(),
                'symbol': trading_pair,
                'source': 'fallback_empty'
            }
    
    def get_24h_ticker(self, trading_pair: str) -> Dict:
        """Fetch 24-hour ticker information."""
        try:
            endpoint = f"/v1/market/{trading_pair}/ticker"
            response = self._make_request("GET", endpoint, requires_auth=False)
            
            return response
            
        except Exception as e:
            logger.error(f"Failed to fetch 24h ticker for {trading_pair}: {e}")
            raise
    
    def test_connection(self) -> bool:
        """Test API connection and authentication."""
        try:
            # Try to fetch account balance as a connection test
            self.get_account_balance()
            logger.info("API connection test successful")
            return True
            
        except Exception as e:
            logger.error(f"API connection test failed: {e}")
            return False 