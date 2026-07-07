import asyncio
import pytest
from datetime import datetime
from tradingagents.multi_agent.engine import EventEngine
from tradingagents.multi_agent.types import MarketDataEvent, AssetType, TradeAction, PortfolioRating
from tradingagents.multi_agent.agents.analyst import AnalystTeamCoordinator
from tradingagents.multi_agent.agents.researcher import ResearchTeamCoordinator
from tradingagents.multi_agent.agents.strategy import TraderAgent
from tradingagents.multi_agent.agents.risk import RiskManager
from tradingagents.multi_agent.agents.execution import ExecutionAgent

async def _async_test_pipeline():
    engine = EventEngine()
    engine.start()

    # Instantiate agents
    analyst_coord = AnalystTeamCoordinator("Analyst Coordinator", engine)
    research_coord = ResearchTeamCoordinator("Research Coordinator", engine)
    trader_agent = TraderAgent("Trader Agent", engine)
    risk_manager = RiskManager("Risk Manager", engine)
    execution_agent = ExecutionAgent("Execution Agent", engine)

    # Track output events
    execution_reports = []
    
    async def track_execution(event):
        execution_reports.append(event)
        
    engine.subscribe(execution_agent.output_type, track_execution)

    # Generate test market event
    event = MarketDataEvent(
        symbol="BTC-USD",
        asset_type=AssetType.CRYPTO,
        open_price=50000.0,
        high_price=51000.0,
        low_price=49000.0,
        close_price=50500.0,
        volume=150.0,
        bid=50490.0,
        ask=50510.0,
        bid_depth=50.0,
        ask_depth=40.0,
        order_book={"historical_closes": [50000.0 + i for i in range(200)]},
        on_chain={"whale_inflows": 10.0},
        derivatives={"funding_rate": 0.0001, "open_interest": 1000000.0}
    )

    # Publish start event
    await engine.publish(event)

    # Wait for the async event pipeline to complete propagation
    # Ingest -> Analyst -> Research -> Strategy -> Risk -> Execution
    for _ in range(20):
        if len(execution_reports) > 0:
            break
        await asyncio.sleep(0.1)

    await engine.stop()

    assert len(execution_reports) == 1
    report = execution_reports[0]
    assert report.symbol == "BTC-USD"
    assert report.executed is True
    assert report.filled_price > 0
    assert report.fees > 0

def test_multi_agent_pipeline():
    asyncio.run(_async_test_pipeline())
