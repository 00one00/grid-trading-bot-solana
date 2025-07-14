Below is a detailed instruction for an AI code IDE to develop a grid trading bot on Solana for small capital investors from scratch, tailored to platforms like goodcryptoX and TradeSanta. This guide ensures the bot is user-friendly, cost-effective, and optimized for Solana’s low fees and high throughput.

```python
import requests
import time
import hmac
import hashlib
import base64
import logging
from typing import Dict, List, Tuple

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class GridTradingBot:
    def __init__(self, api_key: str, api_secret: str, base_url: str, capital: float, pair: str = "SOL/USDC"):
        """Initialize the grid trading bot with API credentials and trading parameters."""
        self.api_key = api_key
        self.api_secret = api_secret
        self.base_url = base_url  # e.g., "https://api.goodcrypto.app" or TradeSanta's API URL
        self.capital = capital  # Total capital in USD (e.g., $250-$500)
        self.trading_pair = pair
        self.grid_levels = 5  # Number of grid levels (configurable)
        self.price_range_percent = 0.10  # 10% price range around current price
        self.risk_per_trade = 0.02  # 2% of capital per trade
        self.orders: List[Dict] = []  # Store active orders

    def sign_request(self, endpoint: str, params: Dict) -> Dict:
        """Generate authenticated headers for API requests."""
        timestamp = str(int(time.time() * 1000))
        query_string = "&".join([f"{k}={v}" for k, v in sorted(params.items())])
        message = f"{timestamp}{endpoint}{query_string}".encode('utf-8')
        signature = hmac.new(
            self.api_secret.encode('utf-8'), message, hashlib.sha256
        ).hexdigest()
        return {
            "API-Key": self.api_key,
            "Timestamp": timestamp,
            "Signature": signature,
            "Content-Type": "application/json"
        }

    def get_market_price(self) -> float:
        """Fetch the current market price for the trading pair."""
        endpoint = f"/v1/market/{self.trading_pair}"
        try:
            response = requests.get(f"{self.base_url}{endpoint}", headers=self.sign_request(endpoint, {}))
            response.raise_for_status()
            data = response.json()
            return float(data['price'])
        except Exception as e:
            logger.error(f"Failed to fetch market price: {e}")
            raise

    def calculate_grid(self, current_price: float) -> Tuple[List[float], List[float]]:
        """Calculate buy and sell grid levels based on current price."""
        price_step = (current_price * self.price_range_percent) / self.grid_levels
        buy_prices = [current_price - (i * price_step) for i in range(1, self.grid_levels + 1)]
        sell_prices = [current_price + (i * price_step) for i in range(1, self.grid_levels + 1)]
        return buy_prices, sell_prices

    def place_order(self, side: str, price: float, quantity: float) -> Dict:
        """Place a limit order via the platform's API."""
        endpoint = "/v1/orders"
        params = {
            "pair": self.trading_pair,
            "side": side,  # "buy" or "sell"
            "type": "limit",
            "price": price,
            "quantity": quantity
        }
        headers = self.sign_request(endpoint, params)
        try:
            response = requests.post(f"{self.base_url}{endpoint}", json=params, headers=headers)
            response.raise_for_status()
            order = response.json()
            logger.info(f"Placed {side} order at {price} for {quantity} {self.trading_pair}")
            return order
        except Exception as e:
            logger.error(f"Failed to place {side} order: {e}")
            raise

    def manage_positions(self):
        """Monitor and manage open orders and positions."""
        endpoint = "/v1/orders/open"
        headers = self.sign_request(endpoint, {"pair": self.trading_pair})
        try:
            response = requests.get(f"{self.base_url}{endpoint}", headers=headers)
            response.raise_for_status()
            open_orders = response.json()
            for order in open_orders:
                if order['status'] == 'filled':
                    self.handle_filled_order(order)
        except Exception as e:
            logger.error(f"Failed to manage positions: {e}")

    def handle_filled_order(self, order: Dict):
        """Place a corresponding order when one is filled."""
        if order['side'] == 'buy':
            sell_price = order['price'] * (1 + 0.02)  # 2% profit target
            quantity = order['quantity']
            self.place_order("sell", sell_price, quantity)
        elif order['side'] == 'sell':
            buy_price = order['price'] * (1 - 0.02)  # Buy back 2% lower
            quantity = order['quantity']
            self.place_order("buy", buy_price, quantity)

    def run(self):
        """Main execution loop for the grid trading bot."""
        logger.info("Starting grid trading bot...")
        while True:
            try:
                current_price = self.get_market_price()
                buy_prices, sell_prices = self.calculate_grid(current_price)
                trade_size = (self.capital * self.risk_per_trade) / current_price

                # Place initial grid orders if none exist
                if not self.orders:
                    for buy_price in buy_prices:
                        order = self.place_order("buy", buy_price, trade_size)
                        self.orders.append(order)
                    for sell_price in sell_prices:
                        order = self.place_order("sell", sell_price, trade_size)
                        self.orders.append(order)

                # Manage existing positions
                self.manage_positions()

                # Sleep to avoid hitting API rate limits
                time.sleep(60)  # Check every minute
            except Exception as e:
                logger.error(f"Bot encountered an error: {e}")
                time.sleep(300)  # Wait 5 minutes before retrying

if __name__ == "__main__":
    # Example usage (replace with real API credentials and URL)
    bot = GridTradingBot(
        api_key="your_api_key",
        api_secret="your_api_secret",
        base_url="https://api.example.com",  # Replace with goodcryptoX or TradeSanta API URL
        capital=250.0  # $250 starting capital
    )
    bot.run()
```

