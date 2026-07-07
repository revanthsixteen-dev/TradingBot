import logging
from typing import Optional
from tradingagents.multi_agent.types import ResearchTeamSignal, StrategyProposal, TradeAction, PortfolioRating, BullBearCase
from tradingagents.multi_agent.agents.base import BaseAgent
from tradingagents.multi_agent.engine import EventEngine

logger = logging.getLogger("multi_agent.agents.strategy")

class BullResearcher:
    def evaluate(self, signal: ResearchTeamSignal) -> list[str]:
        cases = []
        if signal.sentiment_score > 6.0:
            cases.append("Strong positive retail sentiment on social media.")
        if signal.on_chain_flow > 0:
            cases.append("Whale accumulation spotted in on-chain exchange flows.")
        if signal.narrative_score > 7.0:
            cases.append("Leading sector narrative support (AI / institutional interest).")
        return cases if cases else ["No clear bullish catalysts identified."]

class BearResearcher:
    def evaluate(self, signal: ResearchTeamSignal) -> list[str]:
        cases = []
        if signal.sentiment_score < 4.0:
            cases.append("Bearish sentiment spikes on forums.")
        if signal.derivatives_funding > 8.0:
            cases.append("Over-leveraged longs / extreme positive funding rates indicating volatility traps.")
        if signal.macro_score < 4.0:
            cases.append("Macro pressures from interest rates or inflation expectations.")
        return cases if cases else ["No clear bearish catalysts identified."]

# --- Chief Trader Agent ---

class TraderAgent(BaseAgent[ResearchTeamSignal, StrategyProposal]):
    """Chief Decision Maker: Evaluates research, analyst signals, and generates trading actions."""

    def __init__(self, name: str, engine: EventEngine) -> None:
        super().__init__(name, engine, ResearchTeamSignal, StrategyProposal)
        self.bull_researcher = BullResearcher()
        self.bear_researcher = BearResearcher()

    async def process(self, event: ResearchTeamSignal) -> Optional[StrategyProposal]:
        # Run Bull/Bear researcher modules
        bull_arguments = self.bull_researcher.evaluate(event)
        bear_arguments = self.bear_researcher.evaluate(event)
        
        # Settle on conviction and rating
        conviction = event.sentiment_score
        
        bull_count = len(bull_arguments) if bull_arguments[0] != "No clear bullish catalysts identified." else 0
        bear_count = len(bear_arguments) if bear_arguments[0] != "No clear bearish catalysts identified." else 0
        
        # Simple heuristic decision maker
        if bull_count > bear_count:
            action = TradeAction.BUY
            rating = PortfolioRating.BUY if conviction > 7.5 else PortfolioRating.OVERWEIGHT
            rationale = "Bullish case dominates based on whale flow accumulation and retail sentiment support."
        elif bear_count > bull_count:
            action = TradeAction.SELL
            rating = PortfolioRating.SELL if conviction < 3.5 else PortfolioRating.UNDERWEIGHT
            rationale = "Bearish case dominates, macro indicators suggest caution or potential downside risk."
        else:
            action = TradeAction.HOLD
            rating = PortfolioRating.HOLD
            rationale = "Bullish and bearish arguments are evenly balanced. Standing aside."

        # Setup entry targets based on detail snapshots or close price defaults
        target_entry = 50000.0  # Simple default for mock stream
        target_sl = target_entry * 0.95 if action == TradeAction.BUY else target_entry * 1.05
        target_tp = target_entry * 1.15 if action == TradeAction.BUY else target_entry * 0.85

        self._log_structured(logging.INFO, f"Generated Strategy Proposal: {action.value} ({rating.value})", {"symbol": event.symbol})

        return StrategyProposal(
            symbol=event.symbol,
            action=action,
            rating=rating,
            target_entry=target_entry,
            target_sl=target_sl,
            target_tp=target_tp,
            rationale=rationale,
            bull_bear=BullBearCase(
                bullish_arguments=bull_arguments,
                bearish_arguments=bear_arguments,
                conviction_score=conviction * 10.0
            )
        )
