"""Genlock Sentinel — Feedback-to-Telemetry Annotation Pipeline.

Per INTERFACE_OBSERVABILITY_SYSTEM.md Section 7a:
  "Route supervisor feedback into the tracing backend chosen in Section 6 as
   structured, queryable annotations, for building an evaluation dataset that can
   check whether the Root-Cause Correlation node's diagnoses hold up against ground
   truth."

Annotation Mapping (verbatim from spec Section 7a table):

  Feedback Signal             | Span            | Score Name          | Value
  ─────────────────────────── | ─────────────── | ─────────────────── | ──────
  diagnosis_correct (thumbs)  | Root-Cause node | diagnosis_accuracy  | 1 or 0
  free-text correction        | Same span       | comment/observation | text
  HITL Approve/Deny           | HITL Pause span | hitl_decision       | approved/denied
  Deny reason (free text)     | Same span       | comment             | text

Write Timing: Immediately on supervisor action — no batching.

Implementation:
  Langfuse accepts OTLP-standard scoring via its REST Scores API
  (POST /api/public/scores). This client writes scores over HTTPX async
  without any langfuse-sdk dependency (pure OTLP-compatible REST call).

Graceful Degradation:
  If Langfuse credentials are missing, all annotation calls are silent no-ops.
  Never raises — annotation failure must never block the critical control path.
"""

from __future__ import annotations

import logging
import os
from typing import Literal, Optional

import httpx
from pydantic import BaseModel, ConfigDict, Field

logger = logging.getLogger(__name__)

# Langfuse REST Scores API endpoint path
_SCORES_PATH = "/api/public/scores"

# Score names per spec Section 7a
SCORE_DIAGNOSIS_ACCURACY = "diagnosis_accuracy"
SCORE_HITL_DECISION = "hitl_decision"


# ------------------------------------------------------------------------------
# Pydantic V2 request schema for the Langfuse Scores API
# ------------------------------------------------------------------------------

class LangfuseScoreRequest(BaseModel):
    """Strict schema for a Langfuse score write (POST /api/public/scores)."""

    model_config = ConfigDict(strict=True, extra="forbid")

    name: str = Field(..., description="Score name (e.g. 'diagnosis_accuracy')")
    value: float = Field(..., description="Numeric value of the score (e.g. 1.0 or 0.0)")
    trace_id: str = Field(..., description="OTel/Langfuse trace ID the score is linked to")
    observation_id: Optional[str] = Field(
        None, description="Span observation ID if targeting a specific node span"
    )
    comment: Optional[str] = Field(
        None, description="Optional free-text annotation (e.g. supervisor deny reason)"
    )
    data_type: Literal["NUMERIC", "BOOLEAN", "CATEGORICAL"] = Field(
        default="NUMERIC", description="Langfuse data type hint"
    )


# ------------------------------------------------------------------------------
# Feedback annotation async client
# ------------------------------------------------------------------------------

