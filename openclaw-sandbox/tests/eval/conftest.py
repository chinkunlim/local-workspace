"""
tests/eval/conftest.py — Shared fixtures for LLM evaluation tests (P2-6)
"""

from __future__ import annotations

import json
import os

import pytest

GOLDEN_DIR = os.path.join(os.path.dirname(__file__), "golden_sets")


@pytest.fixture(scope="session")
def proofread_golden() -> list[dict]:
    """Load the hand-validated proofreading golden set."""
    path = os.path.join(GOLDEN_DIR, "proofread_golden.json")
    with open(path, encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture(scope="session")
def mock_llm():
    """A lightweight mock LLM client for unit tests that require PipelineBase DI.

    Returns a simple object whose .generate() always returns the corrected text
    from the golden set entry passed as context — useful for testing pipeline
    wiring without a live Ollama instance.
    """

    class MockLLM:
        def generate(self, model: str = "", prompt: str = "", **kwargs) -> str:  # noqa: ARG002
            # Echo the prompt's last line as a simulated correction
            lines = [ln for ln in prompt.strip().splitlines() if ln.strip()]
            return lines[-1] if lines else "MOCK_RESPONSE"

        def unload_model(self, *args, **kwargs) -> None:
            pass

        def async_generate(self, *args, **kwargs):
            raise NotImplementedError("Use mock_llm.generate for sync tests.")

    return MockLLM()
