# Contributing to Pramana

## Scope — Read This First

Pramana is intentionally simple. The entire system is:

1. **CLI** (this repo) runs prompts against LLMs and submits results
2. **API** (`pramana-api`) stores submissions and renders the dashboard

There is no database, no cache, no queue.

| Repo | Scope |
|------|-------|
| **`pramana`** (this repo) | CLI — prompt execution, eval logic, providers, assertions, submission client |
| **`pramana-api`** | Server — submission endpoint, storage, aggregation, Next.js dashboard |

**PRs that add backend features, storage logic, or dashboard code to this repo will be closed.**
PRs that introduce infrastructure beyond the architecture above (ORMs, databases, caching layers, message queues) are out of scope for both repos.

If you're unsure which repo your change belongs in, open an issue first — happy to point you the right way.

## Adding Test Cases

Test cases are the core of Pramana. High-quality, diverse tests improve drift detection.

### Guidelines

1. **Categories**: reasoning, factual, instruction_following, coding, safety, creative
2. **Format**: One JSON object per line in JSONL files
3. **Immutability**: Once published, suites never change (create new versions)
4. **Cost awareness**: Estimate tokens accurately

### Example Test Case

```json
{
  "id": "cheap-011",
  "category": "reasoning",
  "input": "If 5 cats catch 5 mice in 5 minutes, how long for 100 cats to catch 100 mice?",
  "ideal": ["5 minutes", "5 mins"],
  "assertion": {
    "type": "contains_any",
    "case_sensitive": false
  },
  "metadata": {
    "difficulty": "medium",
    "tokens_est": 40,
    "tags": ["math", "logic"]
  }
}
```

### Adding a Test

1. Choose appropriate tier (cheap/moderate/comprehensive)
2. Add test to corresponding JSONL file
3. Update `manifest.toml` with new count and cost estimate
4. Compute new suite hash: `python -c "from pramana.hash import hash_suite; print(hash_suite('suites/v1.0/cheap.jsonl'))"`
5. Submit PR with test case + rationale

## Code Contributions

### Setup

```bash
git clone https://github.com/syd-ppt/pramana
cd pramana
uv pip install -e ".[dev]"
```

### Development

```bash
# Run tests
pytest tests/

# Lint
ruff check .

# Format
ruff format .
```

### PR Guidelines

- One feature per PR
- Include tests for new functionality
- Update documentation
- Follow existing code style
- No breaking changes without discussion

## Adding Providers

Providers auto-register via the `@register()` decorator. No manual `__init__.py` edit needed.

1. Create `src/pramana/providers/yourprovider.py`
2. Inherit from `BaseProvider`
3. Decorate with `@register("provider_name", "api", env_key="YOUR_API_KEY")`
4. Implement `complete()` and `estimate_tokens()`
5. Add provider prefix to `FALLBACK_MODELS` in `models.py`
6. Add tests

Example:
```python
from pramana.providers.base import BaseProvider
from pramana.providers.registry import register

@register("yourprovider", "api", env_key="YOUR_PROVIDER_API_KEY")
class YourProvider(BaseProvider):
    def __init__(self, model_id: str, api_key: str | None = None):
        self.model_id = model_id
        # ...

    async def complete(
        self,
        input_text: str,
        system_prompt: str | None = None,
        temperature: float = 0.0,
        seed: int | None = None,
    ) -> tuple[str, int]:
        # Your implementation
        ...

    def estimate_tokens(self, text: str) -> int:
        return len(text) // 4
```

## Issue Reporting

- Bug reports: Include Python version, command, error message
- Feature requests: Explain use case, not just solution
- Test case suggestions: Provide example with expected behavior

## Code of Conduct

- Be respectful
- Focus on the idea, not the person
- Assume good intent
- Scientific rigor over opinions
