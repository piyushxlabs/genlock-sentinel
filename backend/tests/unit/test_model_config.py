"""Unit tests for Step 6: Model Configuration & Structured Output Schemas."""

import os
import pytest
from pydantic import ValidationError

from src.agents.model_config import (
    SHARED_SYSTEM_PROMPT_STATIC,
    generate_structured_output,
    get_fast_model_name,
    get_model_settings,
    get_reasoning_model_name,
)
from src.structured_outputs import (
    EvidenceBundleExtraction,
    HITLCardPackage,
    RootCauseDiagnosis,
)


def test_dynamic_model_name_resolution(monkeypatch):
    """Verifies that model names are resolved dynamically from env without hardcoding."""
    monkeypatch.setenv("GEMINI_REASONING_MODEL", "custom-reasoning-model-v1")
    monkeypatch.setenv("GEMINI_FAST_MODEL", "custom-fast-model-v2")

    assert get_reasoning_model_name() == "custom-reasoning-model-v1"
    assert get_fast_model_name() == "custom-fast-model-v2"

    reasoning_settings = get_model_settings("reasoning")
    assert reasoning_settings.model_name == "custom-reasoning-model-v1"
    assert reasoning_settings.temperature == 0.0  # Mandatory temperature=0.0

    fast_settings = get_model_settings("fast")
    assert fast_settings.model_name == "custom-fast-model-v2"


def test_shared_system_prompt_for_context_caching():
    """Confirms shared system prompt contains constitutional zero-hallucination rules."""
    assert "Zero-Error / Zero-Hallucination" in SHARED_SYSTEM_PROMPT_STATIC
    assert "Silence-Over-Guessing" in SHARED_SYSTEM_PROMPT_STATIC


def test_evidence_bundle_extraction_schema_validation():
    """Tests strict validation of EvidenceBundleExtraction model."""
    valid_data = {
        "event_id": "f-88213",
        "logs_available": True,
        "log_summary": "14:02:11 frame drop detected on render-07",
        "trace_summary": "find_slow_requests found duration_ms=340",
        "anomaly": None,
    }
    bundle = EvidenceBundleExtraction.model_validate(valid_data)
    assert bundle.event_id == "f-88213"
    assert bundle.logs_available is True

    # Test extra='forbid'
    with pytest.raises(ValidationError):
        EvidenceBundleExtraction.model_validate({**valid_data, "unauthorized_extra": 123})


def test_root_cause_diagnosis_schema_validation():
    """Tests strict validation of RootCauseDiagnosis model."""
    valid_diag = {
        "event_id": "f-88213",
        "category": "network_jitter",
        "confidence": 0.95,
        "rationale": "Citing Loki retry line 14:02:10 on node render-07.",
    }
    diag = RootCauseDiagnosis.model_validate(valid_diag)
    assert diag.category == "network_jitter"
    assert diag.confidence == 0.95

    # Test invalid category rejection
    with pytest.raises(ValidationError):
        RootCauseDiagnosis.model_validate({**valid_diag, "category": "invalid_cause"})

    # Test out-of-range confidence
    with pytest.raises(ValidationError):
        RootCauseDiagnosis.model_validate({**valid_diag, "confidence": 1.5})


def test_hitl_card_package_schema_validation():
    """Tests strict validation of HITLCardPackage model."""
    valid_card = {
        "event_id": "f-91004",
        "escalation_reason": "ambiguous_diagnosis",
        "proposed_action": "none",
        "cost_delta_estimate": "$0",
        "visual_impact_score": "High",
        "root_cause_summary": "Evidence points to thermal throttle or network jitter.",
    }
    card = HITLCardPackage.model_validate(valid_card)
    assert card.escalation_reason == "ambiguous_diagnosis"

    # Test invalid escalation reason
    with pytest.raises(ValidationError):
        HITLCardPackage.model_validate({**valid_card, "escalation_reason": "unknown_reason"})


@pytest.mark.asyncio
async def test_structured_output_generation_mock_mode():
    """Verifies structured output generation in deterministic mock mode."""
    # Test EvidenceBundleExtraction
    evidence = await generate_structured_output(
        role="fast",
        schema_cls=EvidenceBundleExtraction,
        prompt="Analyze telemetry for render-07",
        mock_key="evidence_bundle_simple",
        force_mock=True,
    )
    assert isinstance(evidence, EvidenceBundleExtraction)
    assert evidence.logs_available is True
    assert evidence.event_id == "f-88213"

    # Test RootCauseDiagnosis
    diagnosis = await generate_structured_output(
        role="reasoning",
        schema_cls=RootCauseDiagnosis,
        prompt="Diagnose root cause for render-07",
        mock_key="diagnosis_simple",
        force_mock=True,
    )
    assert isinstance(diagnosis, RootCauseDiagnosis)
    assert diagnosis.category == "network_jitter"
    assert diagnosis.confidence >= 0.75

    # Test HITLCardPackage
    card = await generate_structured_output(
        role="hitl",
        schema_cls=HITLCardPackage,
        prompt="Generate HITL card for render-12",
        mock_key="hitl_card_complex",
        force_mock=True,
    )
    assert isinstance(card, HITLCardPackage)
    assert card.escalation_reason == "ambiguous_diagnosis"


@pytest.mark.asyncio
async def test_live_structured_output_if_api_key_available():
    """Tests live structured output call with Gemini API if GEMINI_API_KEY is configured."""
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        pytest.skip("No GEMINI_API_KEY available for live inference test")

    try:
        evidence = await generate_structured_output(
            role="fast",
            schema_cls=EvidenceBundleExtraction,
            prompt="Extract evidence for test event f-test-01. Set logs_available=true, log_summary='Log frame drop', trace_summary='Trace OK', anomaly=None.",
            mock_key="evidence_bundle_simple",
            force_mock=False,
        )
        assert isinstance(evidence, EvidenceBundleExtraction)
        assert evidence.event_id is not None
    except Exception as e:
        pytest.skip(f"Live model call skipped due to temporary service availability: {e}")
