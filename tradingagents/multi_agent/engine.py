import asyncio
import logging
from typing import Any, Callable, Dict, List, Type
from pydantic import BaseModel

logger = logging.getLogger("multi_agent.engine")

class EventEngine:
    """Core asynchronous event broker/engine supporting Pub/Sub routing."""

    def __init__(self) -> None:
        self._subscribers: Dict[Type[BaseModel], List[Callable[[Any], asyncio.Future | None]]] = {}
        self._queue: asyncio.Queue[BaseModel] = asyncio.Queue()
        self._running: bool = False
        self._task: Optional[asyncio.Task] = None

    def subscribe(self, event_type: Type[BaseModel], handler: Callable[[Any], Any]) -> None:
        """Register a handler for a specific Pydantic event type."""
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []
        self._subscribers[event_type].append(handler)
        logger.info(f"Subscribed handler {handler.__name__ if hasattr(handler, '__name__') else str(handler)} to {event_type.__name__}")

    async def publish(self, event: BaseModel) -> None:
        """Enqueue an event for distribution to all subscribers."""
        await self._queue.put(event)

    def start(self) -> None:
        """Start the event processing loop."""
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._run_loop())
        logger.info("Event Engine started.")

    async def stop(self) -> None:
        """Stop the event engine and await remaining queue events."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("Event Engine stopped.")

    async def _run_loop(self) -> None:
        """Main event consumer loop."""
        while self._running:
            try:
                event = await self._queue.get()
                event_type = type(event)
                handlers = self._subscribers.get(event_type, [])
                
                # Dispatch concurrently to all matching subscribers
                tasks = []
                for handler in handlers:
                    if asyncio.iscoroutinefunction(handler):
                        tasks.append(asyncio.create_task(handler(event)))
                    else:
                        try:
                            handler(event)
                        except Exception as e:
                            logger.error(f"Error executing sync handler for {event_type.__name__}: {e}", exc_info=True)
                
                if tasks:
                    await asyncio.gather(*tasks, return_exceptions=True)
                
                self._queue.task_done()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Unexpected error in event loop: {e}", exc_info=True)
                await asyncio.sleep(0.1)
