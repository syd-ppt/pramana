"""Result submission to API."""

import asyncio
import os

import httpx

from pramana import auth

# Default API endpoint (configurable via PRAMANA_API_URL env var)
DEFAULT_API_URL = "https://pramana-eval.vercel.app"


def get_api_url() -> str:
    """Get API URL from environment or use default."""
    return os.getenv("PRAMANA_API_URL", DEFAULT_API_URL)


def _build_per_result_payloads(results_data: dict) -> list[dict]:
    """Transform EvalResults into per-result payloads matching the API schema.

    The API expects flat per-result objects with top-level model_id,
    prompt_id, and output fields — not the nested EvalResults batch format.
    """
    metadata = results_data.get("run_metadata", {})
    model_id = metadata.get("model_id")
    suite_hash = results_data.get("suite_hash")
    suite_version = results_data.get("suite_version")

    payloads = []
    for result in results_data.get("results", []):
        payloads.append({
            "model_id": model_id,
            "prompt_id": result["test_id"],
            "output": result["output"],
            "assertion_result": result.get("assertion_result"),
            "latency_ms": result.get("latency_ms"),
            "result_hash": result.get("result_hash"),
            "suite_hash": suite_hash,
            "suite_version": suite_version,
            "temperature": metadata.get("temperature"),
            "seed": metadata.get("seed"),
            "runner_version": metadata.get("runner_version"),
            "timestamp": metadata.get("timestamp"),
        })
    return payloads


async def _post_single(
    client: httpx.AsyncClient,
    url: str,
    payload: dict,
    headers: dict,
) -> dict:
    """POST a single result and return parsed response or error detail."""
    response = await client.post(url, json=payload, headers=headers)
    if response.status_code == 422:
        try:
            detail = response.json()
        except Exception:
            detail = response.text
        raise httpx.HTTPStatusError(
            f"422 Unprocessable Entity for prompt_id={payload.get('prompt_id')}: {detail}",
            request=response.request,
            response=response,
        )
    response.raise_for_status()
    return response.json()


async def submit_results(
    results_data: dict, api_url: str | None = None, timeout: float = 30.0,
) -> dict:
    """Submit eval results to Pramana API.

    Transforms the batch EvalResults format into per-result payloads
    and submits each individually to /api/submit.

    Args:
        results_data: Evaluation results (full EvalResults dict)
        api_url: API endpoint (default: PRAMANA_API_URL env var or DEFAULT_API_URL)
        timeout: Request timeout in seconds
    """
    if api_url is None:
        api_url = get_api_url()

    # Build headers
    headers = {"Content-Type": "application/json"}

    # Add auth header if logged in
    auth_header = auth.get_auth_header()
    if auth_header:
        headers.update(auth_header)

    payloads = _build_per_result_payloads(results_data)
    submit_url = f"{api_url}/api/submit"

    semaphore = asyncio.Semaphore(10)

    async def _limited(p: dict) -> dict:
        async with semaphore:
            return await _post_single(client, submit_url, p, headers)

    async with httpx.AsyncClient(timeout=httpx.Timeout(timeout)) as client:
        responses = await asyncio.gather(*[_limited(p) for p in payloads])

    submitted = len(responses)
    duplicates = sum(1 for r in responses if r.get("status") == "duplicate")

    return {
        "status": "duplicate" if duplicates == submitted else "submitted",
        "submitted": submitted,
        "duplicates": duplicates,
    }


async def submit_batch(results: list[dict], api_url: str | None = None) -> list[dict]:
    """Submit multiple result files in sequence.

    Args:
        results: List of EvalResults dicts to submit
        api_url: API endpoint (default: PRAMANA_API_URL env var or DEFAULT_API_URL)
    """
    if api_url is None:
        api_url = get_api_url()

    tasks = [submit_results(result, api_url) for result in results]
    return await asyncio.gather(*tasks)
