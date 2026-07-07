import asyncio
import logging
from typing import Any, Dict, List, Optional
from tradingagents.multi_agent.types import AnalystTeamSignal, ResearchTeamSignal
from tradingagents.multi_agent.agents.base import BaseAgent
from tradingagents.multi_agent.engine import EventEngine

logger = logging.getLogger("multi_agent.agents.researcher")

class OnChainResearcher:
    def research(self, data: AnalystTeamSignal) -> float:
        # returns whale flow score (-10 to +10)
        return 4.5

class DerivativesResearcher:
    def research(self, data: AnalystTeamSignal) -> tuple[float, float]:
        # returns (open_interest_score, funding_rate_score)
        return 7.0, 5.5

class NewsResearcher:
    def research(self, data: AnalystTeamSignal) -> float:
        # ETF announcements, news momentum score
        return 8.0

class SentimentResearcher:
    def research(self, data: AnalystTeamSignal) -> float:
        # Reddit / Twitter retail sentiment score
        return 6.8

class MacroResearcher:
    def research(self, data: AnalystTeamSignal) -> float:
        # Fed rate decisions score
        return 5.0

class CorrelationResearcher:
    def research(self, data: AnalystTeamSignal) -> float:
        # Cross market index correlations
        return 3.2

class NarrativeResearcher:
    def research(self, data: AnalystTeamSignal) -> float:
        # Sector narrative score (e.g. AI / Memes / RWA)
        return 9.0

# --- Research Coordinator ---

class ResearchTeamCoordinator(BaseAgent[AnalystTeamSignal, ResearchTeamSignal]):
    """Coordinates the 7 researchers to create a cohesive ResearchTeamSignal."""

    def __init__(self, name: str, engine: EventEngine) -> None:
        super().__init__(name, engine, AnalystTeamSignal, ResearchTeamSignal)
        self.on_chain = OnChainResearcher()
        self.derivatives = DerivativesResearcher()
        self.news = NewsResearcher()
        self.sentiment = SentimentResearcher()
        self.macro = MacroResearcher()
        self.correlation = CorrelationResearcher()
        self.narrative = NarrativeResearcher()

    async def process(self, event: AnalystTeamSignal) -> Optional[ResearchTeamSignal]:
        # Concurrently gather intelligence from the researchers
        flow = await asyncio.to_thread(self.on_chain.research, event)
        deriv = await asyncio.to_thread(self.derivatives.research, event)
        news = await asyncio.to_thread(self.news.research, event)
        sent = await asyncio.to_thread(self.sentiment.research, event)
        macro = await asyncio.to_thread(self.macro.research, event)
        corr = await asyncio.to_thread(self.correlation.research, event)
        narr = await asyncio.to_thread(self.narrative.research, event)

        return ResearchTeamSignal(
            symbol=event.symbol,
            on_chain_flow=flow,
            derivatives_oi=deriv[0],
            derivatives_funding=deriv[1],
            sentiment_score=sent,
            macro_score=macro,
            correlation_score=corr,
            narrative_score=narr,
            details={
                "oi_conviction": "high" if deriv[0] > 6.0 else "medium",
                "active_narrative": "Institutional accumulation / AI theme"
            }
        )
