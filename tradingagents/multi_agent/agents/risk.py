import logging
from typing import Optional
from tradingagents.multi_agent.types import StrategyProposal, RiskApprovedProposal
from tradingagents.multi_agent.agents.base import BaseAgent
from tradingagents.multi_agent.engine import EventEngine

logger = logging.getLogger("multi_agent.agents.risk")

class RiskManager(BaseAgent[StrategyProposal, RiskApprovedProposal]):
    """Protects portfolio from blowup by adjusting size, stops, and enforcing limits."""

    def __init__(self, name: str, engine: EventEngine) -> None:
        super().__init__(name, engine, StrategyProposal, RiskApprovedProposal)
        self.max_drawdown_limit = 0.10  # 10% maximum drawdown
        self.current_drawdown = 0.02
        self.daily_loss_limit = 0.02    # 2% daily loss limit
        self.current_daily_loss = 0.00
        self.leverage_limit = 3.0       # 3x maximum leverage
        self.max_correlation_limit = 0.7
        self.kill_switch_active = False

    async def process(self, event: StrategyProposal) -> Optional[RiskApprovedProposal]:
        if self.kill_switch_active:
            self._log_structured(logging.CRITICAL, "EMERGENCY KILL SWITCH ACTIVE. Proposal rejected.", {"symbol": event.symbol})
            return RiskApprovedProposal(
                symbol=event.symbol,
                proposal=event,
                approved=False,
                adjusted_size=0.0,
                adjusted_sl=event.target_sl
            )

        # Drawdown check
        if self.current_drawdown >= self.max_drawdown_limit:
            self._log_structured(logging.ERROR, "Max drawdown limit breached. Rejecting all new positions.", {"drawdown": self.current_drawdown})
            return RiskApprovedProposal(
                symbol=event.symbol,
                proposal=event,
                approved=False,
                adjusted_size=0.0,
                adjusted_sl=event.target_sl
            )

        # Daily loss limit check
        if self.current_daily_loss >= self.daily_loss_limit:
            self._log_structured(logging.ERROR, "Daily loss limit breached. Proposal rejected.", {"daily_loss": self.current_daily_loss})
            return RiskApprovedProposal(
                symbol=event.symbol,
                proposal=event,
                approved=False,
                adjusted_size=0.0,
                adjusted_sl=event.target_sl
            )

        # Volatility-adjusted sizing
        # Base sizing: 5% of portfolio. Adjust down if volatility is high or if we are close to limits
        base_size = 0.05
        vol_modifier = 1.0
        
        # Volatility check simulation
        vol_score = event.bull_bear.conviction_score
        if vol_score > 80.0:
            # High conviction but high volatility, reduce size to preserve capital
            vol_modifier = 0.6
        elif vol_score < 40.0:
            # Low conviction, reduce size
            vol_modifier = 0.5
            
        final_size = base_size * vol_modifier

        # Risk parameters verification
        entry = event.target_entry
        sl = event.target_sl
        
        if event.action == "Buy" and sl >= entry:
            # Stop loss must be below entry price for Buy
            sl = entry * 0.98  # Adjust stop loss to a safer 2% below entry
            self._log_structured(logging.WARNING, "Adjusted stop loss to be below entry price.", {"original_sl": event.target_sl, "new_sl": sl})
        elif event.action == "Sell" and sl <= entry:
            # Stop loss must be above entry price for Sell
            sl = entry * 1.02
            self._log_structured(logging.WARNING, "Adjusted stop loss to be above entry price.", {"original_sl": event.target_sl, "new_sl": sl})

        approved = final_size > 0.0
        
        self._log_structured(logging.INFO, f"Proposal approved with adjusted size: {final_size:.2%}", {"symbol": event.symbol, "size": final_size})

        return RiskApprovedProposal(
            symbol=event.symbol,
            proposal=event,
            approved=approved,
            adjusted_size=final_size,
            adjusted_sl=sl,
            risk_metric_snapshot={
                "drawdown": self.current_drawdown,
                "daily_loss": self.current_daily_loss,
                "vol_modifier": vol_modifier
            }
        )
