import asyncio
import json
import logging
from datetime import datetime
import websockets
from typing import Callable, Optional
from tradingagents.multi_agent.types import MarketDataEvent, AssetType
from tradingagents.multi_agent.engine import EventEngine

logger = logging.getLogger("multi_agent.connection")

class RealTimeDataFeed:
    """Manages the ingestion of real-time market data via WebSockets."""

    def __init__(self, engine: EventEngine, ws_uri: Optional[str] = None) -> None:
        self.engine = engine
        self.ws_uri = ws_uri or "wss://api.mocktrading.com/live"
        self._running: bool = False
        self._task: Optional[asyncio.Task] = None

    def start(self) -> None:
        """Start the ingestion thread / task."""
        self._running = True
        self._task = asyncio.create_task(self._read_feed())

    async def stop(self) -> None:
        """Stop reading the data feed."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

    async def _read_feed(self) -> None:
        """Asynchronously connect and read from WebSocket."""
        # Check if we should fall back to simulation for local tests
        if "mock" in self.ws_uri or not self.ws_uri.startswith("ws"):
            logger.info("Starting Simulated Feed (mock mode)...")
            await self._run_simulation()
            return

        while self._running:
            try:
                async with websockets.connect(self.ws_uri, timeout=10.0) as ws:
                    logger.info(f"WebSocket connected to {self.ws_uri}")
                    while self._running:
                        msg = await ws.recv()
                        data = json.loads(msg)
                        
                        # Translate raw WS message to MarketDataEvent
                        event = MarketDataEvent(
                            symbol=data.get("symbol", "BTC-USD"),
                            asset_type=AssetType(data.get("asset_type", "crypto")),
                            open_price=float(data.get("open", 0.0)),
                            high_price=float(data.get("high", 0.0)),
                            low_price=float(data.get("low", 0.0)),
                            close_price=float(data.get("close", 0.0)),
                            volume=float(data.get("volume", 0.0)),
                            bid=float(data.get("bid", 0.0)),
                            ask=float(data.get("ask", 0.0)),
                            bid_depth=float(data.get("bid_depth", 0.0)),
                            ask_depth=float(data.get("ask_depth", 0.0)),
                            order_book=data.get("order_book", {}),
                            on_chain=data.get("on_chain", {}),
                            derivatives=data.get("derivatives", {})
                        )
                        await self.engine.publish(event)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"WebSocket error: {e}. Retrying in 5 seconds...", exc_info=True)
                await asyncio.sleep(5.0)

    async def _run_simulation(self) -> None:
        """Mock simulator that generates tick data for testing."""
        import random
        base_price = 50000.0
        while self._running:
            try:
                # Random walk simulation
                tick = random.normalvariate(0, 50.0)
                base_price += tick
                bid = base_price - 0.5
                ask = base_price + 0.5
                
                event = MarketDataEvent(
                    symbol="BTC-USD",
                    asset_type=AssetType.CRYPTO,
                    open_price=base_price - random.uniform(0, 10),
                    high_price=base_price + random.uniform(0, 20),
                    low_price=base_price - random.uniform(0, 20),
                    close_price=base_price,
                    volume=random.uniform(1.0, 10.0),
                    bid=bid,
                    ask=ask,
                    bid_depth=random.uniform(10.0, 100.0),
                    ask_depth=random.uniform(10.0, 100.0),
                    order_book={"bids": [[bid, 10.0]], "asks": [[ask, 10.0]]},
                    on_chain={"whale_inflows": random.uniform(-100, 100)},
                    derivatives={"funding_rate": 0.0001, "open_interest": 1000000.0}
                )
                await self.engine.publish(event)
                await asyncio.sleep(1.0)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Simulation error: {e}")
                await asyncio.sleep(1.0)
