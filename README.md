<div align="center">

# pramana &nbsp;·&nbsp; प्रमाण

**Did your LLM get worse, or did you?**

Crowdsourced drift detection for LLM APIs. Run reproducible evals, compare results over time, catch silent model changes.

[![Tests](https://github.com/syd-ppt/pramana/workflows/Tests/badge.svg)](https://github.com/syd-ppt/pramana/actions)
[![PyPI](https://img.shields.io/pypi/v/pramana)](https://pypi.org/project/pramana/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

</div>

---

## The Problem

When you call `gpt-5` or `claude-sonnet-4-6` today, you might get different behavior than yesterday. Providers update, fine-tune, and swap models behind stable identifiers. **This is invisible.**

There's no standard way to notice — let alone measure — these changes.

## The Fix

```bash
pip install pramana
```

```bash
$ pramana run --tier cheap --model gpt-5.2
Running cheap suite against gpt-5.2...
✓ 10/10 passed
Pass rate: 100.0%
```

Same prompts. Same parameters. Deterministic where the provider allows it. Compare across runs and users.

---

## Usage

```bash
# See all supported models
pramana models

# Run evals (auto-detects provider from model name)
export OPENAI_API_KEY=sk-...
pramana run --tier cheap --model gpt-4o

# Aliases work too
pramana run --tier cheap --model opus

# Submit to the public leaderboard
pramana submit results.json
```

**Tiers:**

| Tier | Tests | Purpose |
|------|-------|---------|
| `cheap` | 10 | Smoke test, CI gates |
| `moderate` | 25 | Regular monitoring |
| `comprehensive` | 75 | Full evaluation |

All tiers cover 6 categories: reasoning, factual, instruction following, coding, safety, creative.

---

## Providers

| Provider | Temperature | Seed | Reproducibility |
|----------|-------------|------|-----------------|
| **OpenAI** | ✅ Enforced | ✅ Enforced | **High** |
| **Anthropic** | ✅ Enforced | ❌ Ignored | **Low** |
| **Google** | Coming soon | — | — |

For scientific drift detection, **use OpenAI API with explicit keys.** See [REPRODUCIBILITY.md](REPRODUCIBILITY.md).

---

## How It Works

```
You run pramana ──► Fixed prompts hit the API ──► Results hashed & stored
                                                         │
Other users run pramana ──► Same prompts ──► Results compared
                                                         │
                                              Drift detected via
                                              output consistency tracking
```

- **Content-addressable hashing** — SHA-256 of (model, prompt, output) for deduplication
- **Deterministic parameters** — `temperature=0.0`, `seed=42` enforced by default
- **No normalization layer** — raw API responses, not filtered through LiteLLM

---

## Authentication (Optional)

```bash
pramana login          # GitHub/Google OAuth
pramana whoami         # Check status
pramana delete         # GDPR: delete all your data
```

No login required to run evals or submit results. Auth enables personalized tracking.

---

## Development

```bash
git clone https://github.com/syd-ppt/pramana && cd pramana
uv pip install -e ".[dev]"
pytest tests/
```

Backend: [`pramana-api`](https://github.com/syd-ppt/pramana-api) · Dashboard: [pramana.pages.dev](https://pramana.pages.dev)

---

## Contributing

1. **Add test cases** — append to `suites/v1.0/{tier}.jsonl`
2. **Add providers** — subclass `BaseProvider` in `src/pramana/providers/`
3. **Improve assertions** — new types in `assertions.py`

See [CONTRIBUTING.md](CONTRIBUTING.md).

---

<div align="center">

**pramana** (प्रमाण) — Sanskrit for *proof, evidence, valid knowledge*

[Docs](https://syd-ppt.github.io/pramana) · [Dashboard](https://pramana.pages.dev) · [PyPI](https://pypi.org/project/pramana/) · [Issues](https://github.com/syd-ppt/pramana/issues)

</div>
