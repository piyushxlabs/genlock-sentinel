"""Genlock Sentinel — MCP JSON Tool Schemas for All 9 Tools.

Strict Model Context Protocol (MCP) JSON schemas conforming to
AGENT_MASTER_PLAN.md Section 5 and AGENT_LOGIC_SPEC.md Section 3.
"""

from typing import Any, Dict

MCP_TOOL_SCHEMAS: Dict[str, Dict[str, Any]] = {
    # --------------------------------------------------------------------------
    # Tool 1: query_loki_logs
    # --------------------------------------------------------------------------
    "query_loki_logs": {
        "name": "query_loki_logs",
        "description": (
            "Retrieve nDisplay cluster-manager and LogDisplayClusterEngine log lines "
            "for a specific node and frame window from Grafana Loki."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "datasource_uid": {
                    "type": "string",
                    "description": "Grafana Loki datasource UID (e.g. 'loki-stage-01')",
                },
                "logql": {
                    "type": "string",
                    "description": "LogQL query filter expression",
                },
                "start": {
                    "type": "string",
                    "description": "ISO 8601 UTC start timestamp",
                },
                "end": {
                    "type": "string",
                    "description": "ISO 8601 UTC end timestamp",
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of log entries to retrieve",
                    "default": 200,
                },
            },
            "required": ["logql", "start", "end"],
            "additionalProperties": False,
        },
    },

    # --------------------------------------------------------------------------
    # Tool 2: find_slow_requests
    # --------------------------------------------------------------------------
    "find_slow_requests": {
        "name": "find_slow_requests",
        "description": (
            "Detect anomalous or delayed frame-render spans in Tempo trace data "
            "via Grafana Sift investigation."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "service_name": {
                    "type": "string",
                    "description": "Target cluster node service name (e.g. 'render-07')",
                },
                "start": {
                    "type": "string",
                    "description": "ISO 8601 UTC start timestamp",
                },
                "end": {
                    "type": "string",
                    "description": "ISO 8601 UTC end timestamp",
                },
                "min_duration_ms": {
                    "type": "integer",
                    "description": "Minimum span duration in milliseconds to flag",
                    "default": 100,
                },
            },
            "required": ["service_name", "start", "end"],
            "additionalProperties": False,
        },
    },

    # --------------------------------------------------------------------------
    # Tool 3: get_trace_by_id
    # --------------------------------------------------------------------------
    "get_trace_by_id": {
        "name": "get_trace_by_id",
        "description": (
            "Retrieve a complete distributed trace for a known camera frame_id "
            "from Grafana Tempo MCP."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "trace_id": {
                    "type": "string",
                    "description": "Trace identifier matching the active frame_id (e.g. 'f-88213')",
                },
            },
            "required": ["trace_id"],
            "additionalProperties": False,
        },
    },

    # --------------------------------------------------------------------------
    # Tool 4: failover_cluster_leadership
    # --------------------------------------------------------------------------
    "failover_cluster_leadership": {
        "name": "failover_cluster_leadership",
        "description": (
            "Fail cluster leadership over to a healthy standby render node. "
            "Authorized only for network_jitter root causes."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "event_id": {"type": "string", "description": "Active drift event identifier"},
                "node_id": {"type": "string", "description": "Target render node ID"},
                "target_category": {
                    "type": "string",
                    "enum": ["network_jitter"],
                    "description": "Must equal 'network_jitter'",
                },
                "confidence": {
                    "type": "number",
                    "minimum": 0.0,
                    "maximum": 1.0,
                    "description": "Diagnostic confidence score",
                },
                "parameters": {
                    "type": "object",
                    "description": "Optional operational parameters",
                    "additionalProperties": True,
                },
            },
            "required": ["event_id", "node_id", "target_category", "confidence"],
            "additionalProperties": False,
        },
    },

    # --------------------------------------------------------------------------
    # Tool 5: deprioritize_texture_streaming
    # --------------------------------------------------------------------------
    "deprioritize_texture_streaming": {
        "name": "deprioritize_texture_streaming",
        "description": (
            "Deprioritize background texture streaming to resolve asset streaming stalls. "
            "Authorized only for asset_streaming_stall root causes."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "event_id": {"type": "string", "description": "Active drift event identifier"},
                "node_id": {"type": "string", "description": "Target render node ID"},
                "target_category": {
                    "type": "string",
                    "enum": ["asset_streaming_stall"],
                    "description": "Must equal 'asset_streaming_stall'",
                },
                "confidence": {
                    "type": "number",
                    "minimum": 0.0,
                    "maximum": 1.0,
                    "description": "Diagnostic confidence score",
                },
                "parameters": {
                    "type": "object",
                    "description": "Optional operational parameters",
                    "additionalProperties": True,
                },
            },
            "required": ["event_id", "node_id", "target_category", "confidence"],
            "additionalProperties": False,
        },
    },

    # --------------------------------------------------------------------------
    # Tool 6: force_genlock_resync
    # --------------------------------------------------------------------------
    "force_genlock_resync": {
        "name": "force_genlock_resync",
        "description": (
            "Force an immediate genlock hardware re-sync handshake on the drifting node. "
            "Authorized only for thermal_throttle root causes."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "event_id": {"type": "string", "description": "Active drift event identifier"},
                "node_id": {"type": "string", "description": "Target render node ID"},
                "target_category": {
                    "type": "string",
                    "enum": ["thermal_throttle"],
                    "description": "Must equal 'thermal_throttle'",
                },
                "confidence": {
                    "type": "number",
                    "minimum": 0.0,
                    "maximum": 1.0,
                    "description": "Diagnostic confidence score",
                },
                "parameters": {
                    "type": "object",
                    "description": "Optional operational parameters",
                    "additionalProperties": True,
                },
            },
            "required": ["event_id", "node_id", "target_category", "confidence"],
            "additionalProperties": False,
        },
    },

    # --------------------------------------------------------------------------
    # Tool 7: halt_live_take
    # --------------------------------------------------------------------------
    "halt_live_take": {
        "name": "halt_live_take",
        "description": (
            "Halt the active camera take on the virtual production stage. "
            "Strictly HITL-gated: requires explicit supervisor approval."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "event_id": {"type": "string", "description": "Active drift event identifier"},
                "hitl_card_id": {"type": "string", "description": "ID of the approved HITL card"},
                "approval_state": {
                    "type": "string",
                    "enum": ["approved"],
                    "description": "Must equal 'approved'",
                },
                "node_id": {"type": "string", "description": "Target render node ID"},
                "parameters": {
                    "type": "object",
                    "description": "Optional stage parameters",
                    "additionalProperties": True,
                },
            },
            "required": ["event_id", "hitl_card_id", "approval_state"],
            "additionalProperties": False,
        },
    },

    # --------------------------------------------------------------------------
    # Tool 8: fallback_to_greenscreen
    # --------------------------------------------------------------------------
    "fallback_to_greenscreen": {
        "name": "fallback_to_greenscreen",
        "description": (
            "Switch the LED volume walls to uniform chromakey greenscreen. "
            "Strictly HITL-gated: requires explicit supervisor approval."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "event_id": {"type": "string", "description": "Active drift event identifier"},
                "hitl_card_id": {"type": "string", "description": "ID of the approved HITL card"},
                "approval_state": {
                    "type": "string",
                    "enum": ["approved"],
                    "description": "Must equal 'approved'",
                },
                "node_id": {"type": "string", "description": "Target render node ID"},
                "parameters": {
                    "type": "object",
                    "description": "Optional stage parameters",
                    "additionalProperties": True,
                },
            },
            "required": ["event_id", "hitl_card_id", "approval_state"],
            "additionalProperties": False,
        },
    },

    # --------------------------------------------------------------------------
    # Tool 9: execute_threshold_exceeding_failover
    # --------------------------------------------------------------------------
    "execute_threshold_exceeding_failover": {
        "name": "execute_threshold_exceeding_failover",
        "description": (
            "Trigger a multi-node or cloud failover exceeding pre-approved financial limits. "
            "Strictly HITL-gated: requires explicit supervisor approval."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "event_id": {"type": "string", "description": "Active drift event identifier"},
                "hitl_card_id": {"type": "string", "description": "ID of the approved HITL card"},
                "approval_state": {
                    "type": "string",
                    "enum": ["approved"],
                    "description": "Must equal 'approved'",
                },
                "node_id": {"type": "string", "description": "Target render node ID"},
                "parameters": {
                    "type": "object",
                    "description": "Optional stage parameters",
                    "additionalProperties": True,
                },
            },
            "required": ["event_id", "hitl_card_id", "approval_state"],
            "additionalProperties": False,
        },
    },
}
