import os
import math
import logging
from typing import Dict, Any, Optional
from pybit.unified_trading import HTTP
from dotenv import load_dotenv

load_dotenv()

# Setup Logging to console and trading_bot.log file
logger = logging.getLogger("bybit.client")
logger.setLevel(logging.INFO)

if not logger.handlers:
    fh = logging.FileHandler("trading_bot.log", encoding="utf-8")
    fh.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
    logger.addHandler(fh)
    ch = logging.StreamHandler()
    ch.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
    logger.addHandler(ch)

class BybitTestnetClient:
    """Secure Bybit client for execution on Testnet V5 endpoints."""

    def __init__(self) -> None:
        self.api_key: str = os.getenv("BYBIT_API_KEY", "")
        self.api_secret: str = os.getenv("BYBIT_API_SECRET", "")
        
        # Initialize REST HTTP client specifically for Testnet
        self.session = HTTP(
            testnet=True,
            api_key=self.api_key if self.api_key else None,
            api_secret=self.api_secret if self.api_secret else None,
        )
        
        if not self.api_key or not self.api_secret:
            logger.warning("Bybit API Key or Secret not found in environment. Running in sandbox-only mode.")

    def get_symbol_step_size(self, symbol: str) -> float:
        """Fetch min order step size from exchange specifications."""
        try:
            resp = self.session.get_instruments_info(category="linear", symbol=symbol)
            list_info = resp.get("result", {}).get("list", [])
            if list_info:
                lot_size_filter = list_info[0].get("lotSizeFilter", {})
                return float(lot_size_filter.get("qtyStep", 0.001))
        except Exception as e:
            logger.error(f"Error fetching step size for {symbol}: {e}")
        return 0.001

    def calculate_order_qty(self, symbol: str, price: float) -> float:
        """Calculate position size so that notional value is exactly $100 USD (never exceeding it)."""
        if price <= 0:
            return 0.0
            
        step_size = self.get_symbol_step_size(symbol)
        
        # Quantity calculation: target $100 notional
        raw_qty = 100.0 / price
        
        # Round down to nearest step size
        qty = math.floor(raw_qty / step_size) * step_size
        
        # Safety check: if rounding up or drift exceeds $100, step down
        if qty * price > 100.0:
            qty = max(0.0, qty - step_size)
            
        logger.info(f"Sizing: Symbol={symbol}, Price=${price:.2f}, Qty={qty}, Notional=${qty*price:.2f} (Max=$100)")
        return qty

    def place_market_order(self, symbol: str, side: str) -> Optional[Dict[str, Any]]:
        """Place market order on Testnet with error handling and rate limit catch blocks."""
        try:
            # Fetch current ticker price to estimate sizing
            ticker_resp = self.session.get_tickers(category="linear", symbol=symbol)
            list_tickers = ticker_resp.get("result", {}).get("list", [])
            if not list_tickers:
                logger.error(f"Could not retrieve ticker info for {symbol}")
                return None
                
            price = float(list_tickers[0].get("lastPrice", 0.0))
            qty = self.calculate_order_qty(symbol, price)
            if qty <= 0.0:
                logger.error(f"Calculated quantity is 0 for {symbol}. Order aborted.")
                return None

            # Execution order placement
            order = self.session.place_order(
                category="linear",
                symbol=symbol,
                side=side.capitalize(),
                orderType="Market",
                qty=str(qty),
                timeInForce="GTC"
            )
            
            logger.info(f"Placed order successfully: {order}")
            return {
                "order_id": order.get("result", {}).get("orderId"),
                "symbol": symbol,
                "side": side.capitalize(),
                "price": price,
                "qty": qty,
                "fees": price * qty * 0.0006 # standard 6 bps maker/taker fee approximation
            }
        except Exception as e:
            logger.error(f"Order placement failed on {symbol}: {e}", exc_info=True)
            return None
