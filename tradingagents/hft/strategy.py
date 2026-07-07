import math
import numpy as np
from datetime import datetime
from typing import Dict, List, Any, Optional
from pydantic import BaseModel
from tradingagents.hft.engine import TickEvent
from tradingagents.hft.instrument import Instrument

class StrategySignal(BaseModel):
    symbol: str
    action: str  # BUY, SELL, HOLD
    price: float
    qty: float
    strategy_name: str
    metadata: Dict[str, Any] = {}

class BaseStrategy:
    """Base class for all algorithmic and HFT strategies."""

    def __init__(self, name: str, instrument: Instrument) -> None:
        self.name: str = name
        self.instrument: Instrument = instrument
        self.active: bool = True

    def on_tick(self, event: TickEvent) -> Optional[StrategySignal]:
        """Process incoming tick update in the hot path. Returns a signal or None."""
        if not self.active or event.symbol != self.instrument.symbol:
            return None
        return self.execute_logic(event)

    def execute_logic(self, event: TickEvent) -> Optional[StrategySignal]:
        raise NotImplementedError("Subclasses must implement execute_logic.")

# ==============================================================================
# CATEGORY A: ARBITRAGE STRATEGIES
# ==============================================================================

class ExchangeArbitrage(BaseStrategy):
    """1. Exchange Arbitrage: Capitalizes on cross-exchange price spreads."""
    
    def execute_logic(self, event: TickEvent) -> Optional[StrategySignal]:
        # Cross-exchange prices are mapped from event metadata
        ex_a_bid = event.order_book.get("exchange_a_bid", event.bid)
        ex_b_ask = event.order_book.get("exchange_b_ask", event.ask * 1.002) # Mock premium
        
        # Arbitrage Condition: Bid Exchange A > Ask Exchange B + Costs
        costs = 0.0005 * event.close_price # 5 bps transaction fees
        spread = ex_a_bid - ex_b_ask - costs
        
        if spread > 0:
            return StrategySignal(
                symbol=event.symbol,
                action="BUY", # Buy on Exchange B, Sell on Exchange A
                price=ex_b_ask,
                qty=self.instrument.min_order_qty,
                strategy_name=self.name,
                metadata={"spread": spread, "buy_ex": "B", "sell_ex": "A"}
            )
        return None

class CashAndFutureArbitrage(BaseStrategy):
    """2. Basis Trading: Cash vs Future arbitrage."""

    def execute_logic(self, event: TickEvent) -> Optional[StrategySignal]:
        cash_price = event.price
        future_price = event.order_book.get("future_price", cash_price * 1.005)
        
        # Basis calculation
        basis = future_price - cash_price
        carry_costs = 0.001 * cash_price # storage + financing cost
        
        if basis > carry_costs:
            # Overpriced Future: Short Future, Long Cash
            return StrategySignal(
                symbol=event.symbol,
                action="BUY", # Buying the cash leg
                price=cash_price,
                qty=self.instrument.min_order_qty,
                strategy_name=self.name,
                metadata={"arbitrage_type": "cash_and_carry", "basis": basis}
            )
        return None

class IndexArbitrage(BaseStrategy):
    """3. Index Arbitrage: Index ETF vs Component Basket."""

    def execute_logic(self, event: TickEvent) -> Optional[StrategySignal]:
        etf_price = event.price
        basket_nav = event.order_book.get("basket_nav", etf_price * 0.998)
        
        threshold = 0.0015 * etf_price  # 15 bps threshold
        
        if etf_price - basket_nav > threshold:
            # ETF trades at premium: Sell ETF, Buy Basket Components
            return StrategySignal(
                symbol=event.symbol,
                action="SELL",
                price=etf_price,
                qty=self.instrument.min_order_qty,
                strategy_name=self.name,
                metadata={"premium": etf_price - basket_nav}
            )
        return None

class OptionsArbitrage(BaseStrategy):
    """4. Put-Call Parity: Option vs Underlying Basket arbitrage."""

    def execute_logic(self, event: TickEvent) -> Optional[StrategySignal]:
        underlying = event.price
        call_price = event.order_book.get("call_price", 0.0)
        put_price = event.order_book.get("put_price", 0.0)
        strike = self.instrument.strike_price or underlying
        
        if call_price == 0.0 or put_price == 0.0:
            return None
            
        r, t = 0.05, 30.0 / 365.0
        discount = math.exp(-r * t)
        
        # Parity validation: Call + Strike*discount = Put + Stock
        left_side = call_price + strike * discount
        right_side = put_price + underlying
        deviation = abs(left_side - right_side)
        
        if deviation > 0.02 * underlying:
            action = "BUY" if left_side < right_side else "SELL"
            return StrategySignal(
                symbol=event.symbol,
                action=action,
                price=underlying,
                qty=self.instrument.min_order_qty,
                strategy_name=self.name,
                metadata={"deviation": deviation}
            )
        return None

