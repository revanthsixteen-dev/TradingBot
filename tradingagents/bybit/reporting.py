import asyncio
import logging
from datetime import datetime
from typing import List, Dict, Any

logger = logging.getLogger("bybit.reporting")

class PnLTracker:
    """Tracks individual trades, realized PnLs, transaction fees, and cumulative stats."""

    def __init__(self) -> None:
        self.trades: List[Dict[str, Any]] = []
        self.cumulative_pnl: float = 0.0
        self.cumulative_fees: float = 0.0

    def record_entry(self, order_id: str, symbol: str, side: str, price: float, qty: float, fees: float) -> None:
        trade_log = {
            "order_id": order_id,
            "symbol": symbol,
            "direction": side,
            "entry_price": price,
            "exit_price": 0.0,
            "qty": qty,
            "realized_pnl": 0.0,
            "fees": fees,
            "status": "OPEN",
            "timestamp": datetime.utcnow().isoformat()
        }
        self.trades.append(trade_log)
        self.cumulative_fees += fees
        logger.info(f"Recorded entry: {symbol} {side} at {price:.2f}, Qty={qty}")

    def record_exit(self, symbol: str, exit_price: float) -> None:
        """Close open trade logs for the symbol and calculate PnL."""
        for trade in self.trades:
            if trade["symbol"] == symbol and trade["status"] == "OPEN":
                trade["exit_price"] = exit_price
                trade["status"] = "CLOSED"
                
                # PnL Calculation: (Exit - Entry) * Qty for Buy, (Entry - Exit) * Qty for Sell
                multiplier = 1.0 if trade["direction"].upper() == "BUY" else -1.0
                pnl = (exit_price - trade["entry_price"]) * trade["qty"] * multiplier
                
                # Approximate exit fees (0.06% taker fee)
                exit_fees = exit_price * trade["qty"] * 0.0006
                trade["fees"] += exit_fees
                trade["realized_pnl"] = pnl - trade["fees"]
                
                self.cumulative_pnl += trade["realized_pnl"]
                self.cumulative_fees += exit_fees
                
                logger.info(f"Recorded exit: {symbol} closed at {exit_price:.2f}. PnL: ${trade['realized_pnl']:.2f} (Fees: ${trade['fees']:.2f})")
                return

    def generate_report(self) -> str:
        """Formulate a comprehensive text report of all activity since start."""
        now_str = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        report = []
        report.append(f"\n{'='*50}")
        report.append(f"BYBIT ALGORITHMIC TRADING REPORT - {now_str} UTC")
        report.append(f"{'='*50}")
        report.append(f"Cumulative PnL (Net): ${self.cumulative_pnl:.2f}")
        report.append(f"Cumulative Fees:      ${self.cumulative_fees:.2f}")
        report.append(f"Total Trades Executed: {len(self.trades)}")
        report.append(f"{'-'*50}")
        report.append("DETAILED TRADE LOGS:")
        
        for idx, t in enumerate(self.trades):
            status_str = f"CLOSED (PnL: ${t['realized_pnl']:.2f})" if t["status"] == "CLOSED" else "OPEN"
            report.append(
                f"{idx+1}. Symbol={t['symbol']} | Side={t['direction']} | Qty={t['qty']} | "
                f"Entry={t['entry_price']:.2f} | Exit={t['exit_price']:.2f} | Fees=${t['fees']:.2f} | Status={status_str}"
            )
        report.append(f"{'='*50}\n")
        
        report_text = "\n".join(report)
        logger.info("Generated 12-Hour Report Summary.")
        print(report_text) # Print to stdout as well
        return report_text

async def schedule_12h_reports(tracker: PnLTracker, interval_seconds: int = 12 * 3600) -> None:
    """Asynchronous background task runner executing report generation periodically."""
    logger.info(f"12-Hour Report Scheduler started. Interval={interval_seconds}s")
    while True:
        try:
            await asyncio.sleep(interval_seconds)
            report_summary = tracker.generate_report()
            
            # Save report to a text file for records
            with open("trading_bot.log", "a", encoding="utf-8") as f:
                f.write(report_summary)
        except asyncio.CancelledError:
            logger.info("Report scheduler task cancelled.")
            break
        except Exception as e:
            logger.error(f"Error in scheduler execution loop: {e}", exc_info=True)
            await asyncio.sleep(10)
