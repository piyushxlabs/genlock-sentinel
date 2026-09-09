"""Genlock Sentinel — Custom Exception Hierarchy.

Strict exception hierarchy per defensive-execution-structured-outputs-and-fallbacks.md.
Bare try-except blocks are forbidden; all agent errors derive from AgentError.
"""

from __future__ import annotations

from typing import Any, Dict, Optional


class AgentError(Exception):
    """Base exception for all Genlock Sentinel errors."""

    def __init__(
        self,
        message: str,
        event_id: Optional[str] = None,
        node_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.event_id = event_id
        self.node_id = node_id
        self.details = details or {}


class StateValidationError(AgentError):
    """Raised when a state invariant, reducer constraint, or immutability rule is violated."""
    pass


class ToolExecutionError(AgentError):
    """Raised when an MCP or external cluster tool execution fails after retries."""
    pass


class SafetyViolationError(AgentError):
    """Raised when an input prompt injection or prohibited action is detected."""
    pass


class CircuitBreakerTrippedError(AgentError):
    """Raised when node failure counts exceed threshold in a rolling window."""
    pass


class PostApprovalExecutionError(ToolExecutionError):
    """Raised when post-approval dispatch or validation fails."""
    pass