class InterestRateArbitrage(BaseStrategy):
    """5. Interest Rate Arbitrage: Covered Interest Parity (Forex)."""

    def execute_logic(self, event: TickEvent) -> Optional[StrategySignal]:
        spot = event.price
        forward = event.order_book.get("forward_rate", spot * 1.001)
        
        # Rates domestic and foreign
        r_d, r_f = 0.045, 0.02
        t = 90.0 / 360.0 # 3 Months
        
        implied_forward = spot * ((1.0 + r_d * t) / (1.0 + r_f * t))
        spread = forward - implied_forward
        
        if abs(spread) > 0.001 * spot:
            return StrategySignal(
                symbol=event.symbol,
                action="BUY" if spread > 0 else "SELL",
                price=spot,
                qty=self.instrument.min_order_qty,
                strategy_name=self.name,
                metadata={"implied_forward": implied_forward, "spread": spread}
            )
        return None

class YieldCurveArbitrage(BaseStrategy):
    """6. Yield Curve Arbitrage: Mispricing on bond yield spreads."""

    def execute_logic(self, event: TickEvent) -> Optional[StrategySignal]:
        # Spread curve: 10Y minus 2Y Treasury rates
        rate_2y = event.order_book.get("rate_2y", 4.2)
        rate_10y = event.order_book.get("rate_10y", 4.5)
        spread = rate_10y - rate_2y
        
        mean_spread = 0.15 # Historical spread average
        
        if spread > mean_spread + 0.5:
            # Curve steepened excessively: Short 10Y, Long 2Y
            return StrategySignal(
                symbol=event.symbol,
                action="SELL",
                price=event.price,
                qty=self.instrument.min_order_qty,
                strategy_name=self.name,
                metadata={"spread": spread, "action_type": "flatten"}
            )
        return None

class StockVsADRArbitrage(BaseStrategy):
    """7. Stock vs ADR Arbitrage: Resolves international exchange pricing loops."""

    def execute_logic(self, event: TickEvent) -> Optional[StrategySignal]:
        local_price = event.price
        adr_price = event.order_book.get("adr_price", local_price * 1.002)
        fx_rate = event.order_book.get("fx_rate", 1.0)
        conversion_ratio = event.order_book.get("conversion_ratio", 1.0)
        
        implied_adr = local_price * fx_rate * conversion_ratio
        arbitrage_spread = adr_price - implied_adr
        
        if abs(arbitrage_spread) > 0.003 * adr_price:
            return StrategySignal(
                symbol=event.symbol,
                action="BUY" if arbitrage_spread > 0 else "SELL",
                price=local_price,
                qty=self.instrument.min_order_qty,
                strategy_name=self.name,
                metadata={"adr_spread": arbitrage_spread}
            )
        return None

class CommodityArbitrage(BaseStrategy):
    """8. Commodity Arbitrage: Calendar spreads on future expiries."""

    def execute_logic(self, event: TickEvent) -> Optional[StrategySignal]:
        front_month = event.price
        back_month = event.order_book.get("back_month_price", front_month * 1.01)
        
        # Basis carry costs evaluation
        implied_carry = back_month - front_month
        normal_carry = 0.005 * front_month
        
        if implied_carry > normal_carry * 1.5:
            # Sell back month, Buy front month
            return StrategySignal(
                symbol=event.symbol,
                action="BUY",
                price=front_month,
                qty=self.instrument.min_order_qty,
                strategy_name=self.name,
                metadata={"implied_carry": implied_carry}
            )
        return None

