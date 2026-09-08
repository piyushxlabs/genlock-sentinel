"""Genlock Sentinel — Typed State, Reducers, and Checkpointing.

Authoritative state models and deterministic reducers per
AGENT_ORCHESTRATION_BLUEPRINT.md Section 3.
"""

from src.state.reducers import (
    STATE_FIELD_REDUCERS,
    reduce_append_only,
    reduce_immutable,
    reduce_last_write_wins,
    reduce_merge_by_key,
    reduce_state,
    reduce_state_batch,
)
from src.state.schema import (
    ApprovalStatus,
    DiagnosisRecord,
    DriftEvent,
    ErrorRecord,
    EvidenceRefs,
    GenlockSentinelState,
    HITLCard,
    RemediationAction,
    RuntimeConfig,
    SessionStatus,
)

__all__ = [
    # State Enums
    "SessionStatus",
    "ApprovalStatus",
    # State Models
    "DriftEvent",
    "EvidenceRefs",
    "DiagnosisRecord",
    "RemediationAction",
    "HITLCard",
    "ErrorRecord",
    "RuntimeConfig",
    "GenlockSentinelState",
    # Reducers
    "reduce_immutable",
    "reduce_last_write_wins",
    "reduce_merge_by_key",
    "reduce_append_only",
    "reduce_state",
    "reduce_state_batch",
    "STATE_FIELD_REDUCERS",
]
