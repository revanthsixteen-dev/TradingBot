import pytest
from unittest.mock import MagicMock
from tradingagents.bybit.client import BybitTestnetClient
from tradingagents.bybit.reporting import PnLTracker

def test_bybit_qty_sizing_exact_notional():
    client = BybitTestnetClient()
    
    # Mock get_symbol_step_size to return standard 0.001
    client.get_symbol_step_size = MagicMock(return_value=0.001)

    # If price is $3000.0 (like ETH)
    price = 3000.0
    qty = client.calculate_order_qty("ETHUSDT", price)
    
    notional = qty * price
    assert notional <= 100.0
    # Step size was 0.001, so qty must be rounded down
    assert qty == 0.033

    # If price is $0.075 (like DOGE)
    price = 0.075
    qty = client.calculate_order_qty("DOGEUSDT", price)
    notional = qty * price
    assert notional <= 100.0
    assert qty == 1333.333

def test_pnl_tracker_calculations():
    tracker = PnLTracker()
    
    # Record Buy Entry at $100
    tracker.record_entry(
        order_id="test-buy-1",
        symbol="BTCUSDT",
        side="BUY",
        price=50000.0,
        qty=0.002,
        fees=0.06 # ($100 * 0.06% = $0.06)
    )
    
    assert len(tracker.trades) == 1
    assert tracker.trades[0]["status"] == "OPEN"
    
    # Close at $105, simulating exit
    tracker.record_exit("BTCUSDT", 52500.0)
    
    assert tracker.trades[0]["status"] == "CLOSED"
    
    # PnL math check: (52500.0 - 50000.0) * 0.002 = $5.00
    # Exit fees: 52500.0 * 0.002 * 0.0006 = $0.063
    # Total fees: $0.06 + $0.063 = $0.123
    # Realized Net PnL: $5.00 - $0.123 = $4.877
    assert round(tracker.trades[0]["realized_pnl"], 3) == 4.877
    assert round(tracker.cumulative_pnl, 3) == 4.877

def test_report_generation():
    tracker = PnLTracker()
    tracker.record_entry("id-1", "ETHUSDT", "BUY", 3000.0, 0.033, 0.06)
    tracker.record_exit("ETHUSDT", 3100.0)
    
    report = tracker.generate_report()
    assert "Cumulative PnL" in report
    assert "ETHUSDT" in report
    assert "CLOSED" in report