class StatisticalArbitrage(BaseStrategy):
    """9. Statistical Arbitrage: Cointegration spread mean reversion."""

    def execute_logic(self, event: TickEvent) -> Optional[StrategySignal]:
        price_a = event.price
        price_b = event.order_book.get("pair_stock_price", price_a)
        
        # Cointegration spread equation: Spread = StockA - (Beta * StockB)
        beta = 0.85
        spread = price_a - (beta * price_b)
        
        mean_spread = 0.0
        std_spread = 0.50
        z_score = (spread - mean_spread) / std_spread
        
        if z_score > 2.0:
            # Short Stock A, Long Stock B
            return StrategySignal(
                symbol=event.symbol,
                action="SELL",
                price=price_a,
                qty=self.instrument.min_order_qty,
                strategy_name=self.name,
                metadata={"z_score": z_score}
            )
        elif z_score < -2.0:
            # Long Stock A, Short Stock B
            return StrategySignal(
                symbol=event.symbol,
                action="BUY",
                price=price_a,
                qty=self.instrument.min_order_qty,
                strategy_name=self.name,
                metadata={"z_score": z_score}
            )
        return None

class TriangularArbitrage(BaseStrategy):
    """10. Triangular Arbitrage: Crypto cross pair cycles (BTC -> ETH -> USD -> BTC)."""

    def execute_logic(self, event: TickEvent) -> Optional[StrategySignal]:
        # Cross currency rates
        btc_usd = event.price
        eth_usd = event.order_book.get("eth_usd", btc_usd * 0.06)
        eth_btc = event.order_book.get("eth_btc", 0.0601)
        
        if eth_btc == 0:
            return None

        # Implied loop conversion: buy BTC, sell BTC for ETH, sell ETH for USD
        implied_rate = (1.0 / eth_btc) * eth_usd
        arbitrage_ratio = implied_rate / btc_usd
        
        if arbitrage_ratio > 1.002: # 20 bps arbitrage trigger
            return StrategySignal(
                symbol=event.symbol,
                action="BUY",
                price=btc_usd,
                qty=self.instrument.min_order_qty,
                strategy_name=self.name,
                metadata={"arbitrage_ratio": arbitrage_ratio}
            )
        return None

class ETFvsStockArbitrage(BaseStrategy):
    """11. ETF NAV Premium / Discount Arbitrage."""

    def execute_logic(self, event: TickEvent) -> Optional[StrategySignal]:
        etf_price = event.price
        components_value = event.order_book.get("components_total_value", etf_price)
        
        etf_premium = (etf_price - components_value) / components_value
        
        if etf_premium > 0.0025:
            # Premium arbitrage: Sell ETF, Buy basket
            return StrategySignal(
                symbol=event.symbol,
                action="SELL",
                price=etf_price,
                qty=self.instrument.min_order_qty,
                strategy_name=self.name,
                metadata={"premium": etf_premium}
            )
        return None

# ==============================================================================
# CATEGORY B: TIMEFRAME & DIRECTIONAL STRATEGIES
# ==============================================================================

class Scalping(BaseStrategy):
    """12. Scalping: Micro-second order book imbalances."""

    def execute_logic(self, event: TickEvent) -> Optional[StrategySignal]:
        total_depth = event.bid_depth + event.ask_depth
        if total_depth == 0:
            return None
            
        imbalance = (event.bid_depth - event.ask_depth) / total_depth
        
        if imbalance > 0.6:
            # Heavy buying pressure on order book
            return StrategySignal(
                symbol=event.symbol,
                action="BUY",
                price=event.ask,
                qty=self.instrument.min_order_qty,
                strategy_name=self.name,
                metadata={"book_imbalance": imbalance}
            )
        elif imbalance < -0.6:
            # Heavy selling pressure
            return StrategySignal(
                symbol=event.symbol,
                action="SELL",
                price=event.bid,
                qty=self.instrument.min_order_qty,
                strategy_name=self.name,
                metadata={"book_imbalance": imbalance}
            )
        return None

class DayTrading(BaseStrategy):
    """13. Day Trading: Mean Reversion to VWAP."""

    def execute_logic(self, event: TickEvent) -> Optional[StrategySignal]:
        vwap = event.order_book.get("vwap", event.price)
        std_dev = event.order_book.get("price_std", 1.0)
        
        # Deviation limits
        upper_limit = vwap + 2.0 * std_dev
        lower_limit = vwap - 2.0 * std_dev
        
        if event.price >= upper_limit:
            return StrategySignal(
                symbol=event.symbol,
                action="SELL",
                price=event.price,
                qty=self.instrument.min_order_qty,
                strategy_name=self.name,
                metadata={"vwap_deviation": "high"}
            )
        elif event.price <= lower_limit:
            return StrategySignal(
                symbol=event.symbol,
                action="BUY",
                price=event.price,
                qty=self.instrument.min_order_qty,
                strategy_name=self.name,
                metadata={"vwap_deviation": "low"}
            )
        return None

