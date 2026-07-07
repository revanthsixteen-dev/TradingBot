from datetime import datetime
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field

class AssetClass(str, Enum):
    STOCK = "STOCK"
    CRYPTO = "CRYPTO"
    FOREX = "FOREX"
    DERIVATIVE = "DERIVATIVE"
    BOND = "BOND"

class Instrument(BaseModel):
    """Unified representation of a tradable instrument across asset classes."""
    symbol: str = Field(..., description="Unique trading ticker/symbol")
    asset_class: AssetClass = Field(..., description="The asset classification type")
    
    # Tick size and lot parameters
    tick_size: float = Field(default=0.01, description="Minimum price movement")
    lot_size: float = Field(default=1.0, description="Standard contract/lot size")
    min_order_qty: float = Field(default=1.0, description="Minimum order quantity allowed")
    max_order_qty: float = Field(default=100000.0, description="Maximum order quantity allowed")
    
    # Pricing conventions
    base_currency: str = Field(default="USD", description="Base currency (Forex/Crypto)")
    quote_currency: str = Field(default="USD", description="Quote currency")
    price_multiplier: float = Field(default=1.0, description="Contract multiplier for derivatives")
    
    # Equity specifics
    locate_required: bool = Field(default=False, description="Short selling locate required (Stocks)")
    borrow_fee_rate: float = Field(default=0.0, description="Annualized cost to borrow for shorting")
    
    # Derivative specifics
    expiration: Optional[datetime] = Field(default=None, description="Contract expiration time")
    strike_price: Optional[float] = Field(default=None, description="Strike price (Options)")
    is_call: Optional[bool] = Field(default=None, description="True for Call option, False for Put")
    
    # Forex specifics
    pip_value: float = Field(default=0.0001, description="Value representation of a pip")

    def round_price(self, price: float) -> float:
        """Round the price to the nearest tick size."""
        if self.tick_size == 0.0:
            return price
        return round(round(price / self.tick_size) * self.tick_size, 8)

    def round_qty(self, qty: float) -> float:
        """Validate and round quantity boundaries."""
        if qty < self.min_order_qty:
            return 0.0
        # Round to 8 decimal places for crypto fractional quantities, or integer for stocks
        if self.asset_class == AssetClass.CRYPTO:
            return round(qty, 8)
        return float(int(qty))
