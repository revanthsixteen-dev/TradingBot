import asyncio
import numpy as np
import logging
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from tradingagents.hft.instrument import Instrument

logger = logging.getLogger("hft.engine")

# NumPy ring buffer pre-allocated container for microsecond tick storage
class TickRingBuffer:
    """Pre-allocated circular buffer using NumPy arrays to ensure zero-copy operations in the critical path."""

    def __init__(self, capacity: int = 10000) -> None:
        self.capacity: int = capacity
        # Pre-allocate contiguous memory blocks for tick attributes
        self.timestamps: np.ndarray = np.zeros(capacity, dtype='datetime64[ns]')
        self.prices: np.ndarray = np.zeros(capacity, dtype=np.float64)
        self.volumes: np.ndarray = np.zeros(capacity, dtype=np.float64)
        self.bids: np.ndarray = np.zeros(capacity, dtype=np.float64)
        self.asks: np.ndarray = np.zeros(capacity, dtype=np.float64)
        self.bid_depths: np.ndarray = np.zeros(capacity, dtype=np.float64)
        self.ask_depths: np.ndarray = np.zeros(capacity, dtype=np.float64)
        
        self.head: int = 0
        self.size: int = 0

    def append(
        self,
        timestamp: np.datetime64,
        price: float,
        volume: float,
        bid: float,
        ask: float,
        bid_depth: float,
        ask_depth: float
    ) -> None:
        """Write to circular buffer with zero allocations."""
        self.timestamps[self.head] = timestamp
        self.prices[self.head] = price
        self.volumes[self.head] = volume
        self.bids[self.head] = bid
        self.asks[self.head] = ask
        self.bid_depths[self.head] = bid_depth
        self.ask_depths[self.head] = ask_depth

        self.head = (self.head + 1) % self.capacity
        if self.size < self.capacity:
            self.size += 1

    def get_last_n_prices(self, n: int) -> np.ndarray:
        """Retrieve recent closes using sliding indices."""
        n = min(n, self.size)
        if n == 0:
            return np.array([], dtype=np.float64)
        
        start = (self.head - n) % self.capacity
        if start < self.head:
            return self.prices[start:self.head]
        else:
            return np.concatenate((self.prices[start:], self.prices[:self.head]))

@dataclass(frozen=True)
class TickEvent:
    timestamp: np.datetime64
    symbol: str
    price: float
    volume: float
    bid: float
    ask: float
    bid_depth: float
    ask_depth: float
    order_book: Optional[Dict[str, Any]] = None

class HFTEngine:
    """Ultra-low latency event manager coordinating tick distribution and execution loops."""

    def __init__(self) -> None:
        self.buffers: Dict[str, TickRingBuffer] = {}
        self.instruments: Dict[str, Instrument] = {}
        self.strategies: List[Any] = []
        self._running: bool = False
        # Lock-free high-performance queue
        self.queue: asyncio.Queue[TickEvent] = asyncio.Queue(maxsize=100000)
        self._loop_task: Optional[asyncio.Task] = None

    def register_instrument(self, inst: Instrument) -> None:
        self.instruments[inst.symbol] = inst
        self.buffers[inst.symbol] = TickRingBuffer()

    def register_strategy(self, strategy: Any) -> None:
        self.strategies.append(strategy)
        logger.info(f"Registered HFT strategy: {strategy.name}")

    async def publish_tick(self, event: TickEvent) -> None:
        """Fast path: insert tick event into low latency ingestion queue."""
        if event.symbol in self.buffers:
            self.buffers[event.symbol].append(
                event.timestamp,
                event.price,
                event.volume,
                event.bid,
                event.ask,
                event.bid_depth,
                event.ask_depth
            )
        try:
            self.queue.put_nowait(event)
        except asyncio.QueueFull:
            logger.warning("HFT queue full, dropping tick event.")

    def start(self) -> None:
        self._running = True
        self._loop_task = asyncio.create_task(self._process_loop())
        logger.info("HFT Engine execution loop started.")

    async def stop(self) -> None:
        self._running = False
        if self._loop_task:
            self._loop_task.cancel()
            try:
                await self._loop_task
            except asyncio.CancelledError:
                pass

    async def _process_loop(self) -> None:
        """Hot path reader processing tick events sequentially."""
        while self._running:
            try:
                event = await self.queue.get()
                
                # Concurrently execute all register strategy slots
                for strat in self.strategies:
                    try:
                        # Executed inside current loop scope to prevent context switching latency
                        strat.on_tick(event)
                    except Exception as e:
                        logger.error(f"Strategy execution error on {strat.name}: {e}", exc_info=True)
                
                self.queue.task_done()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in HFT event loop: {e}", exc_info=True)
                await asyncio.sleep(0.001)
