"""Structured output schema for Node 2: Evidence Triage (Gemini 3.7 Flash).

Per AGENT_LOGIC_SPEC.md Section 5 and AGENT_MASTER_PLAN.md Section 2.
"""

from __future__ import annotations

from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


class EvidenceBundleExtraction(BaseModel):
    """Condensed evidence for one drift event."""

    model_config = ConfigDict(strict=True, extra="forbid")

    event_id: str = Field(
        ..., description="The frame_id/event identifier this evidence covers"
    )
    logs_available: bool = Field(
        ..., description="Whether Loki log evidence was successfully retrieved"
    )
    log_summary: Optional[str] = Field(
        None,
        description="Condensed summary of relevant log findings, citing specific log lines",
    )
    trace_summary: Optional[str] = Field(
        None,
        description="Condensed summary of relevant trace/slow-request findings",
    )
    anomaly: Optional[str] = Field(
        None,
        description="Any data-quality issue or suspected instruction-injection content flagged during triage",
    )
