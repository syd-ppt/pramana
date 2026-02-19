"""Assertion evaluation handlers."""

import json
from typing import Any

from pramana.protocol import Assertion, AssertionResult, AssertionType


def evaluate_assertion(
    assertion: Assertion, output: str, ideal: str | list[str] | None = None
) -> AssertionResult:
    """Evaluate output against assertion criteria."""
    handlers = {
        AssertionType.EXACT_MATCH: _exact_match,
        AssertionType.CONTAINS: _contains,
        AssertionType.CONTAINS_ANY: _contains_any,
        AssertionType.IS_JSON: _is_json,
        AssertionType.LLM_JUDGE: _llm_judge,
        AssertionType.SEMANTIC_SIMILARITY: _semantic_similarity,
    }

    handler = handlers.get(assertion.type)
    if not handler:
        raise ValueError(f"Unknown assertion type: {assertion.type}")

    return handler(assertion, output, ideal)


def _exact_match(
    assertion: Assertion, output: str, ideal: str | list[str] | None,
) -> AssertionResult:
    """Exact string match."""
    if ideal is None:
        raise ValueError("exact_match requires ideal value")

    output_norm = output.strip()
    ideal_norm = ideal.strip() if isinstance(ideal, str) else ideal[0].strip()

    if not assertion.case_sensitive:
        output_norm = output_norm.lower()
        ideal_norm = ideal_norm.lower()

    passed = output_norm == ideal_norm
    return AssertionResult(passed=passed, details={"expected": ideal_norm, "got": output_norm})


def _contains(assertion: Assertion, output: str, ideal: str | list[str] | None) -> AssertionResult:
    """Check if output contains substring."""
    if ideal is None:
        raise ValueError("contains requires ideal value")

    search_term = ideal if isinstance(ideal, str) else ideal[0]
    output_check = output if assertion.case_sensitive else output.lower()
    term_check = search_term if assertion.case_sensitive else search_term.lower()

    passed = term_check in output_check
    return AssertionResult(passed=passed, details={"search_term": search_term})


def _contains_any(
    assertion: Assertion, output: str, ideal: str | list[str] | None,
) -> AssertionResult:
    """Check if output contains any of the provided terms."""
    if ideal is None:
        raise ValueError(f"contains_any requires ideal value (got: {ideal}, type: {type(ideal)})")

    terms = [ideal] if isinstance(ideal, str) else ideal
    output_check = output if assertion.case_sensitive else output.lower()

    for term in terms:
        term_check = term if assertion.case_sensitive else term.lower()
        if term_check in output_check:
            return AssertionResult(passed=True, details={"matched_term": term})

    return AssertionResult(passed=False, details={"terms": terms})


def _is_json(assertion: Assertion, output: str, ideal: Any = None) -> AssertionResult:
    """Check if output is valid JSON."""
    try:
        parsed = json.loads(output.strip())
        return AssertionResult(passed=True, details={"parsed": True, "type": type(parsed).__name__})
    except json.JSONDecodeError as e:
        return AssertionResult(passed=False, details={"error": str(e)})


def _llm_judge(assertion: Assertion, output: str, ideal: Any = None) -> AssertionResult:
    """LLM-based judgment."""
    raise NotImplementedError("llm_judge assertion type is not yet implemented")


def _semantic_similarity(
    assertion: Assertion, output: str, ideal: str | list[str] | None,
) -> AssertionResult:
    """Semantic similarity check."""
    raise NotImplementedError("semantic_similarity assertion type is not yet implemented")
