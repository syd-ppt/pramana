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


async def submit_results(
    results_data: dict, api_url: str | None = None, timeout: float = 30.0,
) -> dict:
    """Submit eval results to Pramana API.

    Args:
        results_data: Evaluation results to submit
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

    async with httpx.AsyncClient(timeout=httpx.Timeout(timeout)) as client:
        response = await client.post(
            f"{api_url}/api/submit",
            json=results_data,
            headers=headers,
        )
        response.raise_for_status()
        return response.json()


async def submit_batch(results: list[dict], api_url: str | None = None) -> list[dict]:
    """Submit multiple results in parallel.

    Args:
        results: List of evaluation results to submit
        api_url: API endpoint (default: PRAMANA_API_URL env var or DEFAULT_API_URL)
    """
    if api_url is None:
        api_url = get_api_url()

    tasks = [submit_results(result, api_url) for result in results]
    return await asyncio.gather(*tasks)
