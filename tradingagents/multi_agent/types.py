from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

class AssetType(str, Enum):
    STOCK = "stock"
    CRYPTO = "crypto"

class TradeAction(str, Enum):
    BUY = "Buy"
    HOLD = "Hold"
    SELL = "Sell"

class PortfolioRating(str, Enum):
    BUY = "Buy"
    OVERWEIGHT = "Overweight"
    HOLD = "Hold"
    UNDERWEIGHT = "Underweight"
    SELL = "Sell"

# --- Core Market Events ---

class MarketDataEvent(BaseModel):
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    symbol: str
    asset_type: AssetType
    open_price: float
    high_price: float
    low_price: float
    close_price: float
    volume: float
    bid: float
    ask: float
    bid_depth: float
    ask_depth: float
    order_book: Dict[str, Any] = Field(default_factory=dict)
    on_chain: Dict[str, Any] = Field(default_factory=dict)
    derivatives: Dict[str, Any] = Field(default_factory=dict)

# --- Analyst Output Signals ---

class PriceActionSignal(BaseModel):
    pattern: str
    trend: str
    momentum_score: float

class TrendSignal(BaseModel):
    ema_20: float
    ema_50: float
    ema_200: float
    adx: float
    slope: float
    trend_score: float

class SupportResistanceSignal(BaseModel):
    support_levels: List[float]
    resistance_levels: List[float]
    pivot_points: List[float]
    breakout_prob: float

class VolumeSignal(BaseModel):
    volume_spike: bool
    rvol: float
    volume_trend: str

class OrderFlowSignal(BaseModel):
    buy_sell_pressure: float
    bid_ask_imbalance: float
    cvd: float
    absorption: bool

class OrderBookSignal(BaseModel):
    liquidity_walls: List[float]
    spoofing_detected: bool
    depth_imbalance: float

class MarketStructureSignal(BaseModel):
    higher_high: bool
    lower_low: bool
    bos: bool  # Break of Structure
    choch: bool  # Change of Character

class LiquiditySMCSignal(BaseModel):
    liquidity_pools: List[float]
    stop_clusters: List[float]
    order_blocks: List[float]
    fvg: List[float]  # Fair Value Gap

class VolatilitySignal(BaseModel):
    atr: float
    volatility_score: float
    compression: bool

class AnalystTeamSignal(BaseModel):
    symbol: str
    price_action: PriceActionSignal
    trend: TrendSignal
    support_resistance: SupportResistanceSignal
    volume: VolumeSignal
    order_flow: OrderFlowSignal
    order_book: OrderBookSignal
    market_structure: MarketStructureSignal
    liquidity_smc: LiquiditySMCSignal
    volatility: VolatilitySignal

# --- Research Output Signals ---

class ResearchTeamSignal(BaseModel):
    symbol: str
    on_chain_flow: float
    derivatives_oi: float
    derivatives_funding: float
    sentiment_score: float
    macro_score: float
    correlation_score: float
    narrative_score: float
    details: Dict[str, Any] = Field(default_factory=dict)

# --- Strategy Proposals ---

class BullBearCase(BaseModel):
    bullish_arguments: List[str]
    bearish_arguments: List[str]
    conviction_score: float

class StrategyProposal(BaseModel):
    symbol: str
    action: TradeAction
    rating: PortfolioRating
    target_entry: float
    target_sl: float
    target_tp: float
    rationale: str
    bull_bear: BullBearCase

# --- Risk Approved Proposals ---

class RiskApprovedProposal(BaseModel):
    symbol: str
    proposal: StrategyProposal
    approved: bool
    adjusted_size: float  # Percentage of portfolio
    adjusted_sl: float
    risk_metric_snapshot: Dict[str, Any] = Field(default_factory=dict)

# --- Execution Reports ---

class ExecutionReport(BaseModel):
    symbol: str
    action: TradeAction
    executed: bool
    filled_price: Optional[float] = None
    filled_qty: float = 0.0
    slippage: float = 0.0
    fees: float = 0.0
    execution_time: datetime = Field(default_factory=datetime.utcnow)
    error_message: Optional[str] = None