class SwingTrading(BaseStrategy):
    """14. Swing Trading: Multiday Momentum swings."""

    def execute_logic(self, event: TickEvent) -> Optional[StrategySignal]:
        macd_line = event.order_book.get("macd_line", 0.0)
        signal_line = event.order_book.get("signal_line", 0.0)
        
        if macd_line > signal_line:
            return StrategySignal(
                symbol=event.symbol,
                action="BUY",
                price=event.price,
                qty=self.instrument.min_order_qty,
                strategy_name=self.name
            )
        return None

class PositionTrading(BaseStrategy):
    """15. Position Trading: Trend-Following moving average crossings."""

    def execute_logic(self, event: TickEvent) -> Optional[StrategySignal]:
        sma_50 = event.order_book.get("sma_50", event.price)
        sma_200 = event.order_book.get("sma_200", event.price)
        
        if sma_50 > sma_200:
            return StrategySignal(
                symbol=event.symbol,
                action="BUY",
                price=event.price,
                qty=self.instrument.min_order_qty,
                strategy_name=self.name
            )
        return None

class TrendTrading(BaseStrategy):
    """16. Trend Trading: Donchian Channel breakout."""

    def execute_logic(self, event: TickEvent) -> Optional[StrategySignal]:
        channel_high = event.order_book.get("donchian_high", event.price)
        channel_low = event.order_book.get("donchian_low", event.price)
        
        if event.price >= channel_high:
            return StrategySignal(
                symbol=event.symbol,
                action="BUY",
                price=event.price,
                qty=self.instrument.min_order_qty,
                strategy_name=self.name
            )
        return None

class BreakoutTrading(BaseStrategy):
    """17. Breakout Trading: Volatility-Expansion breakouts."""

    def execute_logic(self, event: TickEvent) -> Optional[StrategySignal]:
        atr = event.order_book.get("atr", 1.0)
        resistance = event.order_book.get("resistance", event.price)
        
        # Volatility breakout trigger
        if event.price > resistance + 0.5 * atr:
            return StrategySignal(
                symbol=event.symbol,
                action="BUY",
                price=event.price,
                qty=self.instrument.min_order_qty,
                strategy_name=self.name
            )
        return None

class RangeTrading(BaseStrategy):
    """18. Range Trading: RSI + Bollinger Bands mean reversion."""

    def execute_logic(self, event: TickEvent) -> Optional[StrategySignal]:
        rsi = event.order_book.get("rsi", 50.0)
        boll_lb = event.order_book.get("boll_lb", event.price * 0.98)
        boll_ub = event.order_book.get("boll_ub", event.price * 1.02)
        
        if rsi <= 30.0 and event.price <= boll_lb:
            return StrategySignal(
                symbol=event.symbol,
                action="BUY",
                price=event.price,
                qty=self.instrument.min_order_qty,
                strategy_name=self.name
            )
        elif rsi >= 70.0 and event.price >= boll_ub:
            return StrategySignal(
                symbol=event.symbol,
                action="SELL",
                price=event.price,
                qty=self.instrument.min_order_qty,
                strategy_name=self.name
            )
        return None

class NewsTrading(BaseStrategy):
    """19. News Trading: Sentiment Analysis Event Spike processing."""

    def execute_logic(self, event: TickEvent) -> Optional[StrategySignal]:
        news_sentiment = event.order_book.get("news_sentiment_score", 5.0) # 0 to 10
        
        if news_sentiment >= 8.0:
            return StrategySignal(
                symbol=event.symbol,
                action="BUY",
                price=event.price,
                qty=self.instrument.min_order_qty,
                strategy_name=self.name,
                metadata={"sentiment": "highly_bullish"}
            )
        elif news_sentiment <= 2.0:
            return StrategySignal(
                symbol=event.symbol,
                action="SELL",
                price=event.price,
                qty=self.instrument.min_order_qty,
                strategy_name=self.name,
                metadata={"sentiment": "highly_bearish"}
            )
        return None

class MomentumTrading(BaseStrategy):
    """20. Momentum Trading: Rate of Change (ROC) indicator."""

    def execute_logic(self, event: TickEvent) -> Optional[StrategySignal]:
        roc = event.order_book.get("roc_14", 0.0)
        
        if roc > 2.5: # 2.5% rate of change trigger
            return StrategySignal(
                symbol=event.symbol,
                action="BUY",
                price=event.price,
                qty=self.instrument.min_order_qty,
                strategy_name=self.name
            )
        return None

