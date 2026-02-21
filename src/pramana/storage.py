"""Results file I/O — append-mode accumulation with drain-on-submit."""

from __future__ import annotations

import json
from pathlib import Path

from pramana.protocol import EvalResults


def load_results(path: Path) -> list[dict]:
    """Load results blocks from a JSON file.

    Args:
        path: Path to the results JSON file.

    Returns:
        List of result block dicts.

    Raises:
        json.JSONDecodeError: If the file contains invalid JSON.
        ValueError: If the JSON root is not an object or array.
    """
    if not path.exists():
        return []

    text = path.read_text().strip()
    if not text:
        return []

    data = json.loads(text)

    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        return [data]

    raise ValueError(
        f"Expected JSON object or array in {path}, got {type(data).__name__}"
    )


def append_result(path: Path, results: EvalResults) -> int:
    """Append a result block to the results file.

    Args:
        path: Path to the results JSON file.
        results: Evaluation results to append.

    Returns:
        Total number of runs after append.
    """
    runs = load_results(path)
    runs.append(json.loads(results.model_dump_json()))
    path.write_text(json.dumps(runs, indent=2))
    return len(runs)


def remove_run(path: Path, index: int) -> int:
    """Remove a result run by index and rewrite the file.

    Args:
        path: Path to the results JSON file.
        index: Index of the run to remove.

    Returns:
        Number of remaining runs.

    Raises:
        IndexError: If index is out of range.
    """
    runs = load_results(path)

    if index < 0 or index >= len(runs):
        raise IndexError(
            f"Run index {index} out of range (0..{len(runs) - 1})"
        )

    runs.pop(index)

    if not runs:
        path.unlink()
    else:
        path.write_text(json.dumps(runs, indent=2))

    return len(runs)
