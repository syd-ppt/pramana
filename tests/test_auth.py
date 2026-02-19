"""Tests for authentication module."""

from unittest.mock import patch

import pytest

from pramana import auth


@pytest.fixture
def temp_config_dir(tmp_path):
    """Create temporary config directory."""
    config_dir = tmp_path / ".pramana"
    config_file = config_dir / "config.json"

    # Patch the module-level constants
    with patch.object(auth, "CONFIG_DIR", config_dir), \
         patch.object(auth, "CONFIG_FILE", config_file):
        yield config_dir, config_file


def test_save_and_load_config(temp_config_dir):
    """Test saving and loading configuration."""
    config_dir, config_file = temp_config_dir

    test_config = {"token": "test_token_123", "api_url": "https://example.com"}
    auth.save_config(test_config)

    assert config_file.exists()
    loaded = auth.load_config()
    assert loaded == test_config


def test_load_config_nonexistent(temp_config_dir):
    """Test loading config when file doesn't exist."""
    loaded = auth.load_config()
    assert loaded is None


def test_load_config_invalid_json(temp_config_dir):
    """Test loading config with invalid JSON."""
    config_dir, config_file = temp_config_dir
    config_dir.mkdir(parents=True, exist_ok=True)
    config_file.write_text("invalid json{")

    loaded = auth.load_config()
    assert loaded is None


def test_get_auth_header_with_token(temp_config_dir):
    """Test getting auth header when logged in."""
    config_dir, config_file = temp_config_dir
    auth.save_config({"token": "test_token"})

    header = auth.get_auth_header()
    assert header == {"Authorization": "Bearer test_token"}


def test_get_auth_header_without_token(temp_config_dir):
    """Test getting auth header when not logged in."""
    header = auth.get_auth_header()
    assert header is None


def test_get_api_url(temp_config_dir):
    """Test getting configured API URL."""
    config_dir, config_file = temp_config_dir
    auth.save_config({"token": "test", "api_url": "https://custom.example.com"})

    api_url = auth.get_api_url()
    assert api_url == "https://custom.example.com"


def test_get_api_url_not_logged_in(temp_config_dir):
    """Test getting API URL when not logged in."""
    api_url = auth.get_api_url()
    assert api_url is None


def test_logout_removes_token(temp_config_dir):
    """Test that logout removes token but preserves other config."""
    config_dir, config_file = temp_config_dir
    auth.save_config({"token": "test_token", "preferred_mode": "api"})
    assert config_file.exists()

    auth.logout()
    config = auth.load_config()
    assert config is not None
    assert "token" not in config
    assert config.get("preferred_mode") == "api"


def test_logout_when_not_logged_in(temp_config_dir, capsys):
    """Test logout when no config exists."""
    auth.logout()
    captured = capsys.readouterr()
    assert "Not logged in" in captured.out


def test_whoami_logged_in(temp_config_dir, capsys):
    """Test whoami command when logged in."""
    config_dir, config_file = temp_config_dir
    auth.save_config({"token": "very_long_token_12345678901234567890", "api_url": "https://example.com"})

    auth.whoami()
    captured = capsys.readouterr()
    assert "Logged in" in captured.out
    assert "very_long_token_..." in captured.out
    assert "https://example.com" in captured.out


def test_whoami_not_logged_in(temp_config_dir, capsys):
    """Test whoami command when not logged in."""
    auth.whoami()
    captured = capsys.readouterr()
    assert "Not logged in" in captured.out
    assert "pramana login" in captured.out
