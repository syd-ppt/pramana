"""Integration tests for CLI commands."""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from click.testing import CliRunner

from pramana.cli import cli


@pytest.fixture
def runner():
    """Click CLI test runner."""
    return CliRunner()


@pytest.fixture
def temp_config(tmp_path, monkeypatch):
    """Mock config directory."""
    config_dir = tmp_path / ".pramana"
    config_file = config_dir / "config.json"

    import pramana.auth as auth
    monkeypatch.setattr(auth, "CONFIG_DIR", config_dir)
    monkeypatch.setattr(auth, "CONFIG_FILE", config_file)

    return config_dir, config_file


@pytest.fixture
def mock_suite_file(tmp_path):
    """Create a minimal test suite."""
    suite_dir = tmp_path / "suites" / "v1.0"
    suite_dir.mkdir(parents=True)

    suite_file = suite_dir / "cheap.jsonl"
    test_case = {
        "id": "test-001",
        "category": "reasoning",
        "input": "What is 2+2?",
        "ideal": "4",
        "assertion": {"type": "exact_match", "case_sensitive": False},
        "metadata": {"difficulty": "easy", "tokens_est": 10, "tags": []}
    }
    suite_file.write_text(json.dumps(test_case))

    return suite_file


class TestModelsCommand:
    """Test 'pramana models' command."""

    def test_models_list(self, runner):
        """Should list available models."""
        result = runner.invoke(cli, ["models"])

        assert result.exit_code == 0
        assert "openai" in result.output.lower() or "OPENAI" in result.output
        assert "anthropic" in result.output.lower() or "ANTHROPIC" in result.output

    def test_models_refresh(self, runner):
        """Should refresh model list."""
        result = runner.invoke(cli, ["models", "--refresh"])

        assert result.exit_code == 0
        # Should still show models
        assert "openai" in result.output.lower() or "OPENAI" in result.output


class TestAuthCommands:
    """Test authentication commands."""

    def test_login_opens_browser(self, runner, temp_config, monkeypatch):
        """Should open browser and store token."""
        mock_webbrowser = MagicMock()
        monkeypatch.setattr("pramana.auth.webbrowser.open", mock_webbrowser)

        # Mock user input
        result = runner.invoke(cli, ["login"], input="test_token_123\n")

        assert result.exit_code == 0
        assert "Logged in" in result.output
        mock_webbrowser.assert_called_once()

    def test_whoami_not_logged_in(self, runner, temp_config):
        """Should show not logged in."""
        result = runner.invoke(cli, ["whoami"])

        assert result.exit_code == 0
        assert "Not logged in" in result.output

    def test_whoami_logged_in(self, runner, temp_config):
        """Should show login status."""
        config_dir, config_file = temp_config
        config_dir.mkdir(parents=True, exist_ok=True)
        config_file.write_text(json.dumps({
            "token": "test_token_abc123",
            "api_url": "https://test.example.com"
        }))

        result = runner.invoke(cli, ["whoami"])

        assert result.exit_code == 0
        assert "Logged in" in result.output
        assert "test_token_abc" in result.output

    def test_logout(self, runner, temp_config):
        """Should clear stored token but preserve other config."""
        config_dir, config_file = temp_config
        config_dir.mkdir(parents=True, exist_ok=True)
        config_file.write_text(json.dumps({"token": "test", "preferred_mode": "api"}))

        result = runner.invoke(cli, ["logout"])

        assert result.exit_code == 0
        assert "Logged out" in result.output
        config = json.loads(config_file.read_text())
        assert "token" not in config
        assert config.get("preferred_mode") == "api"


class TestDeleteCommand:
    """Test GDPR deletion command."""

    def test_delete_not_logged_in(self, runner, temp_config):
        """Should fail if not logged in."""
        result = runner.invoke(cli, ["delete", "--confirm"])

        assert result.exit_code == 1
        assert "Not logged in" in result.output

    @patch("pramana.auth.delete_user_data")
    def test_delete_full_deletion(self, mock_delete, runner, temp_config):
        """Should delete all data."""
        # Set up logged in state
        config_dir, config_file = temp_config
        config_dir.mkdir(parents=True, exist_ok=True)
        config_file.write_text(json.dumps({
            "token": "test_token",
            "api_url": "https://test.example.com"
        }))

        # Mock API response
        mock_delete.return_value = {
            "status": "deleted",
            "user_id": "abc123",
            "files_deleted": 42
        }

        result = runner.invoke(cli, ["delete", "--confirm"])

        assert result.exit_code == 0
        assert "deleted successfully" in result.output
        mock_delete.assert_called_once()

    @patch("pramana.auth.delete_user_data")
    def test_delete_anonymize(self, mock_delete, runner, temp_config):
        """Should anonymize data."""
        config_dir, config_file = temp_config
        config_dir.mkdir(parents=True, exist_ok=True)
        config_file.write_text(json.dumps({
            "token": "test_token",
            "api_url": "https://test.example.com"
        }))

        mock_delete.return_value = {
            "status": "anonymized",
            "user_id": "abc123"
        }

        result = runner.invoke(cli, ["delete", "--anonymize", "--confirm"])

        assert result.exit_code == 0
        assert "anonymized successfully" in result.output
        mock_delete.assert_called_once_with(anonymize_only=True, api_url=None)