class CarryTrading(BaseStrategy):
    """21. Carry Trading: Forex Interest Rate Differential."""

    def execute_logic(self, event: TickEvent) -> Optional[StrategySignal]:
        # Checks daily interest rates
        domestic_rate = event.order_book.get("domestic_rate", 0.05)
        foreign_rate = event.order_book.get("foreign_rate", 0.01)
        
        # Buy domestic, Short foreign if rate spread is positive
        if domestic_rate - foreign_rate > 0.03:
            return StrategySignal(
                symbol=event.symbol,
                action="BUY",
                price=event.price,
                qty=self.instrument.min_order_qty,
                strategy_name=self.name,
                metadata={"interest_spread": domestic_rate - foreign_rate}
            )
        return None

# ==============================================================================
# CATEGORY C: SPECIALIZED, QUANT & DERIVATIVES STRATEGIES
# ==============================================================================

class HFTMarketMaking(BaseStrategy):
    """22. Market Making: Avellaneda-Stoikov model for order books."""

    def execute_logic(self, event: TickEvent) -> Optional[StrategySignal]:
        s = event.price
        q = event.order_book.get("current_position", 0.0) # Inventory parameter
        gamma = 0.1
        sigma = event.order_book.get("volatility", 0.02)
        T_minus_t = 1.0 # time fraction to end of session
        
        # Optimal reservation price
        reservation_price = s - q * gamma * (sigma ** 2) * T_minus_t
        
        # Optimal spreads around reservation
        spread = 2.0 * math.log(1.0 + gamma / 0.1) / gamma
        bid_price = reservation_price - spread / 2.0
        
        return StrategySignal(
            symbol=event.symbol,
            action="BUY",
            price=bid_price,
            qty=self.instrument.min_order_qty,
            strategy_name=self.name,
            metadata={"reservation_price": reservation_price, "spread": spread}
        )

class GridTrading(BaseStrategy):
    """23. Grid Trading: Oscillating grid limit loops."""

    def execute_logic(self, event: TickEvent) -> Optional[StrategySignal]:
        reference_price = event.order_book.get("grid_reference", event.price)
        grid_interval = 0.01 * reference_price # 1% grid spacing
        
        # If price falls below a grid step, execute buy order
        if event.price <= reference_price - grid_interval:
            return StrategySignal(
                symbol=event.symbol,
                action="BUY",
                price=event.price,
                qty=self.instrument.min_order_qty,
                strategy_name=self.name
            )
        return None

class EarningsTrading(BaseStrategy):
    """24. Earnings Trading: Volatility crush implied options spreads."""

    def execute_logic(self, event: TickEvent) -> Optional[StrategySignal]:
        implied_vol = event.order_book.get("implied_vol", 0.80)
        historical_vol = event.order_book.get("historical_vol", 0.40)
        
        # If IV is significantly higher than HV before earnings, sell volatility
        if implied_vol > historical_vol * 1.8:
            return StrategySignal(
                symbol=event.symbol,
                action="SELL", # Sell Volatility structure
                price=event.price,
                qty=self.instrument.min_order_qty,
                strategy_name=self.name,
                metadata={"crush_probability": "high"}
            )
        return None

class PairTrading(BaseStrategy):
    """25. Pair Trading: Cointegration mean reversion."""

    def execute_logic(self, event: TickEvent) -> Optional[StrategySignal]:
        # Relies on the same z-score calculation as statistical arbitrage
        z_score = event.order_book.get("pair_z_score", 0.0)
        
        if z_score >= 2.0:
            return StrategySignal(symbol=event.symbol, action="SELL", price=event.price, qty=self.instrument.min_order_qty, strategy_name=self.name)
        elif z_score <= -2.0:
            return StrategySignal(symbol=event.symbol, action="BUY", price=event.price, qty=self.instrument.min_order_qty, strategy_name=self.name)
        return None

class OptionsTrading(BaseStrategy):
    """26. Options Greeks: Delta-neutral options trading."""

    def execute_logic(self, event: TickEvent) -> Optional[StrategySignal]:
        delta = event.order_book.get("position_delta", 0.0)
        
        # Delta hedging threshold
        if abs(delta) > 0.5:
            # Hedge needed: execute offset shares
            action = "SELL" if delta > 0 else "BUY"
            return StrategySignal(
                symbol=event.symbol,
                action=action,
                price=event.price,
                qty=abs(delta) * self.instrument.min_order_qty,
                strategy_name=self.name,
                metadata={"delta_hedge": True}
            )
        return None

