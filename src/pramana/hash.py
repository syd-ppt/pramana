"""Content-addressable hashing for suites and results."""

import hashlib
import json
from pathlib import Path


def hash_suite(jsonl_path: str | Path) -> str:
    """Compute SHA-256 hash of a test suite.

    Canonical hash based on sorted test case IDs and content.
    Ensures suite versioning is deterministic.
    """
    lines = Path(jsonl_path).read_text().strip().split("\n")
    test_cases = [json.loads(line) for line in lines if line.strip()]

    # Sort by ID for canonical ordering
    test_cases.sort(key=lambda x: x["id"])

    # Canonical JSON (sorted keys, no whitespace)
    canonical = json.dumps(test_cases, sort_keys=True, separators=(",", ":"))

    hash_obj = hashlib.sha256(canonical.encode("utf-8"))
    return f"sha256:{hash_obj.hexdigest()}"


def hash_result(model_id: str, test_id: str, output: str) -> str:
    """Compute deduplication hash for a test result.

    Same model + test + output = duplicate submission.
    """
    content = f"{model_id}|{test_id}|{output}"
    hash_obj = hashlib.sha256(content.encode("utf-8"))
    return f"sha256:{hash_obj.hexdigest()}"


def hash_output(output: str) -> str:
    """Compute hash of output text only."""
    hash_obj = hashlib.sha256(output.encode("utf-8"))
    return f"sha256:{hash_obj.hexdigest()}"
