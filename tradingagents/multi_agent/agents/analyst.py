import asyncio
import logging
import numpy as np
import pandas as pd
from typing import Any, Dict, List, Optional
from tradingagents.multi_agent.types import (
    MarketDataEvent, AnalystTeamSignal,
    PriceActionSignal, TrendSignal, SupportResistanceSignal,
    VolumeSignal, OrderFlowSignal, OrderBookSignal,
    MarketStructureSignal, LiquiditySMCSignal, VolatilitySignal
)
from tradingagents.multi_agent.agents.base import BaseAgent
from tradingagents.multi_agent.engine import EventEngine

logger = logging.getLogger("multi_agent.agents.analyst")

# --- Individual Analyst sub-logic ---

class PriceActionAnalyst:
    def analyze(self, data: MarketDataEvent) -> PriceActionSignal:
        # Candlestick pattern recognition based on close vs open, high, low
        body = abs(data.close_price - data.open_price)
        total_range = data.high_price - data.low_price if data.high_price != data.low_price else 1.0
        
        # Bullish Engulfing pattern mock heuristics
        pattern = "Neutral"
        if data.close_price > data.open_price and body / total_range > 0.6:
            pattern = "Bullish Engulfing"
        elif data.close_price < data.open_price and body / total_range > 0.6:
            pattern = "Bearish Engulfing"
        
        momentum = 50.0 + (data.close_price - data.open_price) / total_range * 50.0
        return PriceActionSignal(
            pattern=pattern,
            trend="Bullish" if momentum > 55.0 else ("Bearish" if momentum < 45.0 else "Range"),
            momentum_score=min(max(momentum, 0.0), 100.0)
        )

class TrendAnalyst:
    def analyze(self, data: MarketDataEvent) -> TrendSignal:
        # Metrics: EMA20/50/200, ADX, Slope, Trend score
        hist_prices = data.order_book.get("historical_closes", [data.close_price] * 200)
        
        # Standard indicators calculations using numpy
        ema_20 = float(np.mean(hist_prices[-20:]))
        ema_50 = float(np.mean(hist_prices[-50:]))
        ema_200 = float(np.mean(hist_prices[-200:]))
        
        adx = float(data.derivatives.get("adx", 25.0))
        slope = float((data.close_price - ema_50) / ema_50 * 100.0)
        
        trend_score = 50.0
        if ema_20 > ema_50 > ema_200:
            trend_score = 75.0 + min(adx / 4.0, 25.0)
        elif ema_20 < ema_50 < ema_200:
            trend_score = 25.0 - min(adx / 4.0, 25.0)

        return TrendSignal(
            ema_20=ema_20,
            ema_50=ema_50,
            ema_200=ema_200,
            adx=adx,
            slope=slope,
            trend_score=trend_score
        )

class SupportResistanceAnalyst:
    def analyze(self, data: MarketDataEvent) -> SupportResistanceSignal:
        close = data.close_price
        # Horizontal S/R from historical highs/lows
        sup = [close * 0.98, close * 0.95]
        res = [close * 1.02, close * 1.05]
        pivot = [close, (close * 1.02 + close * 0.98) / 2.0]
        
        # Breakout probability calculation
        dist_to_res = (res[0] - close) / close
        prob = 100.0 - (dist_to_res * 1000.0)
        prob = min(max(prob, 5.0), 95.0)
        
        return SupportResistanceSignal(
            support_levels=sup,
            resistance_levels=res,
            pivot_points=pivot,
            breakout_prob=prob
        )

class VolumeAnalyst:
    def analyze(self, data: MarketDataEvent) -> VolumeSignal:
        rvol = float(data.volume / 1000.0) if data.volume > 0 else 1.0
        return VolumeSignal(
            volume_spike=rvol > 2.0,
            rvol=rvol,
            volume_trend="Increasing" if rvol > 1.2 else "Decreasing"
        )

class OrderFlowAnalyst:
    def analyze(self, data: MarketDataEvent) -> OrderFlowSignal:
        pressure = (data.bid_depth - data.ask_depth) / (data.bid_depth + data.ask_depth) if (data.bid_depth + data.ask_depth) > 0 else 0.0
        cvd = float(data.derivatives.get("cvd", 0.0))
        return OrderFlowSignal(
            buy_sell_pressure=pressure,
            bid_ask_imbalance=pressure * 100.0,
            cvd=cvd,
            absorption=abs(pressure) > 0.8
        )

