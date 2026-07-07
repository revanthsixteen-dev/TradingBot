import asyncio
import logging
import random
from typing import List, Optional
from tradingagents.bybit.client import BybitTestnetClient
from tradingagents.bybit.reporting import PnLTracker, schedule_12h_reports

logger = logging.getLogger("bybit.bot")

class BybitTradingBot:
    """Continuous execution loop coordinating market data feeds and order routing."""

    def __init__(self, symbols: List[str]) -> None:
        self.symbols = symbols
        self.client = BybitTestnetClient()
        self.tracker = PnLTracker()
        self._running = False
        self._tasks: List[asyncio.Task] = []

    def start(self, report_interval_seconds: int = 12 * 3600) -> None:
        self._running = True
        
        # Start core loop and background scheduler tasks
        self._tasks.append(asyncio.create_task(self._continuous_loop()))
        self._tasks.append(asyncio.create_task(schedule_12h_reports(self.tracker, report_interval_seconds)))
        
        logger.info(f"Bybit Trading Bot started on symbols: {self.symbols}")

    async def stop(self) -> None:
        self._running = False
        for task in self._tasks:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
        self._tasks.clear()
        logger.info("Bybit Trading Bot stopped.")

    async def _continuous_loop(self) -> None:
        """Main non-blocking execution loop polling prices and placing trades."""
        logger.info("Core execution loop started.")
        while self._running:
            for symbol in self.symbols:
                try:
                    # Fetch price feed details safely
                    ticker_resp = self.client.session.get_tickers(category="linear", symbol=symbol)
                    list_tickers = ticker_resp.get("result", {}).get("list", [])
                    if not list_tickers:
                        logger.warning(f"No price ticker retrieved for {symbol}")
                        continue
                        
                    price = float(list_tickers[0].get("lastPrice", 0.0))
                    
                    # Heuristics signal generation for testing or integration
                    # (Buy if random chance, sell if already holding, simulating signals)
                    action = random.choice(["BUY", "SELL", "HOLD"])
                    
                    has_open_position = any(
                        t["symbol"] == symbol and t["status"] == "OPEN" for t in self.tracker.trades
                    )

                    if action == "BUY" and not has_open_position:
                        order_details = self.client.place_market_order(symbol, "BUY")
                        if order_details:
                            self.tracker.record_entry(
                                order_id=order_details["order_id"],
                                symbol=symbol,
                                side="BUY",
                                price=order_details["price"],
                                qty=order_details["qty"],
                                fees=order_details["fees"]
                            )
                    elif action == "SELL" and has_open_position:
                        order_details = self.client.place_market_order(symbol, "SELL")
                        if order_details:
                            self.tracker.record_exit(symbol, order_details["price"])
                            
                except Exception as e:
                    logger.error(f"Error in continuous execution flow for {symbol}: {e}", exc_info=True)
                    # Insufficient Balance or rate limits require cooling down
                    await asyncio.sleep(10.0)

            # Polling delay loop
            await asyncio.sleep(5.0)
