"""Negative Architectural Audit: Confirmation of No Long-Term Memory.

Verifies AGENT_MASTER_PLAN.md Section 1 (Explicit Non-Goals), Section 4 (Step 5),
Section 10 (Step 9), and AGENT_ORCHESTRATION_BLUEPRINT.md Section 7:
  - No vector database dependencies (chromadb, pinecone, qdrant, weaviate, faiss, milvus)
  - No unauthorized third-party orchestrators (langchain, crewai, llama-index)
  - No vector-store clients or long-term memory modules in backend source code
  - GenlockSentinelState strictly contains session-scoped fields only
"""

from pathlib import Path
from typing import Set

import tomllib
from src.state.schema import GenlockSentinelState

PROHIBITED_PACKAGES: Set[str] = {
    "chromadb",
    "pinecone",
    "pinecone-client",
    "qdrant-client",
    "weaviate-client",
    "faiss-cpu",
    "faiss-gpu",
    "pgvector",
    "milvus",
    "pymilvus",
    "langchain",
    "langchain-core",
    "langchain-community",
    "crewai",
    "llama-index",
    "llama-index-core",
    "semantic-kernel",
}


def test_no_vector_store_dependencies_in_manifest() -> None:
    """Verifies backend/pyproject.toml contains zero long-term or vector-store dependencies."""
    backend_dir = Path(__file__).resolve().parent.parent.parent
    pyproject_path = backend_dir / "pyproject.toml"

    assert pyproject_path.exists(), "pyproject.toml must exist"

    with open(pyproject_path, "rb") as f:
        data = tomllib.load(f)

    project_deps = data.get("project", {}).get("dependencies", [])
    optional_deps = data.get("project", {}).get("optional-dependencies", {})

    all_declared_deps = set(project_deps)
    for group in optional_deps.values():
        all_declared_deps.update(group)

    # Normalize package names to lowercase base names
    normalized_declared = {
        dep.split(">")[0].split("=")[0].split("<")[0].split("~")[0].split("[")[0].strip().lower()
        for dep in all_declared_deps
    }

    prohibited_intersection = normalized_declared.intersection(PROHIBITED_PACKAGES)
    assert not prohibited_intersection, (
        f"Constitutional violation: Prohibited vector/long-term memory packages found in pyproject.toml: {prohibited_intersection}"
    )


def test_no_vector_store_imports_in_source_tree() -> None:
    """Scans all Python source files in backend/src/ to ensure no vector store imports exist."""
    backend_dir = Path(__file__).resolve().parent.parent.parent
    src_dir = backend_dir / "src"

    assert src_dir.exists(), "src directory must exist"

    python_files = list(src_dir.rglob("*.py"))
    assert len(python_files) > 0, "Source files must exist"

    for py_file in python_files:
        content = py_file.read_text(encoding="utf-8")
        for prohibited in PROHIBITED_PACKAGES:
            import_patterns = [
                f"import {prohibited}",
                f"from {prohibited}",
            ]
            for pattern in import_patterns:
                assert pattern not in content, (
                    f"Constitutional violation: Found prohibited import '{pattern}' in {py_file}"
                )


def test_state_schema_is_strictly_session_scoped() -> None:
    """Verifies that GenlockSentinelState has exactly the 10 constitutional session fields."""
    expected_fields = {
        "session_id",
        "session_status",
        "active_drift_events",
        "evidence_bundle",
        "diagnosis_history",
        "remediation_log",
        "pending_hitl_card",
        "approval_state",
        "error_logs",
        "config",
    }

    actual_fields = set(GenlockSentinelState.model_fields.keys())
    assert actual_fields == expected_fields, (
        f"State schema field discrepancy. Expected: {expected_fields}, Found: {actual_fields}"
    )

    # Ensure no embedding or vector index fields exist
    for field_name in actual_fields:
        assert "vector" not in field_name.lower()
        assert "embedding" not in field_name.lower()
        assert "memory" not in field_name.lower()