class FuturesTrading(BaseStrategy):
    """27. Futures Roll Yield Arbitrage: Contango vs Backwardation."""

    def execute_logic(self, event: TickEvent) -> Optional[StrategySignal]:
        # Evaluates roll yield between front and back futures contracts
        front_month = event.price
        back_month = event.order_book.get("back_month_price", front_month * 1.02)
        
        roll_yield = (front_month - back_month) / front_month
        
        if roll_yield > 0.02:
            # Backwardation: Long Front Future, Short Back Future
            return StrategySignal(
                symbol=event.symbol,
                action="BUY",
                price=front_month,
                qty=self.instrument.min_order_qty,
                strategy_name=self.name
            )
        return None

class ETFTrading(BaseStrategy):
    """28. ETF Sector Rotation Strategy."""

    def execute_logic(self, event: TickEvent) -> Optional[StrategySignal]:
        relative_strength = event.order_book.get("relative_strength_score", 50.0)
        
        if relative_strength > 80.0:
            # Sector momentum outperformer
            return StrategySignal(
                symbol=event.symbol,
                action="BUY",
                price=event.price,
                qty=self.instrument.min_order_qty,
                strategy_name=self.name
            )
        return None

class Martingale(BaseStrategy):
    """29. Capped Martingale Position Sizing."""

    def __init__(self, name: str, instrument: Instrument) -> None:
        super().__init__(name, instrument)
        self.consecutive_losses = 0

    def execute_logic(self, event: TickEvent) -> Optional[StrategySignal]:
        # Determine performance feedback from engine
        pnl = event.order_book.get("last_trade_pnl", 0.0)
        
        if pnl < 0:
            self.consecutive_losses += 1
        else:
            self.consecutive_losses = 0
            
        # Martingale multiplication: size * 2^(losses)
        base_qty = self.instrument.min_order_qty
        multiplier = 2 ** min(self.consecutive_losses, 4) # capped at 4 consecutive doublings to avoid ruin
        
        if self.consecutive_losses > 0:
            return StrategySignal(
                symbol=event.symbol,
                action="BUY",
                price=event.price,
                qty=base_qty * multiplier,
                strategy_name=self.name,
                metadata={"martingale_step": self.consecutive_losses}
            )
        return None

class ICTSMC(BaseStrategy):
    """30. SMC Concepts: Fair Value Gap (FVG) and Order Block sweep zones."""

    def execute_logic(self, event: TickEvent) -> Optional[StrategySignal]:
        fvg_top = event.order_book.get("fvg_top", 0.0)
        fvg_bottom = event.order_book.get("fvg_bottom", 0.0)
        
        # Sweep validation: If price returns to the FVG block area, trade correction
        if event.price <= fvg_top and event.price >= fvg_bottom:
            return StrategySignal(
                symbol=event.symbol,
                action="BUY",
                price=event.price,
                qty=self.instrument.min_order_qty,
                strategy_name=self.name,
                metadata={"block_type": "fvg_fill"}
            )
        return None

class AlgorithmicTrading(BaseStrategy):
    """31. VWAP Execution Algorithm Slicer."""

    def execute_logic(self, event: TickEvent) -> Optional[StrategySignal]:
        target_qty = event.order_book.get("parent_order_qty", 0.0)
        if target_qty <= 0:
            return None
            
        # Slice target quantities into standard execution buckets
        slice_qty = min(target_qty * 0.05, self.instrument.max_order_qty)
        
        return StrategySignal(
            symbol=event.symbol,
            action="BUY",
            price=event.price,
            qty=self.instrument.round_qty(slice_qty),
            strategy_name=self.name,
            metadata={"execution_slice": True}
        )

class QuantitativeTrading(BaseStrategy):
    """32. Quantitative factor combination trading."""

    def execute_logic(self, event: TickEvent) -> Optional[StrategySignal]:
        # Quantitative Multi-Factor model linear summation
        mom_factor = event.order_book.get("momentum_factor", 0.0)
        val_factor = event.order_book.get("value_factor", 0.0)
        vol_factor = event.order_book.get("volatility_factor", 0.0)
        
        alpha_composite = 0.4 * mom_factor + 0.3 * val_factor + 0.3 * vol_factor
        
        if alpha_composite > 1.5:
            return StrategySignal(
                symbol=event.symbol,
                action="BUY",
                price=event.price,
                qty=self.instrument.min_order_qty,
                strategy_name=self.name,
                metadata={"alpha_score": alpha_composite}
            )
        return None
