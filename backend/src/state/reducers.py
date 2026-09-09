"""Genlock Sentinel — State Reducers and Mutation Dispatcher.

Implements the deterministic reducers declared in AGENT_ORCHESTRATION_BLUEPRINT.md Section 3:
  - active_drift_events: merge-by-key (keyed by node_id)
  - evidence_bundle: merge-by-key (keyed by event_id)
  - diagnosis_history: append-only
  - remediation_log: append-only
  - error_logs: append-only
  - pending_hitl_card: last-write-wins
  - approval_state: last-write-wins
  - session_status: last-write-wins
  - session_id: immutable-after-init
  - config: immutable-after-init

All state transitions must pass through these reducers.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Dict, List, Mapping, Optional, Sequence, TypeVar, Union

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
from src.utils.errors import StateValidationError

T = TypeVar("T")
K = TypeVar("K")
V = TypeVar("V")


# ------------------------------------------------------------------------------
# Pure Functional Reducer Primitives
# ------------------------------------------------------------------------------

def reduce_immutable(current_val: T, new_val: T, field_name: str) -> T:
    """Enforces immutable-after-init semantics.

    Raises StateValidationError if an attempt is made to alter the field
    once initialized.
    """
    if current_val is not None and new_val is not None:
        if current_val != new_val:
            raise StateValidationError(
                f"Field '{field_name}' is immutable after initialization and cannot be mutated "
                f"(current: {current_val!r}, attempted: {new_val!r})."
            )
        return current_val
    return new_val if current_val is None else current_val


def reduce_last_write_wins(current_val: Optional[T], new_val: Optional[T]) -> Optional[T]:
    """Enforces last-write-wins semantics."""
    return new_val


def reduce_merge_by_key(
    current_dict: Mapping[K, V],
    update_dict: Mapping[K, Optional[V]],
) -> Dict[K, V]:
    """Enforces merge-by-key semantics.

    Preserves existing keys while non-destructively inserting or updating
    keys present in update_dict. If an incoming key maps to None, the key is removed.
    """
    merged: Dict[K, V] = dict(current_dict)
    for k, v in update_dict.items():
        if v is None:
            merged.pop(k, None)
        else:
            merged[k] = v
    return merged



def reduce_append_only(
    current_list: Sequence[T],
    new_items: Union[T, Sequence[T]],
) -> List[T]:
    """Enforces append-only semantics.

    Appends single items or appends a sequence of new items to the audit trail.
    Existing entries can never be modified or removed.
    """
    merged: List[T] = list(current_list)
    if isinstance(new_items, (list, tuple)):
        merged.extend(new_items)
    else:
        merged.append(new_items)
    return merged


# ------------------------------------------------------------------------------
# State-Level Mutation Reducer Dispatcher
# ------------------------------------------------------------------------------

STATE_FIELD_REDUCERS = {
    "session_id": "immutable",
    "config": "immutable",
    "session_status": "last_write_wins",
    "pending_hitl_card": "last_write_wins",
    "approval_state": "last_write_wins",
    "active_drift_events": "merge_by_key",
    "evidence_bundle": "merge_by_key",
    "diagnosis_history": "append_only",
    "remediation_log": "append_only",
    "error_logs": "append_only",
}


def reduce_state(
    current_state: GenlockSentinelState,
    delta: Dict[str, Any],
) -> GenlockSentinelState:
    """Atomically applies a state delta through declared reducers.

    Strictly forbids undeclared fields and enforces domain-specific invariant
    checks per AGENT_ORCHESTRATION_BLUEPRINT.md Section 3.
    """
    # Verify no undeclared / unauthorized fields in delta
    for key in delta:
        if key not in STATE_FIELD_REDUCERS:
            raise StateValidationError(
                f"Unauthorized state field '{key}' in state delta. Allowed fields: {list(STATE_FIELD_REDUCERS.keys())}"
            )

    # 1. Immutable fields
    session_id = current_state.session_id
    if "session_id" in delta:
        session_id = reduce_immutable(current_state.session_id, delta["session_id"], "session_id")

    config = current_state.config
    if "config" in delta:
        new_config = delta["config"]
        if isinstance(new_config, dict):
            new_config = RuntimeConfig.model_validate(new_config)
        config = reduce_immutable(current_state.config, new_config, "config")

    # 2. Last-write-wins fields
    session_status = current_state.session_status
    if "session_status" in delta:
        raw_status = delta["session_status"]
        if isinstance(raw_status, str):
            raw_status = SessionStatus(raw_status)
        session_status = reduce_last_write_wins(current_state.session_status, raw_status)

    pending_hitl_card = current_state.pending_hitl_card
    if "pending_hitl_card" in delta:
        raw_card = delta["pending_hitl_card"]
        if isinstance(raw_card, dict):
            raw_card = HITLCard.model_validate(raw_card)
        pending_hitl_card = reduce_last_write_wins(current_state.pending_hitl_card, raw_card)

    approval_state = current_state.approval_state
    if "approval_state" in delta:
        raw_approval = delta["approval_state"]
        if isinstance(raw_approval, str):
            raw_approval = ApprovalStatus(raw_approval)
        approval_state = reduce_last_write_wins(current_state.approval_state, raw_approval)

    # 3. Merge-by-key fields
    active_drift_events = current_state.active_drift_events
    if "active_drift_events" in delta:
        raw_events = delta["active_drift_events"]
        validated_events: Dict[str, Optional[DriftEvent]] = {}
        for node_id, event_val in raw_events.items():
            if event_val is None:
                validated_events[node_id] = None
            elif isinstance(event_val, dict):
                validated_events[node_id] = DriftEvent.model_validate(event_val)
            elif isinstance(event_val, DriftEvent):
                validated_events[node_id] = event_val
            else:
                raise StateValidationError(f"Invalid DriftEvent type for node {node_id}: {type(event_val)}")
        active_drift_events = reduce_merge_by_key(current_state.active_drift_events, validated_events)

    evidence_bundle = current_state.evidence_bundle
    if "evidence_bundle" in delta:
        raw_evidence = delta["evidence_bundle"]
        validated_evidence: Dict[str, Optional[EvidenceRefs]] = {}
        for event_id, ev_val in raw_evidence.items():
            if ev_val is None:
                validated_evidence[event_id] = None
            elif isinstance(ev_val, dict):
                validated_evidence[event_id] = EvidenceRefs.model_validate(ev_val)
            elif isinstance(ev_val, EvidenceRefs):
                validated_evidence[event_id] = ev_val
            else:
                raise StateValidationError(f"Invalid EvidenceRefs type for event {event_id}: {type(ev_val)}")
        evidence_bundle = reduce_merge_by_key(current_state.evidence_bundle, validated_evidence)


    # 4. Append-only fields
    diagnosis_history = current_state.diagnosis_history
    if "diagnosis_history" in delta:
        raw_diag = delta["diagnosis_history"]
        raw_diag_list = raw_diag if isinstance(raw_diag, (list, tuple)) else [raw_diag]
        validated_diag: List[DiagnosisRecord] = []
        for item in raw_diag_list:
            if isinstance(item, dict):
                validated_diag.append(DiagnosisRecord.model_validate(item))
            elif isinstance(item, DiagnosisRecord):
                validated_diag.append(item)
            else:
                raise StateValidationError(f"Invalid DiagnosisRecord type: {type(item)}")
        diagnosis_history = reduce_append_only(current_state.diagnosis_history, validated_diag)

    remediation_log = current_state.remediation_log
    if "remediation_log" in delta:
        raw_rem = delta["remediation_log"]
        raw_rem_list = raw_rem if isinstance(raw_rem, (list, tuple)) else [raw_rem]
        validated_rem: List[RemediationAction] = []
        for item in raw_rem_list:
            if isinstance(item, dict):
                validated_rem.append(RemediationAction.model_validate(item))
            elif isinstance(item, RemediationAction):
                validated_rem.append(item)
            else:
                raise StateValidationError(f"Invalid RemediationAction type: {type(item)}")
        remediation_log = reduce_append_only(current_state.remediation_log, validated_rem)

    error_logs = current_state.error_logs
    if "error_logs" in delta:
        raw_err = delta["error_logs"]
        raw_err_list = raw_err if isinstance(raw_err, (list, tuple)) else [raw_err]
        validated_err: List[ErrorRecord] = []
        for item in raw_err_list:
            if isinstance(item, dict):
                validated_err.append(ErrorRecord.model_validate(item))
            elif isinstance(item, ErrorRecord):
                validated_err.append(item)
            else:
                raise StateValidationError(f"Invalid ErrorRecord type: {type(item)}")
        error_logs = reduce_append_only(current_state.error_logs, validated_err)

    # Reconstruct new validated state instance
    return GenlockSentinelState(
        session_id=session_id,
        session_status=session_status,
        active_drift_events=active_drift_events,
        evidence_bundle=evidence_bundle,
        diagnosis_history=diagnosis_history,
        remediation_log=remediation_log,
        pending_hitl_card=pending_hitl_card,
        approval_state=approval_state,
        error_logs=error_logs,
        config=config,
    )


def reduce_state_batch(
    initial_state: GenlockSentinelState,
    deltas: Sequence[Dict[str, Any]],
) -> GenlockSentinelState:
    """Sequentially applies a sequence of deltas through reduce_state."""
    current = initial_state
    for delta in deltas:
        current = reduce_state(current, delta)
    return current
