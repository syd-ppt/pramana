"""Tests for assertion evaluation."""


from pramana.assertions import evaluate_assertion
from pramana.protocol import Assertion, AssertionType


def test_exact_match():
    """Test exact match assertion."""
    assertion = Assertion(type=AssertionType.EXACT_MATCH)

    # Pass
    result = evaluate_assertion(assertion, "42", "42")
    assert result.passed

    # Fail
    result = evaluate_assertion(assertion, "42", "43")
    assert not result.passed


def test_exact_match_case_insensitive():
    """Test case-insensitive exact match."""
    assertion = Assertion(type=AssertionType.EXACT_MATCH, case_sensitive=False)

    result = evaluate_assertion(assertion, "SUCCESS", "success")
    assert result.passed


def test_contains():
    """Test contains assertion."""
    assertion = Assertion(type=AssertionType.CONTAINS)

    result = evaluate_assertion(assertion, "The answer is 42", "42")
    assert result.passed

    result = evaluate_assertion(assertion, "The answer is 42", "43")
    assert not result.passed


def test_contains_any():
    """Test contains_any assertion."""
    assertion = Assertion(type=AssertionType.CONTAINS_ANY, case_sensitive=False)

    result = evaluate_assertion(assertion, "Paris is the capital", ["Paris", "London"])
    assert result.passed

    result = evaluate_assertion(assertion, "Paris is the capital", ["London", "Berlin"])
    assert not result.passed


def test_is_json():
    """Test is_json assertion."""
    assertion = Assertion(type=AssertionType.IS_JSON)

    result = evaluate_assertion(assertion, '{"status": "ok"}', None)
    assert result.passed

    result = evaluate_assertion(assertion, "not json", None)
    assert not result.passed
