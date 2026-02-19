# Pramana Tests

## Test Structure

```
tests/
├── test_models.py              # Model detection & registry
├── test_assertions.py          # Assertion evaluation logic
├── test_hash.py                # Content-addressable hashing
├── test_auth.py                # Authentication & config storage
├── test_cli_integration.py     # CLI command integration tests
└── test_providers_integration.py # Provider API integration tests
```

## Running Tests

### Prerequisites

```bash
# Python 3.11+ required
python --version  # Should be 3.11 or higher

# Install with dev dependencies
pip install -e ".[dev]"
```

### Run All Tests

```bash
pytest tests/
```

### Run Specific Test Files

```bash
# Unit tests
pytest tests/test_models.py -v
pytest tests/test_assertions.py -v
pytest tests/test_hash.py -v
pytest tests/test_auth.py -v

# Integration tests
pytest tests/test_cli_integration.py -v
pytest tests/test_providers_integration.py -v
```

### Run Specific Test Classes

```bash
pytest tests/test_cli_integration.py::TestAuthCommands -v
pytest tests/test_providers_integration.py::TestOpenAIProvider -v
```

### Run with Coverage

```bash
pytest tests/ --cov=pramana --cov-report=html
open htmlcov/index.html
```

## Test Categories

### Unit Tests

Test individual components in isolation:
- **test_models.py** - Dynamic model registry, provider detection
- **test_assertions.py** - Assertion types (exact_match, contains, is_json)
- **test_hash.py** - SHA-256 content hashing
- **test_auth.py** - Config storage, token management

### Integration Tests

Test CLI commands and provider interactions (with mocked APIs):

#### test_cli_integration.py

Tests CLI commands:
- ✅ `pramana models` - List available models
- ✅ `pramana models --refresh` - Force refresh
- ✅ `pramana login` - Browser-based OAuth
- ✅ `pramana whoami` - Check login status
- ✅ `pramana logout` - Clear credentials
- ✅ `pramana delete` - GDPR deletion (full & anonymize)
- ✅ `pramana run` - Execute evals (API key & subscription modes)
- ✅ `pramana submit` - Submit results (authenticated & anonymous)

#### test_providers_integration.py

Tests provider implementations:
- ✅ OpenAI provider (API key, env vars, message formats)
- ✅ Anthropic provider (API key, env vars, message formats)
- ✅ Parameter handling (temperature, seed, reproducibility)
- ✅ Error handling (API errors, invalid keys)
- ✅ Response parsing (content extraction)

## Test Coverage Goals

- **Unit tests:** 90%+ coverage
- **Integration tests:** Cover all CLI commands and provider flows
- **Mocking:** All external API calls mocked (no real API requests in tests)

## CI/CD Integration

Add to `.github/workflows/test.yml`:

```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ["3.11", "3.12"]

    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: ${{ matrix.python-version }}

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -e ".[dev]"

      - name: Run tests
        run: pytest tests/ -v --cov=pramana

      - name: Upload coverage
        uses: codecov/codecov-action@v3
```

## Writing New Tests

### Unit Test Template

```python
"""Tests for new_module."""

import pytest
from pramana.new_module import new_function


def test_new_function_basic():
    """Should handle basic case."""
    result = new_function("input")
    assert result == "expected"


def test_new_function_edge_case():
    """Should handle edge case."""
    with pytest.raises(ValueError):
        new_function(None)
```

### Integration Test Template

```python
"""Integration tests for new command."""

from unittest.mock import patch, AsyncMock
from click.testing import CliRunner
from pramana.cli import cli


def test_new_command():
    """Should execute new command."""
    runner = CliRunner()

    with patch("pramana.module.function") as mock_func:
        mock_func.return_value = "result"

        result = runner.invoke(cli, ["new-command", "--flag"])

        assert result.exit_code == 0
        assert "success" in result.output
```

## Debugging Failed Tests

```bash
# Run single test with full output
pytest tests/test_cli_integration.py::TestAuthCommands::test_login_opens_browser -vvs

# Run with debugger on failure
pytest tests/ --pdb

# Show print statements
pytest tests/ -s
```

## Test Best Practices

1. **Mock external APIs** - Never make real API calls in tests
2. **Use fixtures** - Reuse common setup code
3. **Test edge cases** - Not just happy path
4. **Clear test names** - Describe what is being tested
5. **Fast tests** - Keep total runtime under 10 seconds
6. **Deterministic** - Tests should always pass/fail consistently
