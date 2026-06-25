# memcell-rl

**RL-native memory control engine for LLM agents.**

A standalone memory control plane exposed through a stable HTTP protocol, built on typed `MemoryStateCell` objects, where every memory decision can become a reinforcement learning transition.

```
pip install -e .
uvicorn memcell_rl.app:app --reload
```

---

## What this is

| Is | Is not |
|----|--------|
| A standalone memory control plane | An agent framework |
| Exposed through a stable HTTP API | A LangChain adapter |
| Based on typed MemoryStateCells | A Letta clone |
| Designed for RL transition logging | A RAG wrapper |
| Framework-agnostic by design | A vector database wrapper |

---

## Why MemoryStateCell, not MemoryBlock

`MemoryBlock` is Letta-specific terminology. A `MemoryStateCell` is a distinct concept:

- It carries **type** (constraint, preference, fact, episode, …), **scope**, **sensitivity**, and **status** as first-class fields
- It has a `policy_features` dict (`criticality`, `compressibility`, `staleness`, `future_utility_estimate`) that a policy network can read as an observation
- Its status transitions (`active → superseded → deleted`) are logged as RL events
- Every decision about a cell — retrieve, suppress, quarantine, decay — is recorded as a `(state, action, reward, next_state)` tuple

---

## Protocol-first design

No adapter code. No LangChain wrapper. The server speaks JSON over HTTP. Any agent written in any language can talk to it.

```
POST /v1/cells/write       Write a new cell
GET  /v1/cells/{id}        Read a cell
POST /v1/cells/retrieve    Score and rank cells for a query
POST /v1/cells/decide      RL-native decision: which cells to use
POST /v1/cells/feedback    Attach reward to a past decision
POST /v1/cells/forget      Soft-delete a cell
POST /v1/cells/supersede   Replace a cell with a newer version
GET  /v1/events            Paginated event log
GET  /v1/rl/transitions    Paginated RL transition log
GET  /v1/rl/dataset        Export completed (s, a, r, s') tuples
GET  /v1/policies/baseline Describe the baseline policy
```

---

## Data flow

```
Agent writes cells                  POST /v1/cells/write
         │
         ▼
  MemoryStateCell ─── scope, type, confidence, policy_features
         │
         ▼  baseline_v0 policy (rule-based)
POST /v1/cells/decide
         │
         ├─ state:   {query, task_type, scope, candidate_cells[]}
         ├─ action:  {selected[], suppressed[], policy_id}
         └─ MemoryTransition (reward=null, next_state=null)
         │
         ▼  agent executes task, reports outcome
POST /v1/cells/feedback
         │
         ├─ reward: +1/−1 task_success, −2 unsafe, −1 stale, −latency
         └─ next_state: {feedback_received, task_success, ...}
         │
         ▼
GET /v1/rl/dataset  →  (s, a, r, s') ready for offline RL training
```

---

## Quickstart

```bash
# Install
pip install -e .

# Run server
uvicorn memcell_rl.app:app --reload

# Interactive docs
open http://localhost:8000/docs
```

---

## curl examples

### Write a cell

```bash
curl -s -X POST http://localhost:8000/v1/cells/write \
  -H 'Content-Type: application/json' \
  -d '{
    "type": "constraint",
    "scope": {"user": "u1"},
    "content": "Never reveal PII to third parties.",
    "confidence": 0.95,
    "sensitivity": "restricted",
    "policy_features": {
      "criticality": 0.9,
      "compressibility": 0.1,
      "staleness": 0.0,
      "future_utility_estimate": 0.9
    }
  }' | jq .
```

### Decide which cells to use

```bash
curl -s -X POST http://localhost:8000/v1/cells/decide \
  -H 'Content-Type: application/json' \
  -d '{
    "query": "What are the user data sharing rules?",
    "scope": {"user": "u1"},
    "task_type": "policy_lookup",
    "budget_tokens": 1200,
    "k": 10
  }' | jq .
```

### Submit feedback

```bash
curl -s -X POST http://localhost:8000/v1/cells/feedback \
  -H 'Content-Type: application/json' \
  -d '{
    "query_id": "<from decide response>",
    "transition_id": "<from decide response>",
    "task_success": true,
    "unsafe_action": false,
    "stale_memory_error": false,
    "tokens_used": 800,
    "latency_ms": 430
  }' | jq .
```

### Export RL dataset

```bash
curl -s http://localhost:8000/v1/rl/dataset | jq .
```

