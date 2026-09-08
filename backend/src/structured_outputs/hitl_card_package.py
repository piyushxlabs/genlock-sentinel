"""Structured output schema for Node 5: HITL Card Generation (Gemini 3.7 Flash).

Per AGENT_LOGIC_SPEC.md Section 5 and AGENT_MASTER_PLAN.md Section 2.
"""

from __future__ import annotations

from typing import Literal
from pydantic import BaseModel, ConfigDict, Field


class HITLCardPackage(BaseModel):
    """Structured HITL approval card."""

    model_config = ConfigDict(strict=True, extra="forbid")

    event_id: str = Field(
        ..., description="The frame_id/event identifier this card covers"
    )
    escalation_reason: Literal[
        "ambiguous_diagnosis",
        "take_halt_required",
        "capture_fallback_required",
        "threshold_exceeded",
    ] = Field(..., description="Why this event requires human approval")
    proposed_action: str = Field(
        ...,
        description="The action being proposed for approval, or 'none' if the diagnosis itself is ambiguous",
    )
    cost_delta_estimate: str = Field(
        ...,
        description="Estimated cost impact of the proposed action or continued drift",
    )
    visual_impact_score: str = Field(
        ..., description="Qualitative assessment of on-camera visual risk"
    )
    root_cause_summary: str = Field(
        ..., description="Plain-language summary of the diagnosis and evidence"
    )