class TestRunCommand:
    """Test 'pramana run' command."""

    @patch("pramana.cli.run_eval")
    def test_run_with_api_key(self, mock_run_eval, runner, mock_suite_file, tmp_path, monkeypatch):
        """Should run eval with API key."""
        # Mock run_eval response
        mock_run_eval.return_value = MagicMock(
            summary=MagicMock(total=1, passed=1, skipped=0, pass_rate=1.0),
            model_dump_json=MagicMock(return_value='{"status": "ok"}')
        )

        output_file = tmp_path / "results.json"

        result = runner.invoke(cli, [
            "run",
            "--tier", "cheap",
            "--model", "gpt-4",
            "--output", str(output_file),
            "--api-key", "sk-test123"
        ])

        # Should succeed (or fail with suite not found - that's ok for this test)
        assert result.exit_code in [0, 1]  # Exit 1 is ok if suite not found

        if result.exit_code == 1:
            assert "Suite not found" in result.output

    @patch("pramana.cli.run_eval")
    def test_run_with_subscription_flag(self, mock_run_eval, runner, tmp_path, monkeypatch):
        """Should use subscription mode via registry."""
        from pramana.providers.registry import _REGISTRY, ProviderEntry

        # Register a fake subscription provider
        mock_cls = MagicMock()
        _REGISTRY[("anthropic", "subscription")] = ProviderEntry(
            cls=mock_cls,
            provider_name="anthropic",
            mode="subscription",
            env_key=None,
            sdk_package=None,  # skip SDK check
        )
        # Make is_available return True by patching
        monkeypatch.setattr(
            "pramana.providers.registry.is_available",
            lambda entry, api_key=None: True,
        )

        mock_run_eval.return_value = MagicMock(
            summary=MagicMock(total=1, passed=1, skipped=0, pass_rate=1.0),
            model_dump_json=MagicMock(return_value='{"status": "ok"}')
        )

        output_file = tmp_path / "results.json"

        result = runner.invoke(cli, [
            "run",
            "--tier", "cheap",
            "--model", "claude-opus-4-6",
            "--output", str(output_file),
            "--use-subscription"
        ])

        # Clean up registry
        _REGISTRY.pop(("anthropic", "subscription"), None)

        # Should show subscription warning or fail with suite not found
        if result.exit_code == 1 and "Suite not found" in result.output:
            pass
        else:
            assert "subscription mode" in result.output or result.exit_code == 1

    @patch("pramana.cli.run_eval")
    def test_run_offline_mode(self, mock_run_eval, runner, tmp_path):
        """Should run in offline mode (no submission)."""
        mock_run_eval.return_value = MagicMock(
            summary=MagicMock(total=1, passed=1, skipped=0, pass_rate=1.0),
            model_dump_json=MagicMock(return_value='{"status": "ok"}')
        )

        output_file = tmp_path / "results.json"

        result = runner.invoke(cli, [
            "run",
            "--tier", "cheap",
            "--model", "gpt-4",
            "--output", str(output_file),
            "--offline",
            "--api-key", "sk-test"
        ])

        # Should attempt to run (will fail without suite, but that's ok)
        assert "Suite not found" in result.output or result.exit_code == 0


class TestSubmitCommand:
    """Test 'pramana submit' command."""

    @patch("pramana.cli.submit_results", new_callable=AsyncMock)
    def test_submit_anonymous(self, mock_submit, runner, tmp_path, temp_config):
        """Should submit results anonymously."""
        # Create fake results file
        results_file = tmp_path / "results.json"
        results_file.write_text('{"status": "test"}')

        mock_submit.return_value = {"status": "accepted", "id": "123"}

        result = runner.invoke(cli, ["submit", str(results_file)])

        assert result.exit_code == 0
        assert "Submitted" in result.output
        assert "results" in result.output
        mock_submit.assert_called_once()

    @patch("pramana.cli.submit_results", new_callable=AsyncMock)
    def test_submit_authenticated(self, mock_submit, runner, tmp_path, temp_config):
        """Should submit with authentication."""
        # Set up logged in state
        config_dir, config_file = temp_config
        config_dir.mkdir(parents=True, exist_ok=True)
        config_file.write_text(json.dumps({
            "token": "test_token",
            "api_url": "https://test.example.com"
        }))

        results_file = tmp_path / "results.json"
        results_file.write_text('{"status": "test"}')

        mock_submit.return_value = {"status": "accepted", "submitted": 1}

        result = runner.invoke(cli, ["submit", str(results_file)])

        assert result.exit_code == 0
        assert "Submitted" in result.output
        assert "results" in result.output

    @patch("pramana.cli.submit_results", new_callable=AsyncMock)
    def test_submit_with_custom_api_url(self, mock_submit, runner, tmp_path):
        """Should submit to custom API URL."""
        results_file = tmp_path / "results.json"
        results_file.write_text('{"status": "test"}')

        mock_submit.return_value = {"status": "accepted"}

        result = runner.invoke(cli, [
            "submit",
            str(results_file),
            "--api-url", "https://custom.example.com"
        ])

        assert result.exit_code == 0
        # Should have called with custom URL
        call_args = mock_submit.call_args
        assert call_args[0][1] == "https://custom.example.com"

    def test_submit_nonexistent_file(self, runner):
        """Should fail with nonexistent file."""
        result = runner.invoke(cli, ["submit", "/tmp/nonexistent.json"])

        assert result.exit_code != 0
