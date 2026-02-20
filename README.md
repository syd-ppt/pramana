# Pramana (प्रमाण)

**Did your LLM get worse, or did you?** Find out. Pramana runs reproducible evaluations against provider APIs so you can measure what changed — and when.

[![Tests](https://github.com/syd-ppt/pramana/workflows/Tests/badge.svg)](https://github.com/syd-ppt/pramana/actions)
[![PyPI](https://img.shields.io/pypi/v/pramana)](https://pypi.org/project/pramana/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## Why This Exists

When you call `gpt-5` or `claude-sonnet-4-6` today, you might get different behavior than yesterday — same model name, different results. Providers update, fine-tune, and swap models behind stable identifiers. This is normal and often beneficial, but it's invisible to users who depend on consistent behavior.

There's no standard way to notice, let alone measure, these changes.

## What Pramana Does

Run a fixed set of evaluations against any LLM API. Same prompts, same parameters, deterministic where the provider allows it. Compare results over time — locally or via a public leaderboard.

---

## Platform Support

Works on **macOS**, **Linux**, **Windows**, and **WSL**. Requires Python 3.11+. No platform-specific dependencies.

```bash
pip install pramana       # pip
uv pip install pramana    # uv
uvx pramana               # run without installing
```

---

## Quick Start

### List Available Models

```bash
# See all supported models (auto-updated from LiteLLM registry)
pramana models
```

### Run Evaluations

Pramana auto-detects how to reach your model — just set an API key or install the subscription SDK:

```bash
# API mode (auto-detected from env vars)
export OPENAI_API_KEY=sk-...
pramana run --tier cheap --model gpt-4o

# Subscription mode (auto-detected when claude-agent-sdk is installed)
pramana run --tier cheap --model claude-opus-4-6

# Explicit flags still work
pramana run --tier cheap --model gpt-4o --api-key sk-...
pramana run --tier cheap --model claude-opus-4-6 --use-subscription
```

When both API key and subscription are available for a model, Pramana uses your configured preference (default: subscription). Change with `pramana config`:

```bash
pramana config --show                # Show current preference
pramana config --prefer-api          # Default to API mode
pramana config --prefer-subscription # Default to subscription mode
```

⚠️ **Note:** Subscription mode uses temperature=1.0 and is non-deterministic. For scientific testing, use API keys. See [REPRODUCIBILITY.md](REPRODUCIBILITY.md).

### Submit to Leaderboard (Optional)

```bash
# Submit your results to the public dashboard
pramana submit results.json
```

By default, results are submitted to the community instance. To run your own private instance, set:

```bash
export PRAMANA_API_URL=https://your-api.com
```

### User Authentication (Optional)

Link your submissions to your account for personalized tracking:

```bash
# One-time login (opens browser for GitHub/Google OAuth)
pramana login

# Check status
pramana whoami

# Submit with authentication (automatically uses stored token)
pramana submit results.json

# Logout
pramana logout
```

**Features:**
- ✅ **Personalized dashboard** - "You vs Crowd" statistics
- ✅ **Anonymous by default** - No login required to use Pramana
- ✅ **GDPR compliant** - Full data deletion or anonymization
- ✅ **Zero cost** - Free GitHub/Google OAuth

**Data deletion (GDPR):**

```bash
# Full deletion - remove all your submissions
pramana delete --confirm

# Anonymization - keep results for crowd statistics but unlink from account
pramana delete --anonymize --confirm
```

See [AUTH_IMPLEMENTATION.md](AUTH_IMPLEMENTATION.md) for details.

---

## Test Suites

All three tiers cover the same 6 categories — they differ in test **density**, not scope.

| Tier | Tests | Categories | Use Case |
|------|-------|------------|----------|
| **cheap** | 10 | All 6 (1-3 each) | Quick smoke test, CI gates |
| **moderate** | 25 | All 6 (2-6 each) | Regular monitoring |
| **comprehensive** | 75 | All 6 (8-17 each) | Full evaluation, release validation |

**Categories:** reasoning, factual, instruction_following, coding, safety, creative

**Assertion types:** `exact_match`, `contains`, `contains_any`, `is_json`

All test suites are in `suites/v1.0/*.jsonl` with content-addressable SHA-256 versioning.

---

## Reproducibility

Pramana enforces reproducible evaluation parameters:

- **Temperature:** 0.0 (deterministic output)
- **Seed:** 42 (fixed seed for sampling)

**Provider Support:**

| Provider | Temperature | Seed | Reproducibility |
|----------|-------------|------|-----------------|
| OpenAI API | ✅ Enforced | ✅ Enforced | **High** |
| Anthropic API | ✅ Enforced | ❌ Ignored | **Low** |
| Claude Code | ⚠️ Hints only | ❌ N/A | **Low** |

**Recommendation:** For scientific drift detection, use OpenAI API with explicit keys.

📖 See [REPRODUCIBILITY.md](REPRODUCIBILITY.md) for full technical details.

---

## Development

```bash
git clone https://github.com/syd-ppt/pramana
cd pramana
uv pip install -e ".[dev]"
pytest tests/
ruff check .
```

API server and dashboard are in the sibling repo [`pramana-api`](https://github.com/syd-ppt/pramana-api).

---

## Contributing

We welcome contributions! Ways to help:

1. **Add test cases** - See [CONTRIBUTING.md](CONTRIBUTING.md)
2. **Add provider support** - Implement new `BaseProvider` subclasses
3. **Improve assertions** - New assertion types in `assertions.py`
4. **Report bugs** - File issues on GitHub

**Adding a Test Case:**

Edit `suites/v1.0/{tier}.jsonl` and add:

```json
{
  "id": "category-###",
  "category": "reasoning",
  "input": "Your prompt here",
  "ideal": ["Expected output"],
  "assertion": {"type": "contains", "case_sensitive": false},
  "metadata": {"difficulty": "medium", "tokens_est": 100}
}
```

Submit a PR with your additions!

---

## Architecture

```
┌─────────────┐
│   CLI Tool  │  Run tests locally, see results immediately
└──────┬──────┘
       │
       ├─► Provider APIs (OpenAI, Anthropic, Google)
       │
       └─► Submit results via API (pramana-eval.vercel.app)
              └─► B2 Parquet storage (handled by backend)
```

**Local-first design:**
- No account required to run tests
- Results saved to local JSON files
- Submit to community dashboard via API
- No storage credentials needed — backend handles B2
- Bring your own API keys

---

## Roadmap

- [x] CLI tool with provider integrations
- [x] Standardized test suites (cheap/moderate/comprehensive)
- [x] Content-addressable versioning
- [x] Reproducibility enforcement
- [x] User authentication with personalized tracking
- [x] GDPR compliance (deletion & anonymization)
- [ ] Additional providers (Google, Cohere, Mistral)
- [ ] Custom test suite support
- [ ] Personalized dashboard with DuckDB-WASM queries
- [ ] LLM judge assertions
- [ ] Semantic similarity assertions

---

## Etymology

**Pramana** (प्रमाण, Sanskrit)
- Meaning: proof, evidence, validation
- Pronunciation: `pra-MAH-nah`
- Philosophy: Knowledge established through valid means of proof

In Indian epistemology, pramana represents sources of correct knowledge. Perfect for validating LLM behavior through systematic evaluation.

---

## License

MIT - see [LICENSE](LICENSE)

---

## Acknowledgments

- Inspired by [OpenAI Evals](https://github.com/openai/evals)
- Statistical methods from [Stanford HELM](https://crfm.stanford.edu/helm/)
- Model registry powered by [LiteLLM](https://github.com/BerriAI/litellm)
