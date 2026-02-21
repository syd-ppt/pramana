"""Unit tests for pramana.storage module."""

from __future__ import annotations

import json

import pytest

from pramana.storage import append_result, load_results, remove_run


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def results_file(tmp_path):
    """Return a Path inside tmp_path for results.json."""
    return tmp_path / "results.json"


def _make_eval_results(**overrides):
    """Build a minimal EvalResults instance for testing."""
    from pramana.protocol import EvalResults

    defaults = {
        "suite_version": "v1.0",
        "suite_hash": "abc123",
        "run_metadata": {
            "timestamp": "2025-01-01T00:00:00",
            "model_id": overrides.pop("model_id", "gpt-4"),
            "temperature": 0.0,
            "seed": 42,
            "runner_version": "0.1.0",
        },
        "results": [],
        "summary": {"total": 0, "passed": 0, "skipped": 0, "pass_rate": 0.0},
    }
    defaults.update(overrides)
    return EvalResults(**defaults)


# ---------------------------------------------------------------------------
# load_results
# ---------------------------------------------------------------------------

class TestLoadResults:

    def test_load_nonexistent(self, results_file):
        assert load_results(results_file) == []

    def test_load_empty_file(self, results_file):
        results_file.write_text("")
        assert load_results(results_file) == []

    def test_load_whitespace_only(self, results_file):
        results_file.write_text("   \n  ")
        assert load_results(results_file) == []

    def test_load_single_object(self, results_file):
        obj = {"model_id": "gpt-4", "status": "ok"}
        results_file.write_text(json.dumps(obj))
        assert load_results(results_file) == [obj]

    def test_load_array(self, results_file):
        blocks = [{"a": 1}, {"b": 2}]
        results_file.write_text(json.dumps(blocks))
        assert load_results(results_file) == blocks

    def test_load_invalid_json(self, results_file):
        results_file.write_text("{bad json")
        with pytest.raises(json.JSONDecodeError):
            load_results(results_file)

    def test_load_invalid_type_string(self, results_file):
        results_file.write_text('"just a string"')
        with pytest.raises(ValueError, match="Expected JSON object or array"):
            load_results(results_file)

    def test_load_invalid_type_number(self, results_file):
        results_file.write_text("42")
        with pytest.raises(ValueError, match="Expected JSON object or array"):
            load_results(results_file)


# ---------------------------------------------------------------------------
# append_result
# ---------------------------------------------------------------------------

class TestAppendResult:

    def test_append_new_file(self, results_file):
        er = _make_eval_results(model_id="gpt-4")
        count = append_result(results_file, er)

        assert count == 1
        blocks = json.loads(results_file.read_text())
        assert isinstance(blocks, list)
        assert len(blocks) == 1
        assert blocks[0]["run_metadata"]["model_id"] == "gpt-4"

    def test_append_existing(self, results_file):
        er1 = _make_eval_results(model_id="gpt-4")
        append_result(results_file, er1)

        er2 = _make_eval_results(model_id="claude-opus-4-6")
        count = append_result(results_file, er2)

        assert count == 2
        blocks = json.loads(results_file.read_text())
        assert blocks[0]["run_metadata"]["model_id"] == "gpt-4"
        assert blocks[1]["run_metadata"]["model_id"] == "claude-opus-4-6"

    def test_append_to_old_single_object_format(self, results_file):
        """Backward compat: appending to an old single-object file."""
        old = {"suite_version": "v1.0", "run_metadata": {"model_id": "old"}}
        results_file.write_text(json.dumps(old))

        er = _make_eval_results(model_id="new")
        count = append_result(results_file, er)

        assert count == 2
        blocks = json.loads(results_file.read_text())
        assert blocks[0]["run_metadata"]["model_id"] == "old"
        assert blocks[1]["run_metadata"]["model_id"] == "new"


# ---------------------------------------------------------------------------
# remove_run
# ---------------------------------------------------------------------------

class TestRemoveRun:

    def test_remove_first(self, results_file):
        blocks = [{"id": 0}, {"id": 1}, {"id": 2}]
        results_file.write_text(json.dumps(blocks))

        remaining = remove_run(results_file, 0)
        assert remaining == 2
        data = json.loads(results_file.read_text())
        assert data == [{"id": 1}, {"id": 2}]

    def test_remove_middle(self, results_file):
        blocks = [{"id": 0}, {"id": 1}, {"id": 2}]
        results_file.write_text(json.dumps(blocks))

        remaining = remove_run(results_file, 1)
        assert remaining == 2
        data = json.loads(results_file.read_text())
        assert data == [{"id": 0}, {"id": 2}]

    def test_remove_last_deletes_file(self, results_file):
        results_file.write_text(json.dumps([{"only": True}]))

        remaining = remove_run(results_file, 0)
        assert remaining == 0
        assert not results_file.exists()

    def test_remove_out_of_range(self, results_file):
        results_file.write_text(json.dumps([{"a": 1}]))

        with pytest.raises(IndexError, match="out of range"):
            remove_run(results_file, 5)

    def test_remove_negative_index(self, results_file):
        results_file.write_text(json.dumps([{"a": 1}]))

        with pytest.raises(IndexError, match="out of range"):
            remove_run(results_file, -1)

    def test_remove_from_empty_list(self, results_file):
        results_file.write_text("[]")
        # load_results returns [], so index 0 is out of range (0..-1)
        with pytest.raises(IndexError):
            remove_run(results_file, 0)