### Instructions for AI Code IDE

#### Step 1: Setup and Authentication
- Use Python as the programming language due to its simplicity and robust library support.
- Install required libraries: `requests` for API calls, and set up basic logging with `logging`.
- Implement secure API authentication using HMAC-SHA256 signatures, which is common for trading platforms.

#### Step 2: Market Data Retrieval
- Create a function to fetch real-time price data for the SOL/USDC trading pair using the platform’s API.
- Handle errors gracefully and log them for debugging.

#### Step 3: Grid Calculation
- Calculate grid levels based on the current price, a 10% price range, and 5 levels on each side (buy and sell).
- Ensure calculations are dynamic and adaptable to user inputs in the future.

#### Step 4: Order Placement
- Implement a function to place limit orders at calculated grid levels.
- Use small position sizes (2% of capital per trade) to manage risk for small capital investors ($250-$500).

#### Step 5: Position Management
- Monitor open orders and positions via the API.
- When an order is filled, place a corresponding opposite order (e.g., sell after a buy) to lock in profits.

#### Step 6: Risk Management
- Limit each trade to 1-2% of total capital to minimize losses.
- Include basic stop-loss logic by adjusting grid levels or closing positions if losses exceed a threshold (e.g., 5%).

#### Step 7: Error Handling and Logging
- Implement robust error handling for API failures, network issues, or market anomalies.
- Log all actions (trades, errors) to track performance and debug issues.

#### Step 8: Main Execution Loop
- Run the bot in a continuous loop, checking prices and managing orders every minute.
- Include a delay to respect API rate limits and a retry mechanism for errors.

#### Key Considerations
- **Solana Optimization**: Leverage Solana’s low fees ($0.00025 per transaction) and high throughput for frequent trades.
- **Security**: Securely store API keys (avoid hardcoding in production) and use IP whitelisting if supported by the platform.
- **Regulatory Compliance**: Log trades and ensure the bot can provide records for KYC/AML compliance if required.
- **From Scratch**: The core logic (grid calculation, order placement, position management) is custom-coded, using only standard libraries like `requests`.

#### Deployment
- Test the bot in a simulated environment (e.g., platform testnet) before deploying with real capital.
- Start with $100-$200 to validate performance, then scale to $250-$500 as confidence grows.
- Monitor logs and adjust parameters (e.g., grid levels, price range) based on market conditions.

This instruction provides a complete roadmap for the AI code IDE to build a functional grid trading bot tailored for small capital investors on Solana.