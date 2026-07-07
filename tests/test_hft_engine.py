import asyncio
import numpy as np
import pytest
from datetime import datetime
from tradingagents.hft.instrument import Instrument, AssetClass
from tradingagents.hft.engine import HFTEngine, TickEvent
from tradingagents.hft.risk import RealTimeRiskEngine
from tradingagents.hft.execution import DirectMarketAccessClient, ExecutionOrder
from tradingagents.hft.strategy import Scalping, HFTMarketMaking, StatisticalArbitrage

def test_ring_buffer_preallocation():
    inst = Instrument(symbol="AAPL", asset_class=AssetClass.STOCK)
    engine = HFTEngine()
    engine.register_instrument(inst)
    
    buf = engine.buffers["AAPL"]
    
    # Append tick to ring buffer
    now = np.datetime64(datetime.utcnow())
    buf.append(now, 150.0, 1000.0, 149.9, 150.1, 50.0, 40.0)
    
    assert buf.size == 1
    prices = buf.get_last_n_prices(1)
    assert len(prices) == 1
    assert prices[0] == 150.0

def test_risk_leverage_limits():
    risk = RealTimeRiskEngine(init_capital=100000.0)
    inst = Instrument(symbol="BTC-USD", asset_class=AssetClass.CRYPTO)
    
    # Approve trade under leverage limits
    approved = risk.pre_trade_risk_check("BTC-USD", 50000.0, 2.0, "BUY", inst)
    assert approved is True
    
    # Exceeding leverage limits: 300000.0 exposure exceeds 100000.0 capital * 5.0 leverage limit
    rejected = risk.pre_trade_risk_check("BTC-USD", 50000.0, 11.0, "BUY", inst)
    assert rejected is False

async def _async_test_hft_engine_pipeline():
    engine = HFTEngine()
    inst = Instrument(symbol="BTC-USD", asset_class=AssetClass.CRYPTO)
    engine.register_instrument(inst)
    
    # Register strategy
    scalper = Scalping("Scalper", inst)
    engine.register_strategy(scalper)
    
    # Capture strategy output signal mock
    signals = []
    original_execute = scalper.execute_logic
    
    def mock_execute(event):
        sig = original_execute(event)
        if sig:
            signals.append(sig)
    
    scalper.execute_logic = mock_execute
    
    engine.start()
    
    # High bid depth -> triggers Scalping BUY signal
    event = TickEvent(
        timestamp=np.datetime64(datetime.utcnow()),
        symbol="BTC-USD",
        price=50000.0,
        volume=10.0,
        bid=49999.0,
        ask=50001.0,
        bid_depth=100.0,
        ask_depth=20.0
    )
    
    await engine.publish_tick(event)
    
    # Wait for loop consumer
    for _ in range(10):
        if len(signals) > 0:
            break
        await asyncio.sleep(0.01)
        
    await engine.stop()
    assert len(signals) == 1
    assert signals[0].symbol == "BTC-USD"

def test_hft_engine_pipeline():
    asyncio.run(_async_test_hft_engine_pipeline())