class FeedbackAnnotationClient:
    """Async client that writes supervisor feedback scores to Langfuse.

    Thread-safe; uses a shared async HTTPX client (call close() at shutdown).
    All public methods are fire-and-forget: they log errors but never raise.
    """

    def __init__(self) -> None:
        self._base_url = os.environ.get("LANGFUSE_BASE_URL", "https://cloud.langfuse.com").rstrip("/")
        self._public_key = os.environ.get("LANGFUSE_PUBLIC_KEY", "").strip()
        self._secret_key = os.environ.get("LANGFUSE_SECRET_KEY", "").strip()
        self._enabled = bool(self._public_key and self._secret_key)
        self._client: Optional[httpx.AsyncClient] = None

        if not self._enabled:
            logger.warning(
                "FeedbackAnnotationClient: LANGFUSE_PUBLIC_KEY/SECRET_KEY not set — "
                "all feedback annotations will be silently skipped."
            )

    def _get_client(self) -> httpx.AsyncClient:
        """Returns (creating if needed) the shared HTTPX async client."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=self._base_url,
                auth=(self._public_key, self._secret_key),
                timeout=httpx.Timeout(10.0),
                headers={"Content-Type": "application/json"},
            )
        return self._client

    async def _post_score(self, score: LangfuseScoreRequest) -> None:
        """POSTs a single score to the Langfuse Scores API.

        Silently logs on failure — never propagates exceptions.
        """
        if not self._enabled:
            return
        try:
            client = self._get_client()
            response = await client.post(
                _SCORES_PATH,
                content=score.model_dump_json(exclude_none=True),
            )
            response.raise_for_status()
            logger.debug(
                "FeedbackAnnotationClient: Score '%s'=%.1f written for trace_id=%s",
                score.name,
                score.value,
                score.trace_id,
            )
        except httpx.HTTPStatusError as exc:
            logger.error(
                "FeedbackAnnotationClient: HTTP %d writing score '%s': %s",
                exc.response.status_code,
                score.name,
                exc.response.text,
            )
        except Exception as exc:
            logger.error(
                "FeedbackAnnotationClient: Unexpected error writing score '%s': %s",
                score.name,
                exc,
            )

    # --------------------------------------------------------------------------
    # Public annotation methods (per spec Section 7a)
    # --------------------------------------------------------------------------

    async def record_diagnosis_accuracy(
        self,
        trace_id: str,
        observation_id: Optional[str],
        is_correct: bool,
        actual_root_cause: Optional[str] = None,
    ) -> None:
        """Records a post-hoc diagnosis accuracy score from the supervisor thumbs signal.

        Per spec:
          name: "diagnosis_accuracy"
          value: 1 (correct) or 0 (incorrect)
          comment: actual_root_cause if marked incorrect

        Args:
            trace_id:          OTel trace ID of the Root-Cause Correlation span's session.
            observation_id:    Span ID of the Root-Cause Correlation node span.
            is_correct:        True = supervisor confirmed diagnosis; False = incorrect.
            actual_root_cause: Optional free-text correction when is_correct is False.
        """
        score = LangfuseScoreRequest(
            name=SCORE_DIAGNOSIS_ACCURACY,
            value=1.0 if is_correct else 0.0,
            trace_id=trace_id,
            observation_id=observation_id,
            comment=actual_root_cause if not is_correct else None,
            data_type="NUMERIC",
        )
        await self._post_score(score)

        if not is_correct and actual_root_cause:
            logger.info(
                "FeedbackAnnotationClient: Diagnosis marked incorrect — actual_root_cause='%s' "
                "recorded for trace_id=%s",
                actual_root_cause,
                trace_id,
            )

    async def record_hitl_decision(
        self,
        trace_id: str,
        observation_id: Optional[str],
        decision: Literal["approved", "denied"],
        deny_reason: Optional[str] = None,
    ) -> None:
        """Records a HITL supervisor Approve/Deny decision as a Langfuse score.

        Per spec:
          name:  "hitl_decision"
          value: 1 (approved) or 0 (denied)
          comment: deny_reason if provided

        Args:
            trace_id:       OTel trace ID of the HITL Pause span's session.
            observation_id: Span ID of the HITL Pause node span.
            decision:       "approved" or "denied".
            deny_reason:    Optional supervisor explanation on denial.
        """
        score = LangfuseScoreRequest(
            name=SCORE_HITL_DECISION,
            value=1.0 if decision == "approved" else 0.0,
            trace_id=trace_id,
            observation_id=observation_id,
            comment=deny_reason,
            data_type="NUMERIC",
        )
        await self._post_score(score)

    async def close(self) -> None:
        """Closes the underlying HTTPX client. Call at application shutdown."""
        if self._client and not self._client.is_closed:
            try:
                await self._client.aclose()
            except Exception as exc:
                logger.debug("FeedbackAnnotationClient.close(): %s", exc)
            finally:
                self._client = None


# ------------------------------------------------------------------------------
# Module-level singleton accessor
# ------------------------------------------------------------------------------

_feedback_client: Optional[FeedbackAnnotationClient] = None


def get_feedback_client() -> FeedbackAnnotationClient:
    """Returns the process-wide FeedbackAnnotationClient (creates on first call)."""
    global _feedback_client
    if _feedback_client is None:
        _feedback_client = FeedbackAnnotationClient()
    return _feedback_client


async def close_feedback_client() -> None:
    """Closes the process-wide client. Call at process shutdown."""
    global _feedback_client
    if _feedback_client is not None:
        await _feedback_client.close()
        _feedback_client = None
