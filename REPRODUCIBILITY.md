# Reproducibility in Pramana

## Overview

Pramana requires reproducible model outputs to accurately detect drift. This document explains reproducibility guarantees for different user types and providers.

## User Types

### Type 1: API Users (High Reproducibility)
**Who:** Users with provider API keys (OPENAI_API_KEY, ANTHROPIC_API_KEY)
**How:** Direct API calls with explicit temperature and seed parameters
**Recommended for:** Scientific drift detection, research, production monitoring

### Type 2: Subscription Users (Low Reproducibility)
**Who:** Users with Claude Code Max subscription, no API keys
**How:** Programmatic access via claude-agent-sdk
**Use case:** Exploratory testing, personal benchmarking (not scientific drift detection)

---

## Provider Comparison

| Provider | Temperature | Seed | Reproducibility | Recommended Use |
|----------|-------------|------|-----------------|-----------------|
| **OpenAI API** | ✅ Enforced | ✅ Enforced | **High** | ✅ Scientific drift detection |
| **Anthropic API** | ✅ Enforced | ❌ Ignored | **Low** | ⚠️ Not recommended |
| **Claude Code** | ⚠️ Hint only (default: 1.0) | ❌ Not available | **Low** | ⚠️ Not recommended |

---

## Technical Details

### OpenAI API ✅

**Status:** Full reproducibility support

```python
# Guaranteed deterministic output
response = await openai_client.chat.completions.create(
    model="gpt-4",
    messages=[{"role": "user", "content": "prompt"}],
    temperature=0.0,
    seed=42
)
```

**Guarantees:**
- Same `seed` + same `system_fingerprint` → identical output
- `system_fingerprint` changes only on infrastructure updates (rare)
- Temperature=0 enforced at API level

**Documentation:** https://cookbook.openai.com/examples/reproducible_outputs_with_the_seed_parameter

---

### Anthropic API ❌

**Status:** Seed parameter NOT supported (as of February 2026)

```python
# Non-deterministic even with temperature=0
response = await anthropic_client.messages.create(
    model="claude-opus-4-6",
    messages=[{"role": "user", "content": "prompt"}],
    temperature=0.0,
    seed=42  # ⚠️ IGNORED - parameter accepted but has no effect
)
```

**Issues:**
- API accepts `seed` parameter but **silently ignores it**
- Official docs: "even with temperature=0.0, results will not be fully deterministic"
- No `system_fingerprint` equivalent
- No reproducibility guarantees

**Evidence:**
- API docs: https://docs.anthropic.com/en/api/messages (no seed parameter)
- LiteLLM issue: https://github.com/BerriAI/litellm/issues/6856

**Code impact:** `src/pramana/providers/anthropic.py` passes seed but it's a no-op.

---

### Claude Code Subscription ❌

**Status:** No parameter control, uses default temperature=1.0

```python
# Non-deterministic, cannot control parameters
from claude_agent_sdk import query

async for msg in query(
    prompt="[Parameters: temperature=0.0, seed=42]\n\nprompt"
):
    # Parameters sent as text hints only, not enforced
    pass
```

**Characteristics:**
- **Default temperature:** 1.0 (consistent across all users)
- **Default seed:** None (parameter doesn't exist)
- **Parameter hints:** Can include in prompt text, but not enforced by API
- **Reproducibility:** Non-deterministic by design

**Evidence:**
- Agent SDK issue: https://github.com/anthropics/claude-agent-sdk-python/issues/273
- No temperature/seed parameters exposed in SDK
- Uses Messages API internally with defaults

---

## Recommendations

### For Scientific Drift Detection
**Use OpenAI API with explicit keys:**
```bash
export OPENAI_API_KEY="sk-..."
pramana run --tier comprehensive --model gpt-4 --temperature 0.0 --seed 42
```

### For Exploratory Testing
**Use any provider, but understand limitations:**
```bash
# API users
pramana run --tier cheap --model claude-opus-4-6 --api-key "sk-..."

# Subscription users
pramana run --tier cheap --model claude-opus-4-6 --use-subscription
```

⚠️ **Warning:** Results from Anthropic API and Claude Code subscription are **not reproducible** and should not be used for drift detection research.

---

## Testing Reproducibility

Run the test suite to verify assertion logic and provider wiring:

```bash
uv run python -m pytest tests/
```

For empirical variance measurement, run the same eval multiple times and compare result hashes.

---

## Future Work

1. **Anthropic seed support:** Monitor for API updates adding true seed support
2. **Claude Code control:** Test if future SDK versions expose temperature/seed
3. **Alternative providers:** Add Google Gemini, Cohere (check seed support first)
4. **Validation mode:** Run tests N times, flag inconsistencies automatically

---

## Summary

**Two standards exist:**

1. **API Standard (High Reproducibility)**
   - Provider: OpenAI
   - Parameters: temperature=0.0, seed=42
   - Guarantee: Deterministic outputs
   - Use: Scientific drift detection

2. **Subscription Standard (Low Reproducibility)**
   - Provider: Claude Code
   - Parameters: temperature=1.0 (implicit default)
   - Guarantee: None (non-deterministic)
   - Use: Exploratory testing only

**Key insight:** Consistent defaults ≠ reproducibility. Claude Code uses temperature=1.0 for all users (standard), but outputs still vary (non-deterministic).
