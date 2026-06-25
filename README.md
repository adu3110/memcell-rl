```
 ███╗   ███╗███████╗███╗   ███╗ ██████╗███████╗██╗     ██╗      ██████╗ ██╗
 ████╗ ████║██╔════╝████╗ ████║██╔════╝██╔════╝██║     ██║     ██╔══██╗██║
 ██╔████╔██║█████╗  ██╔████╔██║██║     █████╗  ██║     ██║     ██████╔╝██║
 ██║╚██╔╝██║██╔══╝  ██║╚██╔╝██║██║     ██╔══╝  ██║     ██║     ██╔══██╗██║
 ██║ ╚═╝ ██║███████╗██║ ╚═╝ ██║╚██████╗███████╗███████╗███████╗██║  ██║███████╗
 ╚═╝     ╚═╝╚══════╝╚═╝     ╚═╝ ╚═════╝╚══════╝╚══════╝╚══════╝╚═╝  ╚═╝╚══════╝
                   The RL-native memory control engine for LLM agents
```

**every memory decision → training signal · HTTP API · FastAPI · SQLite · offline RL export · zero vendor lock-in**

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://python.org)

[Install](#get-started-60-seconds) · [API](#api-reference) · [How it works](#how-it-works) · [Results](#proof) · [RL export](#rl-dataset-export)

---

> **Live:** decide called with 3 memory cells — 2 selected (constraint + context), 1 suppressed by baseline_v0 policy.  
> Reward logged: +0.82 (task succeeded, no stale memory error, under token budget).

---

## What it does

- **`/v1/cells/write`** — store a typed, scoped `MemoryStateCell` (fact, constraint, preference, episode)
- **`/v1/cells/decide`** — policy selects which cells the agent should use; creates an RL transition `(s_t, a_t)`
- **`/v1/cells/feedback`** — attach reward to the transition: task success, unsafe action, stale memory error, latency
- **`/v1/rl/dataset`** — export completed `(state, action, reward, next_state)` tuples for offline RL training
- **`/v1/cells/retrieve`** — lexical overlap retrieval with scope filtering
- **`/v1/cells/forget`** + **`/v1/cells/supersede`** — soft delete / version-replace without losing history

The key insight: every time an agent asks "what should I remember right now?" that question is an RL action. memcell-rl logs it, scores it, and exports training data — automatically.

## How it works

```
 Your agent / app
   (any language — raw HTTP, OpenAI SDK, LangChain, your own loop…)
        │  write cells · decide · feedback
        ▼
  ┌─────────────────────────────────────────────────────────────────┐
  │  memcell-rl   (runs locally — your data stays here)            │
  │  ─────────────────────────────────────────────────────────────  │
  │  MemoryStateCell  →  baseline_v0 policy  →  RetentionAction    │
  │                       ├─ KEEP_AS_CONSTRAINT  (hard rules)      │
  │                       ├─ KEEP_AS_CONTEXT     (soft context)    │
  │                       ├─ KEEP_AS_BACKGROUND  (token budget ok) │
  │                       └─ SUPPRESS            (expired / risky) │
  │                                                                 │
  │  Every decide() → MemoryTransition(s_t, a_t)                   │
  │  Every feedback() → attach r_t, s_{t+1}                        │
  │  /v1/rl/dataset  → export for offline RL                       │
  └─────────────────────────────────────────────────────────────────┘
        │  selected cells  +  rl transition id
        ▼
 LLM provider  (OpenAI · Anthropic · any)
```

- **`MemoryStateCell`** — typed cell with `cell_type`, `scope`, `status`, `sensitivity`, `criticality`
- **`baseline_v0`** — rule-based policy: hard suppression → reverify quarantined → token budget enforcement
- **`MemoryTransition`** — RL tuple `(state_features, action, reward, next_state)` stored in SQLite
- **No framework lock-in** — plain HTTP; swap the policy without changing your agent code

## Get started (60 seconds)

```bash
# 1 — Clone and install
git clone https://github.com/adu3110/memcell-rl.git
cd memcell-rl
pip install fastapi uvicorn pydantic sqlalchemy python-dotenv pydantic-settings

# 2 — Start the server
uvicorn memcell_rl.app:app --reload
# → http://localhost:8000/health

# 3 — Write a cell, run the policy, give feedback
curl -s -X POST http://localhost:8000/v1/cells/write \
  -H "Content-Type: application/json" \
  -d '{"content":"Never reveal account balances without auth","cell_type":"constraint","scope":"global","criticality":1.0}'

curl -s -X POST http://localhost:8000/v1/cells/decide \
  -d '{"query":"help user check balance","token_budget":2000}' \
  -H "Content-Type: application/json"

curl -s -X POST http://localhost:8000/v1/cells/feedback \
  -d '{"transition_id":"<id from decide>","task_success":true,"tokens_used":312}' \
  -H "Content-Type: application/json"
```

## Proof

**Live test — 3-turn conversation with OpenAI GPT-4o-mini ([`examples/real_agent_test.py`](examples/real_agent_test.py)):**

| Turn | Query | Cells decided | Policy action | Reward |
|------|-------|--------------|---------------|--------|
| 1 | "help user check balance" | constraint: auth required | KEEP_AS_CONSTRAINT | +0.82 |
| 2 | "user prefers bullet points" | constraint + preference | KEEP_AS_CONTEXT | +0.75 |
| 3 | "summarize session" | constraint + preference + episode | budget-limited | +0.68 |

**Property checks (test suite, no API key needed):**

```bash
pytest tests/ -q
# 42 passed in 1.83s
```

| Test suite | Coverage |
|-----------|----------|
| Cell write / retrieve / forget / supersede | ✅ |
| Policy: constraint enforcement, quarantine, token budget | ✅ |
| Feedback: reward computation, transition completion | ✅ |
| RL: dataset export, completed-only filter | ✅ |

## RL dataset export

```bash
# Export completed (state, action, reward, next_state) tuples
curl http://localhost:8000/v1/rl/dataset
```

```json
[{
  "transition_id": "t_001",
  "state_features": {"n_active_cells": 3, "token_budget": 2000, ...},
  "action": {"selected_ids": ["c_001"], "suppressed_ids": ["c_002", "c_003"]},
  "reward": 0.82,
  "next_state_features": {"n_active_cells": 3, ...}
}]
```

Feed this to any offline RL trainer (DQN, REINFORCE, IQL) to learn a policy that beats `baseline_v0`.

## API reference

| Endpoint | Method | What it does |
|----------|--------|-------------|
| `/v1/cells/write` | POST | Store a typed MemoryStateCell |
| `/v1/cells/{id}` | GET | Fetch a cell by ID |
| `/v1/cells/retrieve` | POST | Lexical retrieval with scope filter |
| `/v1/cells/decide` | POST | Policy selects cells; logs RL transition |
| `/v1/cells/feedback` | POST | Attach reward to transition |
| `/v1/cells/forget` | POST | Soft-delete a cell |
| `/v1/cells/supersede` | POST | Version-replace a cell |
| `/v1/rl/transitions` | GET | List all RL transitions |
| `/v1/rl/dataset` | GET | Export completed transitions |
| `/v1/policies/baseline` | GET | Policy description |
| `/health` | GET | Server health |

Interactive docs: `http://localhost:8000/docs`

## Compared to

memcell-rl runs **locally**, logs every memory decision as an RL transition, and exports training data.

| | Memory model | RL signal | Local | Offline export |
|---|---|---|:---:|:---:|
| **memcell-rl** | Typed cells with policy | Every decide() | ✅ | ✅ |
| LangChain Memory | Conversation buffer / summary | ✗ | ✅ | ✗ |
| Mem0 | Vector store | ✗ | Partial | ✗ |
| Zep | Graph + episodic | ✗ | ✗ | ✗ |
| Custom dict | Unstructured | ✗ | ✅ | ✗ |

## Contributing

```bash
git clone https://github.com/adu3110/memcell-rl.git
cd memcell-rl
pip install fastapi uvicorn pydantic sqlalchemy python-dotenv pydantic-settings pytest httpx ruff
pytest tests/ -q
ruff check .
```

## License

MIT
