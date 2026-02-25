"""Core eval execution logic."""

from __future__ import annotations

import json
from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path

from pramana import __version__
from pramana.assertions import evaluate_assertion
from pramana.hash import hash_result, hash_suite
from pramana.protocol import (
    AssertionResult,
    AssertionType,
    EvalResults,
    RunMetadata,
    RunSummary,
    TestCase,
    TestResult,
)
from pramana.providers.base import BaseProvider


def load_suite(suite_path: Path) -> tuple[list[TestCase], str, str]:
    """Load test cases and compute suite metadata.

    Returns:
        (test_cases, suite_hash, suite_version)
    """
    test_cases = []
    for line in suite_path.read_text().strip().split("\n"):
        if line.strip():
            data = json.loads(line)
            test_cases.append(TestCase(**data))

    suite_hash = hash_suite(suite_path)
    suite_version = f"v1.0-{suite_path.stem}"
    return test_cases, suite_hash, suite_version


async def run_eval(
    suite_path: Path,
    provider: BaseProvider,
    temperature: float = 0.0,
    seed: int = 42,
    on_progress: Callable[[int, int, TestResult], None] | None = None,
) -> EvalResults:
    """Execute eval suite against provider."""
    test_cases, suite_hash, suite_version = load_suite(suite_path)

    # Run tests
    total = len(test_cases)
    results = []
    for i, test_case in enumerate(test_cases):
        result = await _run_test(test_case, provider, temperature, seed)
        results.append(result)
        if on_progress is not None:
            on_progress(i + 1, total, result)

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
        if test_case.assertion.type == AssertionType.LLM_JUDGE:
            assertion_result = await _evaluate_llm_judge(
                test_case=test_case,
                output=output,
                provider=provider,
            )
        else:
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

    # Compute score: 1.0=passed, 0.0=failed, None=skipped
    skipped = assertion_result.details.get("skipped", False)
    score: float | None = None if skipped else (1.0 if assertion_result.passed else 0.0)

    return TestResult(
        test_id=test_case.id,
        output=output,
        assertion_result=assertion_result,
        latency_ms=latency_ms,
        result_hash=result_hash,
        score=score,
    )


_JUDGE_SYSTEM_PROMPT = (
    "You are an evaluation judge. Given a model output and a question about it, "
    "respond with ONLY 'YES' or 'NO'. Do not explain."
)


async def _evaluate_llm_judge(
    test_case: TestCase,
    output: str,
    provider: BaseProvider,
) -> AssertionResult:
    """Evaluate output using LLM as judge."""
    judge_prompt = test_case.assertion.judge_prompt
    if not judge_prompt:
        raise ValueError(f"llm_judge requires judge_prompt for test {test_case.id}")

    prompt = f"Model output:\n{output}\n\nQuestion: {judge_prompt}"

    judge_response, _ = await provider.complete(
        input_text=prompt,
        system_prompt=_JUDGE_SYSTEM_PROMPT,
        temperature=0.0,
        seed=42,
    )

    verdict = judge_response.strip().upper()
    passed = verdict.startswith("YES")

    return AssertionResult(
        passed=passed,
        details={"judge_prompt": judge_prompt, "judge_verdict": verdict},
    )
