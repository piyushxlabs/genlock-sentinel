"""Genlock Sentinel — Typed State, Reducers, and Checkpointing.

Authoritative state models, deterministic reducers, and checkpointing per
AGENT_ORCHESTRATION_BLUEPRINT.md Section 3 and AGENT_MASTER_PLAN.md Section 4 & 10.
"""

from src.state.checkpointing import (
    create_session_service,
    delete_checkpoint,
    get_database_url,
    init_checkpoint_db,
    list_checkpoints,
    load_checkpoint,
    save_checkpoint,
)
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
    # Checkpointing
    "get_database_url",
    "create_session_service",
    "init_checkpoint_db",
    "save_checkpoint",
    "load_checkpoint",
    "delete_checkpoint",
    "list_checkpoints",
]
