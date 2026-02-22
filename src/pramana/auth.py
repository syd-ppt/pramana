"""CLI authentication - browser-based token flow."""

import json
import stat
import webbrowser
from pathlib import Path

CONFIG_DIR = Path.home() / ".pramana"
CONFIG_FILE = CONFIG_DIR / "config.json"

DEFAULT_API_URL = "https://pramana.pages.dev"


def login(api_url: str = DEFAULT_API_URL) -> None:
    """Open browser to get CLI token."""
    print(f"Opening {api_url}/cli-token in your browser...")
    print("Copy your token and paste it here.")

    webbrowser.open(f"{api_url}/cli-token")
    token = input("\nPaste token: ").strip()

    if not token:
        print("Error: No token provided")
        return

    update_config("token", token)
    update_config("api_url", api_url)
    print("✓ Logged in! Your submissions will now be linked to your account.")


def logout() -> None:
    """Clear stored token (preserves other config like preferred_mode)."""
    config = load_config()
    if not config or "token" not in config:
        print("Not logged in")
        return

    config.pop("token", None)
    config.pop("api_url", None)
    save_config(config)
    print("✓ Logged out")


def whoami() -> None:
    """Show current login status."""
    config = load_config()
    if config and config.get("token"):
        token = config["token"]
        # Show first 16 chars of token for verification
        token_preview = token[:16] + "..." if len(token) > 16 else token
        print(f"Logged in (token: {token_preview})")
        print(f"API URL: {config.get('api_url', 'not set')}")
    else:
        print("Not logged in. Run 'pramana login' to authenticate.")


def load_config() -> dict | None:
    """Load user config."""
    if not CONFIG_FILE.exists():
        return None
    try:
        return json.loads(CONFIG_FILE.read_text())
    except (json.JSONDecodeError, OSError):
        return None


def save_config(config: dict) -> None:
    """Save user config with restricted permissions."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    CONFIG_DIR.chmod(stat.S_IRWXU)  # 0o700 — owner only
    CONFIG_FILE.write_text(json.dumps(config, indent=2))
    CONFIG_FILE.chmod(stat.S_IRUSR | stat.S_IWUSR)  # 0o600 — owner read/write


def update_config(key: str, value: str) -> None:
    """Merge a single key into existing config (preserves other keys)."""
    config = load_config() or {}
    config[key] = value
    save_config(config)


def get_auth_header() -> dict | None:
    """Get Authorization header if logged in."""
    config = load_config()
    if not config or "token" not in config:
        return None
    return {"Authorization": f"Bearer {config['token']}"}


def get_api_url() -> str | None:
    """Get configured API URL."""
    config = load_config()
    if not config:
        return None
    return config.get("api_url")


async def delete_user_data(anonymize_only: bool = False, api_url: str | None = None) -> dict:
    """Delete user data via API.

    Args:
        anonymize_only: If True, keep results as anonymous. If False, full deletion.
        api_url: API endpoint (default: from config)

    Returns:
        API response dict
    """
    import httpx

    if api_url is None:
        api_url = get_api_url()
        if not api_url:
            raise ValueError("Not logged in. Cannot delete data without authentication.")

    auth_header = get_auth_header()
    if not auth_header:
        raise ValueError("Not logged in. Run 'pramana login' first.")

    params = {"anonymize_only": "true"} if anonymize_only else {}

    async with httpx.AsyncClient(timeout=httpx.Timeout(30.0)) as client:
        response = await client.delete(
            f"{api_url}/api/user/me",
            headers=auth_header,
            params=params,
        )
        response.raise_for_status()
        return response.json()
