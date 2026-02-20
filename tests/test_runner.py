"""Tests for runner module."""

import json
from pathlib import Path

import pytest

from pramana.providers.base import BaseProvider
from pramana.runner import run_eval


class MockProvider(BaseProvider):
    """Test provider that returns canned responses."""

    def __init__(self, responses: dict[str, str] | None = None):
        self.model_id = "mock-model"
        self._responses = responses or {}
        self._default_response = "42"

    async def complete(
        self,
        input_text: str,
        system_prompt: str | None = None,
        temperature: float = 0.0,
        seed: int | None = None,
    ) -> tuple[str, int]:
        output = self._responses.get(input_text, self._default_response)
        return output, 100

    def estimate_tokens(self, text: str) -> int:
        return len(text) // 4


def _make_suite(tmp_path: Path, test_cases: list[dict]) -> Path:
    """Write test cases to a JSONL file."""
    suite_file = tmp_path / "test_suite.jsonl"
    lines = [json.dumps(tc) for tc in test_cases]
    suite_file.write_text("\n".join(lines))
    return suite_file


@pytest.fixture
def basic_test_cases():
    """Two passing test cases with exact_match."""
    return [
        {
            "id": "test-001",
            "category": "reasoning",
            "input": "What is 2+2?",
            "ideal": "42",
            "assertion": {"type": "exact_match", "case_sensitive": False},
            "metadata": {"difficulty": "easy", "tokens_est": 10},
        },
        {
            "id": "test-002",
            "category": "factual",
            "input": "Capital of France?",
            "ideal": "Paris",
            "assertion": {"type": "contains", "case_sensitive": False},
            "metadata": {"difficulty": "easy", "tokens_est": 10},
        },
    ]


@pytest.mark.asyncio
async def test_run_eval_all_pass(tmp_path, basic_test_cases):
    """All tests pass with correct responses."""
    suite = _make_suite(tmp_path, basic_test_cases)
    provider = MockProvider(responses={
        "What is 2+2?": "42",
        "Capital of France?": "The capital is Paris.",
    })

    results = await run_eval(suite, provider)

    assert results.summary.total == 2
    assert results.summary.passed == 2
    assert results.summary.skipped == 0
    assert results.summary.pass_rate == 1.0
    assert results.run_metadata.model_id == "mock-model"
    assert results.suite_hash.startswith("sha256:")


@pytest.mark.asyncio
async def test_run_eval_mixed_results(tmp_path, basic_test_cases):
    """Some tests pass, some fail."""
    suite = _make_suite(tmp_path, basic_test_cases)
    provider = MockProvider(responses={
        "What is 2+2?": "wrong answer",
        "Capital of France?": "The capital is Paris.",
    })

    results = await run_eval(suite, provider)

    assert results.summary.total == 2
    assert results.summary.passed == 1
    assert results.summary.pass_rate == 0.5


@pytest.mark.asyncio
async def test_run_eval_skipped_not_implemented(tmp_path):
    """NotImplementedError assertions are skipped, not crashed."""
    test_cases = [
        {
            "id": "test-001",
            "category": "reasoning",
            "input": "What is 2+2?",
            "ideal": "42",
            "assertion": {"type": "exact_match", "case_sensitive": False},
            "metadata": {"difficulty": "easy", "tokens_est": 10},
        },
        {
            "id": "test-llm",
            "category": "creative",
            "input": "Write a haiku",
            "ideal": None,
            "assertion": {
                "type": "llm_judge",
                "judge_prompt": "Is this a haiku?",
            },
            "metadata": {"difficulty": "medium", "tokens_est": 50},
        },
    ]
    suite = _make_suite(tmp_path, test_cases)
    provider = MockProvider(responses={
        "What is 2+2?": "42",
        "Write a haiku": "cherry blossoms fall / gently on the stream / spring",
    })

    results = await run_eval(suite, provider)

    assert results.summary.total == 2
    assert results.summary.passed == 1
    assert results.summary.skipped == 1
    # pass_rate is calculated against scoreable (non-skipped) tests
    assert results.summary.pass_rate == 1.0

    # Verify the skipped test has correct details
    llm_result = [r for r in results.results if r.test_id == "test-llm"][0]
    assert llm_result.assertion_result.passed is False
    assert llm_result.assertion_result.details["skipped"] is True
    assert "not yet implemented" in llm_result.assertion_result.details["reason"]


@pytest.mark.asyncio
async def test_run_eval_empty_suite(tmp_path):
    """Empty suite produces zero results."""
    suite_file = tmp_path / "empty.jsonl"
    suite_file.write_text("")
    provider = MockProvider()

    results = await run_eval(suite_file, provider)

    assert results.summary.total == 0
    assert results.summary.passed == 0
    assert results.summary.pass_rate == 0.0


@pytest.mark.asyncio
async def test_run_eval_suite_hash_deterministic(tmp_path, basic_test_cases):
    """Same suite content produces same hash."""
    suite1 = _make_suite(tmp_path, basic_test_cases)
    provider = MockProvider()

    results1 = await run_eval(suite1, provider)

    # Recreate suite with same content
    suite2 = tmp_path / "test_suite2.jsonl"
    lines = [json.dumps(tc) for tc in basic_test_cases]
    suite2.write_text("\n".join(lines))

    results2 = await run_eval(suite2, provider)

    assert results1.suite_hash == results2.suite_hash
