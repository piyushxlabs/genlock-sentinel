"""7-Node ADK Workflow Runtime Graph Orchestration.

Strictly implements the authoritative 7-node ADK Workflow Runtime graph
topology defined in AGENT_ORCHESTRATION_BLUEPRINT.md Section 4 and
AGENT_MASTER_PLAN.md Section 10 (Step 11):

Node 1: Stream Watch (non-LLM)
  → Node 2: Evidence Triage (Gemini 3.7 Flash)
  → Node 3: Root-Cause Correlation (Gemini 3.1 Pro)
  → Decision Edge:
      [Node 4: Autonomous Remediation Dispatch (deterministic, route="autonomous")
       OR
       Node 5: HITL Card Generation (Gemini 3.7 Flash, route="hitl")
         → Node 6: HITL Pause (ADK Checkpoint Interrupt)
         → Node 7: Post-Approval Handling (deterministic)]
"""

from __future__ import annotations

from typing import Any, AsyncGenerator, Dict, List, Optional

from google.adk import Context, Event
from google.adk.workflow import Edge, FunctionNode, START, Workflow

from src.agents.autonomous_dispatch import autonomous_dispatch_node
from src.agents.evidence_triage import evidence_triage_node
from src.agents.hitl_card_generation import hitl_card_generation_node
from src.agents.post_approval_handling import post_approval_handling_node
from src.agents.root_cause_correlation import root_cause_correlation_node
from src.agents.stream_watch import stream_watch_node
from src.state.schema import ApprovalStatus, GenlockSentinelState


def get_or_init_state(ctx: Context) -> GenlockSentinelState:
    """Safely extracts and reconstructs GenlockSentinelState from Context."""
    raw_state = ctx.state.to_dict() if hasattr(ctx.state, "to_dict") else dict(ctx.state)
    if "session_id" not in raw_state or not raw_state["session_id"]:
        session_id = getattr(getattr(ctx, "session", None), "id", None) or "session-default"
        raw_state["session_id"] = session_id
    return GenlockSentinelState.model_validate(raw_state)


# ------------------------------------------------------------------------------
# Node 6: HITL Pause (Interrupt / Resume Checkpoint)
# ------------------------------------------------------------------------------

async def hitl_pause_node(
    ctx: Context,
    node_input: Optional[Dict[str, Any]] = None,
) -> AsyncGenerator[Event, None]:
    """Node 6: Durable HITL graph interrupt checkpoint.

    Suspends execution with long_running_tool_ids until supervisor Approve/Deny
    is submitted. When resumed with updated approval_state, execution proceeds
    to Node 7 (Post-Approval Handling).
    """
    state = get_or_init_state(ctx)

    if state.approval_state == ApprovalStatus.PENDING or state.approval_state is None:
        card_id = state.pending_hitl_card.card_id if state.pending_hitl_card else "pending_hitl_card"
        yield Event(
            author="node6_hitl_pause",
            long_running_tool_ids=["hitl_supervisor_approval"],
            output={
                "status": "awaiting_supervisor_approval",
                "pending_card_id": card_id,
            },
        )
        return

    # Supervisor has approved or denied -> proceed to Node 7
    yield Event(
        author="node6_hitl_pause",
        output={
            "status": "resumed_from_hitl_pause",
            "approval_state": state.approval_state.value,
        },
    )


# ------------------------------------------------------------------------------
# Node Instantiations
# ------------------------------------------------------------------------------

node1_stream_watch = FunctionNode(
    name="node1_stream_watch",
    func=stream_watch_node,
)

node2_evidence_triage = FunctionNode(
    name="node2_evidence_triage",
    func=evidence_triage_node,
)

node3_root_cause_correlation = FunctionNode(
    name="node3_root_cause_correlation",
    func=root_cause_correlation_node,
)

node4_autonomous_dispatch = FunctionNode(
    name="node4_autonomous_dispatch",
    func=autonomous_dispatch_node,
)

node5_hitl_card_generation = FunctionNode(
    name="node5_hitl_card_generation",
    func=hitl_card_generation_node,
)

node6_hitl_pause = FunctionNode(
    name="node6_hitl_pause",
    func=hitl_pause_node,
)

node7_post_approval_handling = FunctionNode(
    name="node7_post_approval_handling",
    func=post_approval_handling_node,
)


ALL_GRAPH_NODES = [
    node1_stream_watch,
    node2_evidence_triage,
    node3_root_cause_correlation,
    node4_autonomous_dispatch,
    node5_hitl_card_generation,
    node6_hitl_pause,
    node7_post_approval_handling,
]


def create_genlock_workflow_edges() -> List[Edge]:
    """Builds the authoritative 7-node ADK Workflow edge list."""
    return [
        # Ingestion -> Triage -> Reasoning
        Edge(from_node=START, to_node=node1_stream_watch),
        Edge(from_node=node1_stream_watch, to_node=node2_evidence_triage),
        Edge(from_node=node2_evidence_triage, to_node=node3_root_cause_correlation),

        # Decision Edge: Autonomous branch
        Edge(
            from_node=node3_root_cause_correlation,
            to_node=node4_autonomous_dispatch,
            route="autonomous",
        ),

        # Decision Edge: HITL Escalation branch
        Edge(
            from_node=node3_root_cause_correlation,
            to_node=node5_hitl_card_generation,
            route="hitl",
        ),
        Edge(from_node=node5_hitl_card_generation, to_node=node6_hitl_pause),
        Edge(from_node=node6_hitl_pause, to_node=node7_post_approval_handling),
    ]


def create_genlock_workflow(name: str = "genlock_sentinel_workflow") -> Workflow:
    """Instantiates and validates the compiled 7-Node Genlock Sentinel Workflow."""
    return Workflow(
        name=name,
        edges=create_genlock_workflow_edges(),
    )
