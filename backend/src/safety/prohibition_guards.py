"""Genlock Sentinel — Structural Prohibition Guards & Precondition Verifiers.

Enforces constitutional non-capabilities and pre-condition invariants per
AGENT_BEHAVIOR_PROFILE.md Section 6, AGENT_LOGIC_SPEC.md Section 10, and
AGENT_MASTER_PLAN.md Section 8:
1. Constitutional Non-Capabilities: Refuses creative generation, cluster administration,
   cast/crew messaging, and post-production video editing.
2. Tool Dispatch Invariants:
   - HITL-gated actions (Tools 7–9) require approval_state == "approved" and matching card ID.
   - Reversible actions (Tools 4–6) require confidence >= floor and category match.
   - No actions on ambiguous diagnosis.
   - No actions when session is terminated or in error.
3. Sensitive Information & Credential Protection (OWASP LLM02).
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

from src.safety.model_armor_client import get_model_armor_client
from src.state.schema import ApprovalStatus, GenlockSentinelState, SessionStatus
from src.utils.errors import StateValidationError, ToolExecutionError

# ------------------------------------------------------------------------------
# Constitutional Non-Capabilities & Prohibited Request Patterns
# ------------------------------------------------------------------------------

PROHIBITED_INTENT_PATTERNS = {
    "creative_generation": re.compile(
        r"(generate|write|create|draft)\s+(a\s+|an\s+)?(script|screenplay|concept\s*art|storyboard|video|image|dialogue)",
        re.IGNORECASE,
    ),
    "general_cluster_administration": re.compile(
        r"(delete|drain|cordon|scale|restart)\s+(kubernetes|k8s|pod|deployment|daemonset|namespace)",
        re.IGNORECASE,
    ),
    "cast_crew_communication": re.compile(
        r"(send|notify|message|email|slack|discord|sms|text).*?\b(cast|crew|director|actor|dp|cinematographer)",
        re.IGNORECASE,
    ),
    "post_production_editing": re.compile(
        r"(color\s*grade|lut|edit\s*timeline|premiere|davinci|export\s*exr|render\s*final)",
        re.IGNORECASE,
    ),
}

# Remediation tools to required diagnostic category mapping
REVERSIBLE_TOOL_CATEGORY_MAP = {
    "failover_cluster_leadership": "network_jitter",
    "deprioritize_texture_streaming": "asset_streaming_stall",
    "force_genlock_resync": "thermal_throttle",
}

HITL_GATED_TOOLS = {
    "halt_live_take",
    "fallback_to_greenscreen",
    "execute_threshold_exceeding_failover",
}


def validate_in_scope_request(intent: str) -> None:
    """Verifies that an incoming intent does not violate constitutional non-capabilities.

    Raises ToolExecutionError if intent requests out-of-scope capabilities.
    """
    if not intent:
        return

    for category, pattern in PROHIBITED_INTENT_PATTERNS.items():
        if pattern.search(intent):
            raise ToolExecutionError(
                f"Request classified as '{category}' is unconstitutional and strictly outside "
                f"Genlock Sentinel's scope (ICVFX frame-sync SRE only)."
            )


def validate_tool_dispatch_preconditions(
    tool_name: str,
    parameters: Dict[str, Any],
    state: GenlockSentinelState,
) -> None:
    """Programmatically enforces state invariants and trust boundaries before tool execution."""
    # 1. Session Lifecycle Boundary (Constraint 5)
    if state.session_status in (SessionStatus.FAILED, SessionStatus.STOPPED):
        raise ToolExecutionError(
            f"Cannot execute tool '{tool_name}': session '{state.session_id}' is in terminal '{state.session_status.value}' status."
        )

    # 2. HITL-Gated Actions Verification (Constraint 1)
    if tool_name in HITL_GATED_TOOLS:
        if state.approval_state != ApprovalStatus.APPROVED:
            raise ToolExecutionError(
                f"HITL-gated tool '{tool_name}' requires approval_state == 'approved', "
                f"found '{state.approval_state}'."
            )
        if state.pending_hitl_card is None:
            raise StateValidationError(
                f"HITL-gated tool '{tool_name}' requires active pending_hitl_card in state."
            )

        card = state.pending_hitl_card
        hitl_card_id = parameters.get("hitl_card_id")
        if hitl_card_id not in (card.card_id, card.event_id):
            raise StateValidationError(
                f"HITL card ID mismatch: parameter hitl_card_id='{hitl_card_id}' does not match "
                f"pending card '{card.card_id}'."
            )

        if card.proposed_action != tool_name:
            raise ToolExecutionError(
                f"Proposed action mismatch: pending card specifies '{card.proposed_action}', "
                f"cannot execute '{tool_name}'."
            )
        return

    # 3. Reversible Remediation Actions Verification (Constraint 4)
    if tool_name in REVERSIBLE_TOOL_CATEGORY_MAP:
        required_category = REVERSIBLE_TOOL_CATEGORY_MAP[tool_name]

        if not state.diagnosis_history:
            raise ToolExecutionError(
                f"Cannot execute remediation tool '{tool_name}': diagnosis_history is empty."
            )

        latest_diag = state.diagnosis_history[-1]
        diag_cat = getattr(latest_diag, "category", None) or (latest_diag.get("category") if isinstance(latest_diag, dict) else None)
        diag_conf = getattr(latest_diag, "confidence", 0.0) if hasattr(latest_diag, "confidence") else (latest_diag.get("confidence", 0.0) if isinstance(latest_diag, dict) else 0.0)

        if diag_cat == "ambiguous":
            raise ToolExecutionError(
                f"Cannot execute autonomous tool '{tool_name}': latest diagnosis is ambiguous."
            )

        if diag_cat != required_category:
            raise ToolExecutionError(
                f"Diagnosis category mismatch: tool '{tool_name}' requires category '{required_category}', "
                f"found '{diag_cat}'."
            )

        if diag_conf < state.config.confidence_floor:
            raise ToolExecutionError(
                f"Confidence floor violation: tool '{tool_name}' requires confidence >= "
                f"{state.config.confidence_floor}, found {diag_conf}."
            )


def screen_state_for_sensitive_leakage(state_data: Dict[str, Any]) -> None:
    """Recursively scans state dictionary for credentials or secrets (OWASP LLM02).

    Raises StateValidationError if any secret is discovered in state.
    """
    model_armor = get_model_armor_client()

    def _inspect(data: Any, path: str = "") -> None:
        if isinstance(data, str):
            res = model_armor.sanitize_text(data)
            for finding in res.findings:
                if finding.category == "credential_leakage":
                    raise StateValidationError(
                        f"Sensitive credential leakage detected in state at '{path}': {finding.message}"
                    )
        elif isinstance(data, dict):
            for k, v in data.items():
                _inspect(v, f"{path}.{k}" if path else k)
        elif isinstance(data, (list, tuple)):
            for idx, item in enumerate(data):
                _inspect(item, f"{path}[{idx}]")

    _inspect(state_data)


def screen_hitl_card_for_sensitive_leakage(card_package: Dict[str, Any]) -> Dict[str, Any]:
    """Sanitizes draft HITLCardPackage to ensure zero secrets or topology details leak to supervisor UI."""
    model_armor = get_model_armor_client()
    sanitized_package, _, _ = model_armor.sanitize_tool_response("hitl_card_package", card_package)
    return sanitized_package
