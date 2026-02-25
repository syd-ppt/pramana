#!/usr/bin/env python3
"""Transform and submit test results to Pramana API."""

import json
import sys
import time
from pathlib import Path
import httpx


def submit_results(results_file: Path, api_url: str = "https://pramana.pages.dev"):
    """Submit test results to API."""

    # Load results
    with open(results_file) as f:
        data = json.load(f)

    model_id = data["run_metadata"]["model_id"]

    # Transform each result to API format
    submissions = []
    for result in data["results"]:
        submission = {
            "model_id": model_id,
            "prompt_id": result["test_id"],
            "output": result["output"],
            "metadata": {
                "latency_ms": result.get("latency_ms"),
                "result_hash": result.get("result_hash"),
                "passed": result.get("assertion_result", {}).get("passed"),
                "suite_version": data["suite_version"],
                "temperature": data["run_metadata"]["temperature"],
                "seed": data["run_metadata"]["seed"],
            }
        }
        submissions.append(submission)

    # Submit to API
    success = 0
    failed = 0

    print(f"Submitting {len(submissions)} results for {model_id}...")

    with httpx.Client(timeout=30.0) as client:
        for i, sub in enumerate(submissions, 1):
            # Rate limit: 60/min = 1/sec, so add 1.1s delay between requests
            if i > 1:
                time.sleep(1.1)

            try:
                response = client.post(
                    f"{api_url}/api/submit",
                    json=sub
                )
                response.raise_for_status()
                result = response.json()
                print(f"  [{i}/{len(submissions)}] ✓ {sub['prompt_id']}: {result.get('status')}")
                success += 1
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 429:
                    print(f"  [{i}/{len(submissions)}] ⏱ Rate limited, waiting 60s...")
                    time.sleep(60)
                    # Retry
                    try:
                        response = client.post(f"{api_url}/api/submit", json=sub)
                        response.raise_for_status()
                        result = response.json()
                        print(f"  [{i}/{len(submissions)}] ✓ {sub['prompt_id']}: {result.get('status')} (retry)")
                        success += 1
                    except Exception as retry_err:
                        print(f"  [{i}/{len(submissions)}] ✗ {sub['prompt_id']}: {retry_err}")
                        failed += 1
                else:
                    print(f"  [{i}/{len(submissions)}] ✗ {sub['prompt_id']}: {e.response.status_code}")
                    print(f"      {e.response.text[:200]}")
                    failed += 1
            except Exception as e:
                print(f"  [{i}/{len(submissions)}] ✗ {sub['prompt_id']}: {e}")
                failed += 1

    print(f"\n✓ Success: {success}/{len(submissions)}")
    if failed:
        print(f"✗ Failed: {failed}/{len(submissions)}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python submit_results.py <results_file>")
        print("Example: python submit_results.py cheap_results.json")
        sys.exit(1)

    submit_results(Path(sys.argv[1]))
