"""Genlock Sentinel — Google Model Armor Security Client.

Provides automated input/output sanitization per AGENT_MASTER_PLAN.md Section 8,
AGENT_LOGIC_SPEC.md Section 10, and OWASP Top 10 for LLM Applications 2025:
- OWASP LLM01: Prompt Injection & Instruction Overrides in untrusted telemetry.
- OWASP LLM02: Sensitive Information & Credential Disclosure.
"""

from __future__ import annotations

import os
import re
from typing import Any, Dict, List, Literal, Optional, Tuple

from pydantic import BaseModel, ConfigDict, Field


class SanitizationFinding(BaseModel):
    """Specific security or policy finding emitted by Model Armor."""

    model_config = ConfigDict(strict=True, extra="forbid")

    rule_name: str = Field(..., description="Name of the triggered safety rule")
    category: Literal["prompt_injection", "pii", "credential_leakage", "harmful_content"] = Field(
        ..., description="Threat classification category"
    )
    severity: Literal["low", "medium", "high", "critical"] = Field(
        ..., description="Assessed severity level"
    )
    message: str = Field(..., description="Human-readable description of the finding")


class SanitizationResult(BaseModel):
    """Result of prompt or tool output sanitization."""

    model_config = ConfigDict(strict=True, extra="forbid")

    original_text: str
    sanitized_text: str
    is_blocked: bool = False
    findings: List[SanitizationFinding] = Field(default_factory=list)


# ------------------------------------------------------------------------------
# Threat Pattern Definitions (OWASP LLM01 & LLM02)
# ------------------------------------------------------------------------------

PROMPT_INJECTION_RULES = [
    (
        "ignore_instructions",
        re.compile(r"ignore\s+(all\s+|previous\s+|prior\s+)?instructions", re.IGNORECASE),
        "prompt_injection",
        "critical",
        "Attempt to override prior or system instructions detected.",
    ),
    (
        "system_prompt_override",
        re.compile(r"system\s*prompt\s*override", re.IGNORECASE),
        "prompt_injection",
        "critical",
        "System prompt override directive detected in telemetry payload.",
    ),
    (
        "developer_mode_jailbreak",
        re.compile(r"you\s+are\s+now\s+in\s+(developer|dan|jailbreak)\s+mode", re.IGNORECASE),
        "prompt_injection",
        "critical",
        "Jailbreak or persona override attempt detected.",
    ),
    (
        "admin_override",
        re.compile(r"admin\s+(override|mode|access|bypass)", re.IGNORECASE),
        "prompt_injection",
        "high",
        "Privileged administrative override syntax detected.",
    ),
    (
        "force_approval_command",
        re.compile(r"approve\s+(all\s+actions|immediately|override)", re.IGNORECASE),
        "prompt_injection",
        "high",
        "Malicious imperative command seeking automatic tool approval.",
    ),
    (
        "malicious_execution_directive",
        re.compile(r"execute\s+(halt_live_take|fallback_to_greenscreen|failover)", re.IGNORECASE),
        "prompt_injection",
        "critical",
        "Malicious execution directive attempting actuator hijack in telemetry.",
    ),
]

CREDENTIAL_LEAKAGE_RULES = [
    (
        "grafana_service_token",
        re.compile(r"glsa_[A-Za-z0-9_\-]{20,}", re.IGNORECASE),
        "credential_leakage",
        "critical",
        "Raw Grafana service account token detected.",
    ),
    (
        "langfuse_api_key",
        re.compile(r"[ps]k-lf-[A-Za-z0-9_\-]{20,}", re.IGNORECASE),
        "credential_leakage",
        "critical",
        "Raw Langfuse telemetry key detected.",
    ),
    (
        "generic_bearer_token",
        re.compile(r"Bearer\s+[A-Za-z0-9_\-\.]{25,}", re.IGNORECASE),
        "credential_leakage",
        "critical",
        "Raw HTTP Bearer authorization token detected.",
    ),
    (
        "private_key_block",
        re.compile(r"-----BEGIN\s+[A-Z ]*PRIVATE\s+KEY-----", re.IGNORECASE),
        "credential_leakage",
        "critical",
        "Cryptographic private key header detected.",
    ),
    (
        "database_password_uri",
        re.compile(r"://[^:]+:([^@]+)@", re.IGNORECASE),
        "credential_leakage",
        "high",
        "Database password embedded in connection URI detected.",
    ),
]


