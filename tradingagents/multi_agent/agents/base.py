import asyncio
import logging
import time
from typing import Any, Dict, Generic, TypeVar
from pydantic import BaseModel
from tradingagents.multi_agent.engine import EventEngine

logger = logging.getLogger("multi_agent.agents.base")

TIn = TypeVar("TIn", bound=BaseModel)
TOut = TypeVar("TOut", bound=BaseModel)

class CircuitBreakerOpenException(Exception):
    """Exception raised when the circuit breaker is open."""
    pass

class BaseAgent(Generic[TIn, TOut]):
    """Abstract base class for all TradingAgents in the system.
    
    Includes built-in:
    - Circuit Breaker pattern
    - Exponential backoff retry logic
    - Event engine registration
    - Structured logging
    """

    def __init__(
        self,
        name: str,
        engine: EventEngine,
        input_type: type[TIn],
        output_type: type[TOut],
        failure_threshold: int = 3,
        recovery_timeout: float = 10.0,
    ) -> None:
        self.name: str = name
        self.engine: EventEngine = engine
        self.input_type: type[TIn] = input_type
        self.output_type: type[TOut] = output_type
        
        # Circuit Breaker states: CLOSED, OPEN, HALF-OPEN
        self.failure_threshold: int = failure_threshold
        self.recovery_timeout: float = recovery_timeout
        self.failure_count: int = 0
        self.state: str = "CLOSED"
        self.last_state_change: float = time.time()

        # Register standard subscriber
        self.engine.subscribe(self.input_type, self.on_event)

    def _log_structured(self, level: int, msg: str, extra: Dict[str, Any] = None) -> None:
        """Structured logging helper."""
        log_data = {
            "agent": self.name,
            "state": self.state,
            "failures": self.failure_count,
            **(extra or {})
        }
        logger.log(level, f"[{self.name}] {msg} | Context: {log_data}")

    def trip_breaker(self) -> None:
        """Open the circuit breaker."""
        self.state = "OPEN"
        self.last_state_change = time.time()
        self._log_structured(logging.ERROR, "Circuit breaker tripped! Breaker is now OPEN.")

    def reset_breaker(self) -> None:
        """Close the circuit breaker."""
        self.state = "CLOSED"
        self.failure_count = 0
        self.last_state_change = time.time()
        self._log_structured(logging.INFO, "Circuit breaker reset. Breaker is now CLOSED.")

    def attempt_recovery(self) -> bool:
        """Attempt to transition from OPEN to HALF-OPEN."""
        if self.state == "OPEN" and (time.time() - self.last_state_change) > self.recovery_timeout:
            self.state = "HALF-OPEN"
            self.last_state_change = time.time()
            self._log_structured(logging.WARNING, "Attempting recovery: Breaker transition to HALF-OPEN.")
            return True
        return False

    async def on_event(self, event: TIn) -> None:
        """Standard event routing slot."""
        if not isinstance(event, self.input_type):
            return

        if self.state == "OPEN":
            if not self.attempt_recovery():
                self._log_structured(logging.WARNING, f"Event skipped. Circuit breaker is open.")
                return

        self._log_structured(logging.DEBUG, f"Processing incoming event of type {type(event).__name__}")
        
        # Exponential backoff retry loop
        max_attempts = 3
        backoff = 1.0
        for attempt in range(max_attempts):
            try:
                # Execute agent-specific implementation
                output_event = await self.process(event)
                
                # If we were in HALF-OPEN state, reset the breaker on success
                if self.state == "HALF-OPEN":
                    self.reset_breaker()
                
                if output_event:
                    await self.engine.publish(output_event)
                return
            except Exception as e:
                self.failure_count += 1
                self._log_structured(logging.ERROR, f"Process failure (attempt {attempt+1}/{max_attempts}): {e}", {"error": str(e)})
                
                # Check if failure threshold is reached
                if self.failure_count >= self.failure_threshold:
                    self.trip_breaker()
                    break

                # Sleep with backoff
                await asyncio.sleep(backoff)
                backoff *= 2.0

    async def process(self, event: TIn) -> Optional[TOut]:
        """Core logic to override in subclasses."""
        raise NotImplementedError("Subclasses must implement the process method.")
