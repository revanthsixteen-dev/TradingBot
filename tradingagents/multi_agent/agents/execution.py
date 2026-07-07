import logging
import random
from datetime import datetime
from typing import Optional
from tradingagents.multi_agent.types import RiskApprovedProposal, ExecutionReport, TradeAction
from tradingagents.multi_agent.agents.base import BaseAgent
from tradingagents.multi_agent.engine import EventEngine

logger = logging.getLogger("multi_agent.agents.execution")

class ExecutionAgent(BaseAgent[RiskApprovedProposal, ExecutionReport]):
    """Execution desk that simulates limit/market order routing, slippage, and fills."""

    def __init__(self, name: str, engine: EventEngine) -> None:
        super().__init__(name, engine, RiskApprovedProposal, ExecutionReport)

    async def process(self, event: RiskApprovedProposal) -> Optional[ExecutionReport]:
        if not event.approved:
            self._log_structured(logging.INFO, "Skipping execution for unapproved risk proposal.", {"symbol": event.symbol})
            return None

        # Simulate execution parameters
        action = event.proposal.action
        if action == TradeAction.HOLD:
            self._log_structured(logging.DEBUG, "No execution needed for HOLD proposal.", {"symbol": event.symbol})
            return None

        self._log_structured(logging.INFO, f"Routing execution order for {action.value}...", {"symbol": event.symbol})

        # Mock fill simulation
        success = True
        error_msg = None
        
        # Simulate slippage: random drift up to 0.1%
        slippage = random.uniform(0.0, 0.001)
        base_price = event.proposal.target_entry
        
        if action == TradeAction.BUY:
            filled_price = base_price * (1.0 + slippage)
        else:
            filled_price = base_price * (1.0 - slippage)

        # Mock fees: 0.1% taker fee
        fee_rate = 0.001
        fees = filled_price * event.adjusted_size * fee_rate

        self._log_structured(logging.INFO, f"Order filled successfully. Price: {filled_price:.2f}, Slippage: {slippage:.3%}", {"symbol": event.symbol})

        return ExecutionReport(
            symbol=event.symbol,
            action=action,
            executed=success,
            filled_price=filled_price,
            filled_qty=event.adjusted_size,
            slippage=slippage,
            fees=fees,
            execution_time=datetime.utcnow(),
            error_message=error_msg
        )