class ModelArmorClient:
    """Google Model Armor security client with offline rule-based fallbacks."""

    def __init__(
        self,
        project_id: Optional[str] = None,
        location: Optional[str] = None,
        template_id: Optional[str] = None,
    ) -> None:
        self.project_id = project_id or os.environ.get("GOOGLE_CLOUD_PROJECT", "genlock-sentinel-dev")
        self.location = location or os.environ.get("GOOGLE_CLOUD_LOCATION", "us-central1")
        self.template_id = template_id or "genlock-sentinel-guardrails"

    def sanitize_text(self, text: str) -> SanitizationResult:
        """Sanitizes text against prompt injection and sensitive credential leakage.

        Employs offline rule-based inspection matching Google Model Armor templates.
        """
        if not text:
            return SanitizationResult(original_text="", sanitized_text="", is_blocked=False, findings=[])

        sanitized = text
        findings: List[SanitizationFinding] = []
        is_blocked = False

        # 1. Screen for prompt-injection attacks (OWASP LLM01)
        for rule_name, pattern, category, severity, message in PROMPT_INJECTION_RULES:
            if pattern.search(sanitized):
                findings.append(
                    SanitizationFinding(
                        rule_name=rule_name,
                        category=category,
                        severity=severity,
                        message=message,
                    )
                )
                sanitized = pattern.sub(f"[MODEL_ARMOR_REDACTED:{rule_name.upper()}]", sanitized)
                if severity == "critical":
                    is_blocked = True

        # 2. Screen for credential & secret leakage (OWASP LLM02)
        for rule_name, pattern, category, severity, message in CREDENTIAL_LEAKAGE_RULES:
            if pattern.search(sanitized):
                findings.append(
                    SanitizationFinding(
                        rule_name=rule_name,
                        category=category,
                        severity=severity,
                        message=message,
                    )
                )
                sanitized = pattern.sub("[MODEL_ARMOR_SECRET_REDACTED]", sanitized)
                is_blocked = True

        return SanitizationResult(
            original_text=text,
            sanitized_text=sanitized,
            is_blocked=is_blocked,
            findings=findings,
        )

    def sanitize_tool_response(
        self,
        tool_name: str,
        payload: Any,
    ) -> Tuple[Any, List[SanitizationFinding], bool]:
        """Recursively inspects and sanitizes MCP tool response data before Gemini ingestion."""
        findings: List[SanitizationFinding] = []
        is_blocked = False

        def _clean_item(item: Any) -> Any:
            nonlocal is_blocked
            if isinstance(item, str):
                res = self.sanitize_text(item)
                if res.findings:
                    findings.extend(res.findings)
                if res.is_blocked:
                    is_blocked = True
                return res.sanitized_text
            elif isinstance(item, dict):
                return {k: _clean_item(v) for k, v in item.items()}
            elif isinstance(item, list):
                return [_clean_item(v) for v in item]
            return item

        sanitized_payload = _clean_item(payload)
        return sanitized_payload, findings, is_blocked


_DEFAULT_MODEL_ARMOR_CLIENT: Optional[ModelArmorClient] = None


def get_model_armor_client() -> ModelArmorClient:
    """Returns the singleton ModelArmorClient instance."""
    global _DEFAULT_MODEL_ARMOR_CLIENT
    if _DEFAULT_MODEL_ARMOR_CLIENT is None:
        _DEFAULT_MODEL_ARMOR_CLIENT = ModelArmorClient()
    return _DEFAULT_MODEL_ARMOR_CLIENT
