import logging
from typing import Dict, Any
from tradingagents.hft.instrument import Instrument

logger = logging.getLogger("hft.risk")

class RealTimeRiskEngine:
    """Ultra-low latency risk validation module for validating orders pre-routing."""

    def __init__(self, init_capital: float = 1000000.0) -> None:
        self.total_capital: float = init_capital
        self.used_margin: float = 0.0
        self.daily_loss_limit: float = init_capital * 0.02  # 2% max daily loss
        self.cumulative_loss: float = 0.0
        self.max_leverage: float = 5.0  # 5x max portfolio leverage
        
        # Position tracking: symbol -> current absolute position quantity
        self.positions: Dict[str, float] = {}
        self.kill_switch_active: bool = False

    def activate_kill_switch(self) -> None:
        self.kill_switch_active = True
        logger.critical("EMERGENCY KILL SWITCH ACTIVATED. ALL TRADING SUSPENDED.")

    def deactivate_kill_switch(self) -> None:
        self.kill_switch_active = False
        logger.info("Kill switch deactivated. Resuming normal operations.")

    def update_capital(self, realized_pnl: float) -> None:
        self.total_capital += realized_pnl
        if realized_pnl < 0:
            self.cumulative_loss += abs(realized_pnl)

    def pre_trade_risk_check(
        self,
        symbol: str,
        price: float,
        qty: float,
        action: str,
        inst: Instrument
    ) -> bool:
        """Execute pre-routing checks. Returns True if order is approved, False otherwise."""
        if self.kill_switch_active:
            return False

        # Drawdown / Loss limit check
        if self.cumulative_loss >= self.daily_loss_limit:
            logger.error(f"Trade rejected: Daily loss limit breached ({self.cumulative_loss:.2f} >= {self.daily_loss_limit:.2f})")
            return False

        # Calculate contract value based on asset type multipliers
        contract_multiplier = inst.price_multiplier
        order_value = price * qty * contract_multiplier
        
        # Margin and leverage checks
        current_exposure = sum(
            abs(self.positions.get(s, 0.0)) * price * self.price_multiplier_for(s)
            for s in self.positions
        )
        projected_exposure = current_exposure + order_value
        
        projected_leverage = projected_exposure / self.total_capital if self.total_capital > 0 else 999.0
        if projected_leverage > self.max_leverage:
            logger.error(f"Trade rejected: Leverage limit breach ({projected_leverage:.2f}x > {self.max_leverage:.2f}x)")
            return False

        # Locate verification for Stock short selling
        if action.upper() == "SELL" and inst.asset_class.value == "STOCK":
            current_pos = self.positions.get(symbol, 0.0)
            if current_pos - qty < 0 and inst.locate_required:
                logger.warning(f"Short locate warning on {symbol}: Borrow fee is {inst.borrow_fee_rate:.2%}")

        return True

    def price_multiplier_for(self, symbol: str) -> float:
        # Internal helper mapping multipliers
        return 1.0

    def update_position(self, symbol: str, fill_qty: float, action: str) -> None:
        """Update internal position states after execution confirmation."""
        multiplier = 1.0 if action.upper() == "BUY" else -1.0
        current = self.positions.get(symbol, 0.0)
        self.positions[symbol] = current + (fill_qty * multiplier)
