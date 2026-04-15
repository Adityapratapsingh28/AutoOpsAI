"""
AutoOps AI — Base Tool.

Abstract base class for all tools in the platform.
Every tool must implement: run(input_data, context) -> dict

Provides a shared `_run_async()` helper that safely executes async DB
operations from within sync tool code, whether there's a running event
loop (FastAPI/Uvicorn) or not.
"""

import asyncio
import logging
from abc import ABC, abstractmethod
from typing import Any, Dict

logger = logging.getLogger("autoops.tools.base")


class BaseTool(ABC):
    """Abstract base class for AutoOps tools."""

    name: str = "base_tool"
    description: str = "Base tool"

    @abstractmethod
    def run(self, input_data: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute the tool.

        Args:
            input_data: Tool-specific input data
            context: Execution context (workflow info, user info, event_loop, etc.)

        Returns:
            Dictionary with at minimum: {"status": "...", ...}
        """
        raise NotImplementedError

    @staticmethod
    def _run_async(coro, context: Dict[str, Any] = None, timeout: float = 15.0):
        """Safely run an async coroutine from sync tool code.

        Handles three scenarios:
          1. An event loop reference is passed via context["event_loop"]
             → uses run_coroutine_threadsafe (safest for FastAPI)
          2. An event loop is currently running (but not passed)
             → uses run_coroutine_threadsafe with get_running_loop()
          3. No event loop is running
             → creates a temporary one (testing / CLI context)

        Args:
            coro: The awaitable coroutine to execute.
            context: Optional context dict that may contain "event_loop".
            timeout: Max seconds to wait for the result.

        Returns:
            The result of the coroutine.
        """
        context = context or {}

        # Try 1: Loop from context (explicitly passed by orchestrator_service)
        loop = context.get("event_loop")
        if loop and loop.is_running():
            future = asyncio.run_coroutine_threadsafe(coro, loop)
            return future.result(timeout=timeout)

        # Try 2: Running loop in current thread
        try:
            loop = asyncio.get_running_loop()
            future = asyncio.run_coroutine_threadsafe(coro, loop)
            return future.result(timeout=timeout)
        except RuntimeError:
            pass

        # Try 3: No loop running — create a temporary one
        loop = asyncio.new_event_loop()
        try:
            return loop.run_until_complete(coro)
        finally:
            loop.close()
