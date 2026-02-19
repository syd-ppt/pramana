"""Tests for hash functions."""

import tempfile
from pathlib import Path

from pramana.hash import hash_output, hash_result, hash_suite


def test_hash_suite_deterministic():
    """Suite hash should be deterministic."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as f:
        f.write('{"id": "test-001", "content": "test"}\n')
        f.write('{"id": "test-002", "content": "test2"}\n')
        path = f.name

    try:
        hash1 = hash_suite(path)
        hash2 = hash_suite(path)
        assert hash1 == hash2
        assert hash1.startswith("sha256:")
    finally:
        Path(path).unlink()


def test_hash_result_deduplication():
    """Same model+test+output should produce same hash."""
    hash1 = hash_result("gpt-4", "test-001", "output text")
    hash2 = hash_result("gpt-4", "test-001", "output text")
    assert hash1 == hash2

    # Different output should produce different hash
    hash3 = hash_result("gpt-4", "test-001", "different output")
    assert hash1 != hash3


def test_hash_output():
    """Output hash should be deterministic."""
    output = "This is a test output"
    hash1 = hash_output(output)
    hash2 = hash_output(output)
    assert hash1 == hash2
    assert hash1.startswith("sha256:")