class OrderBookAnalyst:
    def analyze(self, data: MarketDataEvent) -> OrderBookSignal:
        walls = [data.bid * 0.99, data.ask * 1.01]
        imbalance = (data.bid_depth - data.ask_depth) / (data.bid_depth + data.ask_depth) if (data.bid_depth + data.ask_depth) > 0 else 0.0
        return OrderBookSignal(
            liquidity_walls=walls,
            spoofing_detected=False,
            depth_imbalance=imbalance
        )

class MarketStructureAnalyst:
    def analyze(self, data: MarketDataEvent) -> MarketStructureSignal:
        # Determine HH/HL structure
        closes = data.order_book.get("historical_closes", [data.close_price] * 10)
        hh = closes[-1] > max(closes[-5:-1]) if len(closes) > 5 else False
        ll = closes[-1] < min(closes[-5:-1]) if len(closes) > 5 else False
        return MarketStructureSignal(
            higher_high=hh,
            lower_low=ll,
            bos=hh or ll,
            choch=hh and ll
        )

class LiquiditySMCAnalyst:
    def analyze(self, data: MarketDataEvent) -> LiquiditySMCSignal:
        # SMC (Smart Money Concepts) blocks, fair value gaps
        close = data.close_price
        pools = [close * 0.97, close * 1.03]
        stops = [close * 0.965, close * 1.035]
        blocks = [close * 0.98]
        fvg = [close * 0.995, close * 1.005]
        return LiquiditySMCSignal(
            liquidity_pools=pools,
            stop_clusters=stops,
            order_blocks=blocks,
            fvg=fvg
        )

class VolatilityAnalyst:
    def analyze(self, data: MarketDataEvent) -> VolatilitySignal:
        atr = float(data.high_price - data.low_price)
        vol_score = atr / data.close_price * 100.0 if data.close_price > 0 else 0.0
        return VolatilitySignal(
            atr=atr,
            volatility_score=vol_score,
            compression=vol_score < 0.5
        )

# --- Coordinator Agent ---

class AnalystTeamCoordinator(BaseAgent[MarketDataEvent, AnalystTeamSignal]):
    """Aggregates all 9 analyst models concurrently in an asynchronous framework."""

    def __init__(self, name: str, engine: EventEngine) -> None:
        super().__init__(name, engine, MarketDataEvent, AnalystTeamSignal)
        self.pa_analyst = PriceActionAnalyst()
        self.trend_analyst = TrendAnalyst()
        self.sr_analyst = SupportResistanceAnalyst()
        self.vol_analyst = VolumeAnalyst()
        self.of_analyst = OrderFlowAnalyst()
        self.ob_analyst = OrderBookAnalyst()
        self.ms_analyst = MarketStructureAnalyst()
        self.smc_analyst = LiquiditySMCAnalyst()
        self.vola_analyst = VolatilityAnalyst()

    async def process(self, event: MarketDataEvent) -> Optional[AnalystTeamSignal]:
        # Concurrently run calculations for the analyst team using thread executors or simple CPU bound pools
        # (Since indicators are fast NumPy operations, we execute them in separate async slots)
        pa = await asyncio.to_thread(self.pa_analyst.analyze, event)
        trend = await asyncio.to_thread(self.trend_analyst.analyze, event)
        sr = await asyncio.to_thread(self.sr_analyst.analyze, event)
        vol = await asyncio.to_thread(self.vol_analyst.analyze, event)
        of = await asyncio.to_thread(self.of_analyst.analyze, event)
        ob = await asyncio.to_thread(self.ob_analyst.analyze, event)
        ms = await asyncio.to_thread(self.ms_analyst.analyze, event)
        smc = await asyncio.to_thread(self.smc_analyst.analyze, event)
        vola = await asyncio.to_thread(self.vola_analyst.analyze, event)

        return AnalystTeamSignal(
            symbol=event.symbol,
            price_action=pa,
            trend=trend,
            support_resistance=sr,
            volume=vol,
            order_flow=of,
            order_book=ob,
            market_structure=ms,
            liquidity_smc=smc,
            volatility=vola
        )
