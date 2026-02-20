"""Core eval execution logic."""

import json
from datetime import datetime, timezone
from pathlib import Path

from pramana import __version__
from pramana.assertions import evaluate_assertion
from pramana.hash import hash_result, hash_suite
from pramana.protocol import (
    AssertionResult,
    EvalResults,
    RunMetadata,
    RunSummary,
    TestCase,
    TestResult,
)
from pramana.providers.base import BaseProvider


async def run_eval(
    suite_path: Path,
    provider: BaseProvider,
    temperature: float = 0.0,
    seed: int = 42,
) -> EvalResults:
    """Execute eval suite against provider."""
    # Load test cases
    test_cases = []
    for line in suite_path.read_text().strip().split("\n"):
        if line.strip():
            data = json.loads(line)
            test_cases.append(TestCase(**data))

    # Compute suite hash
    suite_hash = hash_suite(suite_path)
    suite_version = f"v1.0-{suite_path.stem}"

    # Run tests
    results = []
    for test_case in test_cases:
        result = await _run_test(test_case, provider, temperature, seed)
        results.append(result)

    # Compute summary
    passed = sum(1 for r in results if r.assertion_result.passed)
    skipped = sum(
        1 for r in results if r.assertion_result.details.get("skipped", False)
    )
    total = len(results)
    scoreable = total - skipped
    summary = RunSummary(
        total=total,
        passed=passed,
        skipped=skipped,
        pass_rate=passed / scoreable if scoreable else 0.0,
    )

    # Create metadata
    metadata = RunMetadata(
        timestamp=datetime.now(timezone.utc),
        model_id=provider.model_id,
        temperature=temperature,
        seed=seed,
        runner_version=__version__,
    )

    return EvalResults(
        suite_version=suite_version,
        suite_hash=suite_hash,
        run_metadata=metadata,
        results=results,
        summary=summary,
    )


async def _run_test(
    test_case: TestCase,
    provider: BaseProvider,
    temperature: float,
    seed: int | None,
) -> TestResult:
    """Execute single test case."""
    # Get input text
    input_text = (
        test_case.input if isinstance(test_case.input, str)
        else test_case.input[0]["content"]
    )

    # Execute completion
    output, latency_ms = await provider.complete(
        input_text=input_text,
        temperature=temperature,
        seed=seed,
    )

    # Evaluate assertion
    try:
        assertion_result = evaluate_assertion(
            assertion=test_case.assertion,
            output=output,
            ideal=test_case.ideal,
        )
    except NotImplementedError as e:
        assertion_result = AssertionResult(
            passed=False,
            details={"skipped": True, "reason": str(e)},
        )
    except Exception as e:
        raise RuntimeError(f"Assertion failed for test {test_case.id}: {e}") from e

    # Compute hash
    result_hash = hash_result(provider.model_id, test_case.id, output)

    return TestResult(
        test_id=test_case.id,
        output=output,
        assertion_result=assertion_result,
        latency_ms=latency_ms,
        result_hash=result_hash,
    )
