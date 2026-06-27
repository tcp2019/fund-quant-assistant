# v2.0 动态权重+新手引导+PWA Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development

> **Status:** active | **Created:** 2026-06-27
> **Spec:** docs/superpowers/specs/active/2026-06-27-adaptive-onboarding-pwa-design.md

**Goal:** 动态权重、新手引导、PWA

---

### Task 1: 动态权重

**Files:**
- Create: `backend/tests/test_adaptive_weights.py`
- Create: `backend/app/services/signals/adaptive_weights.py`
- Modify: `backend/app/services/signals/engine.py`

`adaptive_weights.py`:
```python
"""Adaptive layer weights based on macro environment."""

DEFAULT_WEIGHTS = {"rebalance": 0.4, "risk": 0.3, "performance": 0.3}
TIGHT_WEIGHTS = {"rebalance": 0.4, "risk": 0.4, "performance": 0.2}
LOOSE_WEIGHTS = {"rebalance": 0.5, "risk": 0.2, "performance": 0.3}


def get_adaptive_weights(environment: str) -> dict:
    if environment == "tight":
        return TIGHT_WEIGHTS
    elif environment == "loose":
        return LOOSE_WEIGHTS
    return DEFAULT_WEIGHTS
```

Test: verify tight/loose/neutral/unknown return correct weights.

In engine.py `run_signal_engine`, after computing `days_since_snapshot`, call:
```python
from app.services.macro import fetch_macro_indicators
macro = fetch_macro_indicators()
weights = get_adaptive_weights(macro.get("environment", "neutral"))
# Replace LAYER_WEIGHTS reference with weights
```

Where `LAYER_WEIGHTS` is used in `aggregate_signals`, pass the dynamic weights instead.

Commit: `feat: adaptive signal weights based on macro environment`

### Task 2: 新手引导

**Files:**
- Create: `frontend/src/components/OnboardingGuide.tsx`
- Modify: `frontend/src/pages/Dashboard.tsx`

`OnboardingGuide.tsx`: 3-step card component, shown when no holdings. Uses localStorage `fund-quant-onboarded` to track completion.

Dashboard: import and render `<OnboardingGuide />` when `!overview || overview.holdings.length === 0`, replacing the current empty state.

Commit: `feat: add onboarding guide for new users`

### Task 3: PWA

**Files:**
- Modify: `frontend/vite.config.ts`
- Create: `frontend/public/manifest.json`
- Create: `frontend/public/icon-192.png` (placeholder)
- Modify: `frontend/index.html`

Install `vite-plugin-pwa`, configure with minimal manifest. Use existing favicon as PWA icon fallback.

Commit: `feat: add PWA manifest and service worker`

### Task 4: 回归 + 归档

Run tests + build. Archive plan. Update README.
