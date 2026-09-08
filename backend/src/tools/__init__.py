"""Genlock Sentinel — Tool Registrations and Schemas.

Exposes all 9 tools across the three operational tiers:
  - Tools 1–3: Evidence Triage (read-only Grafana/Tempo queries)
  - Tools 4–6: Autonomous Remediation (reversible cluster actions)
  - Tools 7–9: Post-Approval Handling (HITL-gated high-stakes actions)
"""

from src.tools.autonomous_remediation_tools import (
    deprioritize_texture_streaming,
    failover_cluster_leadership,
    force_genlock_resync,
)
from src.tools.evidence_triage_tools import (
    find_slow_requests,
    get_mcp_client,
    get_trace_by_id,
    query_loki_logs,
)
from src.tools.mcp_clients.grafana_mcp_client import GrafanaMCPClient, sanitize_logql
from src.tools.post_approval_tools import (
    execute_threshold_exceeding_failover,
    fallback_to_greenscreen,
    halt_live_take,
)
from src.tools.schemas.mcp_schemas import MCP_TOOL_SCHEMAS
from src.tools.schemas.pydantic_models import (
    FindSlowRequestsInput,
    FindSlowRequestsOutput,
    GetTraceByIdInput,
    GetTraceByIdOutput,
    HitlGatedActionInput,
    HitlGatedActionOutput,
    QueryLokiLogsInput,
    QueryLokiLogsOutput,
    ReversibleRemediationInput,
    ReversibleRemediationOutput,
)

__all__ = [
    # Tools 1–3: Evidence Triage
    "query_loki_logs",
    "find_slow_requests",
    "get_trace_by_id",
    # Tools 4–6: Autonomous Remediation
    "failover_cluster_leadership",
    "deprioritize_texture_streaming",
    "force_genlock_resync",
    # Tools 7–9: Post-Approval Handling
    "halt_live_take",
    "fallback_to_greenscreen",
    "execute_threshold_exceeding_failover",
    # Schemas
    "QueryLokiLogsInput",
    "QueryLokiLogsOutput",
    "FindSlowRequestsInput",
    "FindSlowRequestsOutput",
    "GetTraceByIdInput",
    "GetTraceByIdOutput",
    "ReversibleRemediationInput",
    "ReversibleRemediationOutput",
    "HitlGatedActionInput",
    "HitlGatedActionOutput",
    "MCP_TOOL_SCHEMAS",
    # Clients & Utilities
    "GrafanaMCPClient",
    "get_mcp_client",
    "sanitize_logql",
]
