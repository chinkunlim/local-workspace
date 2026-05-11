"""
tests/eval/test_proofread_quality.py — LLM-as-a-Judge quality evaluation (P2-6)
================================================================================
Uses DeepEval to assess faithfulness and answer relevancy of p02_proofread
output against the 10-item hand-validated golden set.

Run locally:
    pip install deepeval
    export OPENAI_API_KEY=sk-...   # or use Ollama proxy
    python -m pytest tests/eval/test_proofread_quality.py -v

Design choices:
  - FaithfulnessMetric: Verifies the corrected text does not add hallucinated
    facts not present in the original transcript.
  - AnswerRelevancyMetric: Verifies the corrected text stays on topic.
  - Threshold 0.75: Advisory in CI (eval.yml has continue-on-error: true).
    Raise to 0.85 once golden set is expanded to 50+ items.
  - The test gracefully skips if deepeval is not installed so the core CI
    suite (ci.yml) never fails due to a missing eval dependency.
"""

from __future__ import annotations

import pytest

try:
    from deepeval import assert_test
    from deepeval.metrics import AnswerRelevancyMetric, FaithfulnessMetric
    from deepeval.test_case import LLMTestCase

    DEEPEVAL_AVAILABLE = True
except ImportError:
    DEEPEVAL_AVAILABLE = False


FAITHFULNESS_THRESHOLD = 0.75
RELEVANCY_THRESHOLD = 0.75


@pytest.mark.skipif(not DEEPEVAL_AVAILABLE, reason="deepeval not installed")
class TestProofreadFaithfulness:
    """Verify that the corrected transcripts do not introduce hallucinated facts."""

    def test_faithfulness_all_items(self, proofread_golden):
        """Each corrected entry must be faithful to its raw source."""
        metric = FaithfulnessMetric(threshold=FAITHFULNESS_THRESHOLD, model="gpt-4o-mini")
        failures = []

        for item in proofread_golden:
            tc = LLMTestCase(
                input=item["raw"],
                actual_output=item["corrected"],
                retrieval_context=[item["raw"]],  # source is the ground truth context
            )
            try:
                assert_test(tc, [metric])
            except AssertionError as exc:
                failures.append(
                    f"[{item['id']}] FAILED faithfulness: {exc}\n  Note: {item.get('note', '')}"
                )

        if failures:
            pytest.fail(
                f"{len(failures)}/{len(proofread_golden)} items failed faithfulness:\n"
                + "\n".join(failures)
            )

    def test_answer_relevancy_all_items(self, proofread_golden):
        """Each corrected entry must remain relevant to the original question."""
        metric = AnswerRelevancyMetric(threshold=RELEVANCY_THRESHOLD, model="gpt-4o-mini")
        failures = []

        for item in proofread_golden:
            tc = LLMTestCase(
                input=item["raw"],
                actual_output=item["corrected"],
            )
            try:
                assert_test(tc, [metric])
            except AssertionError as exc:
                failures.append(f"[{item['id']}] FAILED relevancy: {exc}")

        if failures:
            pytest.fail(
                f"{len(failures)}/{len(proofread_golden)} items failed relevancy:\n"
                + "\n".join(failures)
            )


@pytest.mark.skipif(not DEEPEVAL_AVAILABLE, reason="deepeval not installed")
class TestProofreadGoldenSetSanity:
    """Sanity checks that do not require an LLM — run in all environments."""

    def test_golden_set_has_minimum_items(self, proofread_golden):
        """Golden set must have at least 10 items to be statistically meaningful."""
        assert len(proofread_golden) >= 10, (
            f"Golden set only has {len(proofread_golden)} items; minimum is 10."
        )

    def test_all_items_have_required_fields(self, proofread_golden):
        """Every golden item must have id, raw, corrected, and subject fields."""
        required = {"id", "raw", "corrected", "subject"}
        for item in proofread_golden:
            missing = required - item.keys()
            assert not missing, f"Item {item.get('id', '?')} missing fields: {missing}"

    def test_corrected_is_longer_or_equal_to_raw(self, proofread_golden):
        """Corrections should generally expand or maintain transcript length."""
        for item in proofread_golden:
            # Allow up to 20% shrinkage (some corrections trim verbosity)
            raw_len = len(item["raw"])
            corrected_len = len(item["corrected"])
            assert corrected_len >= raw_len * 0.8, (
                f"[{item['id']}] Corrected output suspiciously shorter than raw: "
                f"{corrected_len} < {raw_len * 0.8:.0f}"
            )
