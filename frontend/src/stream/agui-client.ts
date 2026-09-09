/**
 * Genlock Sentinel — AG-UI SSE Streaming Client Runtime.
 *
 * Implements persistent SSE connection handling, initial state snapshot resync,
 * RFC 6902 JSON Patch application, and typed event dispatching per
 * AGENT_MASTER_PLAN.md Section 7 and INTERFACE_OBSERVABILITY_SYSTEM.md Section 2 & 2a.
 */

export interface DriftEvent {
  event_id: string;
  node_id: string;
  timestamp: string;
  sync_offset_us: number;
  severity: "nominal" | "warning" | "critical";
  status: string;
}

export interface EvidenceBundle {
  event_id: string;
  logs_available: boolean;
  log_summary: string;
  trace_summary: string;
  anomaly?: string | null;
}

export interface DiagnosisRecord {
  event_id: string;
  category: "network_jitter" | "thermal_throttle" | "asset_streaming_stall" | "ambiguous";
  confidence: number;
  rationale: string;
  node_id?: string;
  timestamp: string;
}

export interface HITLCard {
  card_id: string;
  event_id: string;
  node_id: string;
  escalation_reason: "ambiguous_diagnosis" | "take_halt_required" | "capture_fallback_required" | "threshold_exceeded";
  proposed_action: "halt_live_take" | "fallback_to_greenscreen" | "execute_threshold_exceeding_failover" | string;
  cost_delta_estimate: string;
  visual_impact_score: string;
  root_cause_summary: string;
  created_at: string;
}

export interface RemediationAction {
  action_id: string;
  event_id: string;
  node_id: string;
  action_taken: string;
  timestamp: string;
  success: boolean;
  details?: Record<string, any>;
}

export interface ErrorRecord {
  timestamp: string;
  event_id?: string | null;
  node_id?: string | null;
  error_type: string;
  message: string;
}

export interface GenlockState {
  session_id: string;
  session_status: "monitoring" | "awaiting_approval" | "resumed" | "stopped";
  approval_state: "pending" | "approved" | "denied" | "halted" | null;
  active_drift_events: Record<string, DriftEvent>;
  evidence_bundle: Record<string, EvidenceBundle>;
  diagnosis_history: DiagnosisRecord[];
  pending_hitl_card: HITLCard | null;
  remediation_log: RemediationAction[];
  error_logs: ErrorRecord[];
}

export interface SyncOffsetSample {
  node_id: string;
  sync_offset_us: number;
  threshold_us: number;
  timestamp: string;
}

export interface StepEvent {
  type: "STEP_STARTED" | "STEP_FINISHED";
  step_name:
    | "stream_watch"
    | "evidence_triage"
    | "root_cause_correlation"
    | "autonomous_dispatch"
    | "hitl_card_generation"
    | "hitl_pause"
    | "post_approval_handling";
  event_id: string;
}

export interface ToolCallEvent {
  type: "TOOL_CALL_START" | "TOOL_CALL_ARGS" | "TOOL_CALL_END" | "TOOL_CALL_RESULT";
  toolCallId: string;
  toolCallName?: string;
  delta?: string;
  content?: string;
}

export interface ReasoningEvent {
  type: "REASONING_START" | "REASONING_MESSAGE_START" | "REASONING_MESSAGE_CONTENT" | "REASONING_MESSAGE_END" | "REASONING_END";
  messageId?: string;
  delta?: string;
}

export interface RunEvent {
  type: "RUN_STARTED" | "RUN_PAUSED" | "RUN_FINISHED" | "RUN_ERROR";
  runId?: string;
  threadId?: string;
  reason?: string;
  message?: string;
  code?: string;
}

export interface StateDeltaOp {
  op: "add" | "replace" | "remove";
  path: string;
  value?: any;
}

export interface StateDeltaEvent {
  type: "STATE_DELTA";
  delta: StateDeltaOp[];
}

export interface StateSnapshotEvent {
  type: "STATE_SNAPSHOT";
  session_id: string;
  state: Partial<GenlockState>;
}

export type AGUIStreamEvent =
  | RunEvent
  | StepEvent
  | ToolCallEvent
  | ReasoningEvent
  | StateDeltaEvent
  | StateSnapshotEvent
  | ({ type: "SYNC_OFFSET_SAMPLE" } & SyncOffsetSample);

export type StateListener = (state: GenlockState) => void;
export type TelemetryListener = (sample: SyncOffsetSample) => void;
export type StepListener = (event: StepEvent) => void;
export type ReasoningListener = (delta: string) => void;
export type ErrorListener = (message: string, code: string) => void;

/**
 * Applies RFC 6902 JSON Patch operations to the in-memory GenlockState replica.
 */