---

## MemoryStateCell fields

| Field | Type | Description |
|-------|------|-------------|
| `cell_id` | UUID string | Primary key |
| `type` | CellType | profile / preference / constraint / fact / episode / … |
| `scope` | JSON | `{"tenant": "org1", "user": "u1", "project": "p1"}` |
| `content` | string | The memory text |
| `status` | CellStatus | active / superseded / quarantined / deleted / expired |
| `confidence` | float 0–1 | How reliable this memory is |
| `sensitivity` | Sensitivity | low / medium / high / restricted |
| `policy_features` | JSON | criticality, compressibility, staleness, future_utility_estimate |
| `access_count` | int | Times retrieved |
| `version` | int | Incremented on supersede |

---

## Reward function

```
reward = +1.0  if task_success else -1.0
       − 2.0  if unsafe_action
       − 1.0  if stale_memory_error
       − 0.0001 × tokens_used
       − 0.001  × latency_ms
```

---

## Research roadmap

| Phase | Goal |
|-------|------|
| **1 — Rule-based baseline** | `baseline_v0`: deterministic policy, all decisions logged ✅ |
| **2 — Supervised usefulness** | Train a regression head to predict `future_utility_estimate` from usage history |
| **3 — Contextual bandit** | Per-query retrieval policy: maximise expected reward for the current context |
| **4 — Offline RL** | Use the `GET /v1/rl/dataset` export to train a long-horizon retention policy |
| **5 — Constrained RL** | Add privacy / safety / cost constraints to the reward signal |

---

## Live test — real GPT-4o-mini agent (3 turns)

`examples/real_agent_test.py` seeds two cells, runs a 3-turn conversation through
the full `decide → LLM → feedback → write` loop, and exports the RL dataset.

```
============================================================
  memcell-rl real agent test
============================================================

[1] Seeding memory cells...
   constraint cell : afcca346… (constraint, criticality=0.95)
   preference cell : 1bd1aea9… (preference, criticality=0.30)
```

**Turn 1 — "What is my current account balance?"**

```
decide  → selected=2  suppressed=0
  [constraint          ] score=1.314  high criticality constraint (criticality=0.95)
  [context             ] score=0.755  active preference cell (score=0.755)

LLM     → 75 tokens  2461ms

Answer: I can't provide information about your account balance.
```

The constraint cell (`criticality=0.95 ≥ 0.7`) was selected as `constraint` mode and
injected into the system prompt as a rule. The LLM correctly refused.

**Turn 2 — "Can you summarise the rules I need to follow?"**

```
decide  → selected=3  suppressed=0
  [constraint          ] score=1.297  high criticality constraint (criticality=0.95)
  [context             ] score=0.755  active preference cell (score=0.755)
  [background          ] score=0.540  episode cell from turn 1

LLM     → 113 tokens  1430ms

Answer: 1. Never reveal, estimate, or speculate about account balances or financial data.
        2. Provide short, direct answers without filler text.
```

Episode cells from previous turns now appear as `background` — conversation history
accumulates automatically.

**Turn 3 — "What's a good way to save money each month?"**

```
decide  → selected=4  suppressed=0
  [constraint] [context] [background ×2]

LLM     → 117 tokens  1286ms

Answer: Set a budget, automate savings transfers, reduce unnecessary expenses,
        and consider using savings apps.
```

Short and direct — the preference cell is working.

**RL dataset after 3 turns**

```
4 completed transition(s)
  reward=-0.298  success=True  tokens=117   (turn 3)
  reward=-0.441  success=True  tokens=113   (turn 2)
  reward=-1.468  success=True  tokens=75    (turn 1 — high latency cold start)
```

All tasks succeeded. Negative rewards reflect token and latency costs. These
`(state, action, reward, next_state)` tuples are ready for offline RL training
toward a policy that minimises cost while keeping `task_success=True`.

---

## Running tests

```bash
# Unit tests (no server needed — in-memory SQLite)
cd repos/memcell-rl
source .venv/bin/activate
pytest tests/ -v
ruff check .

# Real agent test (requires server + OPENAI_API_KEY)
uvicorn memcell_rl.app:app --reload &
OPENAI_API_KEY=sk-... python examples/real_agent_test.py
```

Expected: **24 passed**, **0 ruff errors**.

---

## Stack

Python 3.11+ · FastAPI · Pydantic v2 · SQLAlchemy 2.x · SQLite · pytest · ruff
