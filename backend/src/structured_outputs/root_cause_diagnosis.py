"""Structured output schema for Node 3: Root-Cause Correlation (Gemini 3.1 Pro).

Per AGENT_LOGIC_SPEC.md Section 5 and AGENT_MASTER_PLAN.md Section 2.
"""

from __future__ import annotations

from typing import Literal
from pydantic import BaseModel, ConfigDict, Field


class RootCauseDiagnosis(BaseModel):
    """Root-cause classification for one drift event."""

    model_config = ConfigDict(strict=True, extra="forbid")

    event_id: str = Field(
        ..., description="The frame_id/event identifier this diagnosis covers"
    )
    category: Literal[
        "network_jitter",
        "thermal_throttle",
        "asset_streaming_stall",
        "ambiguous",
    ] = Field(
        ...,
        description="The diagnosed category, or ambiguous if none fits confidently",
    )
    confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Model's confidence in this classification",
    )
    rationale: str = Field(
        ...,
        description="Evidence-grounded explanation citing specific evidence_bundle fields",
    )