export function applyStateDelta(state: GenlockState, ops: StateDeltaOp[]): GenlockState {
  const next = { ...state };

  for (const op of ops) {
    const segments = op.path.replace(/^\//, "").split("/");
    const field = segments[0] as keyof GenlockState;

    if (!field) continue;

    if (op.op === "replace") {
      (next as any)[field] = op.value;
    } else if (op.op === "add") {
      if (segments.length === 2 && segments[1] === "-") {
        // Append-only array reducer
        const currentArr = Array.isArray(next[field]) ? (next[field] as any[]) : [];
        (next as any)[field] = [...currentArr, op.value];
      } else if (segments.length === 2) {
        // Merge-by-key dictionary reducer
        const key = segments[1];
        const currentObj = (next[field] as Record<string, any>) || {};
        (next as any)[field] = { ...currentObj, [key]: op.value };
      } else {
        (next as any)[field] = op.value;
      }
    } else if (op.op === "remove") {
      if (segments.length === 2) {
        const key = segments[1];
        const currentObj = { ...((next[field] as Record<string, any>) || {}) };
        delete currentObj[key];
        (next as any)[field] = currentObj;
      } else {
        (next as any)[field] = null;
      }
    }
  }

  return next;
}

export class AGUIStreamingClient {
  private eventSource: EventSource | null = null;
  private sessionId: string;
  private stateListeners: Set<StateListener> = new Set();
  private telemetryListeners: Set<TelemetryListener> = new Set();
  private stepListeners: Set<StepListener> = new Set();
  private reasoningListeners: Set<ReasoningListener> = new Set();
  private errorListeners: Set<ErrorListener> = new Set();

  private currentState: GenlockState;

  constructor(sessionId: string) {
    this.sessionId = sessionId;
    this.currentState = {
      session_id: sessionId,
      session_status: "monitoring",
      approval_state: null,
      active_drift_events: {},
      evidence_bundle: {},
      diagnosis_history: [],
      pending_hitl_card: null,
      remediation_log: [],
      error_logs: [],
    };
  }

  public getState(): GenlockState {
    return this.currentState;
  }

  public onStateChange(listener: StateListener): () => void {
    this.stateListeners.add(listener);
    listener(this.currentState);
    return () => this.stateListeners.delete(listener);
  }

  public onTelemetry(listener: TelemetryListener): () => void {
    this.telemetryListeners.add(listener);
    return () => this.telemetryListeners.delete(listener);
  }

  public onStep(listener: StepListener): () => void {
    this.stepListeners.add(listener);
    return () => this.stepListeners.delete(listener);
  }

  public onReasoning(listener: ReasoningListener): () => void {
    this.reasoningListeners.add(listener);
    return () => this.reasoningListeners.delete(listener);
  }

  public onError(listener: ErrorListener): () => void {
    this.errorListeners.add(listener);
    return () => this.errorListeners.delete(listener);
  }

  public connect(): void {
    if (this.eventSource) {
      this.eventSource.close();
    }

    const streamUrl = `/sessions/${this.sessionId}/stream`;
    this.eventSource = new EventSource(streamUrl);

    this.eventSource.onmessage = (evt) => {
      try {
        const raw = evt.data?.trim();
        if (!raw || raw.startsWith(":")) return;

        const event: AGUIStreamEvent = JSON.parse(raw);
        this.handleEvent(event);
      } catch (err) {
        console.warn("[AG-UI] Error parsing stream event frame:", err);
      }
    };

    this.eventSource.onerror = (err) => {
      console.warn("[AG-UI] SSE stream connection interrupted. Browser reconnecting automatically:", err);
    };
  }

  public disconnect(): void {
    if (this.eventSource) {
      this.eventSource.close();
      this.eventSource = null;
    }
  }

  public handleEvent(event: AGUIStreamEvent): void {
    switch (event.type) {
      case "STATE_SNAPSHOT": {
        this.currentState = {
          ...this.currentState,
          ...(event.state as any),
        };
        this.notifyState();
        break;
      }
      case "STATE_DELTA": {
        this.currentState = applyStateDelta(this.currentState, event.delta);
        this.notifyState();
        break;
      }
      case "SYNC_OFFSET_SAMPLE": {
        for (const l of this.telemetryListeners) {
          l(event);
        }
        break;
      }
      case "STEP_STARTED":
      case "STEP_FINISHED": {
        for (const l of this.stepListeners) {
          l(event);
        }
        break;
      }
      case "REASONING_MESSAGE_CONTENT": {
        if (event.delta) {
          for (const l of this.reasoningListeners) {
            l(event.delta);
          }
        }
        break;
      }
      case "RUN_ERROR": {
        if (event.message) {
          for (const l of this.errorListeners) {
            l(event.message, event.code || "RUNTIME_ERROR");
          }
        }
        break;
      }
      case "RUN_PAUSED": {
        // Paused state will be reflected in STATE_DELTA pending_hitl_card / session_status
        break;
      }
      default:
        break;
    }
  }

  private notifyState(): void {
    for (const listener of this.stateListeners) {
      listener(this.currentState);
    }
  }
}
