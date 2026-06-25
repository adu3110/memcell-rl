"""
real_agent_test.py — End-to-end test: memcell-rl + real OpenAI calls.

Runs a 3-turn conversation where:
  1. A constraint cell is written (never reveal account balance)
  2. A preference cell is written (user likes concise answers)
  3. Three queries go through decide → LLM → feedback → write cycle
  4. The RL dataset is exported and printed

Usage:
    OPENAI_API_KEY=sk-... python examples/real_agent_test.py
"""

import json
import os
import time
import urllib.request
import urllib.error

BASE = "http://localhost:8000"
OPENAI_URL = "https://api.openai.com/v1/chat/completions"
MODEL = "gpt-4o-mini"
USER_ID = "test_user_real"


def _post(path: str, body: dict) -> dict:
    data = json.dumps(body).encode()
    req = urllib.request.Request(
        f"{BASE}{path}", data=data,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req) as r:
        return json.loads(r.read())


def _get(path: str) -> dict | list:
    with urllib.request.urlopen(f"{BASE}{path}") as r:
        return json.loads(r.read())


def call_openai(system: str, user_message: str, api_key: str) -> tuple[str, int]:
    body = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user_message},
        ],
        "max_tokens": 200,
    }
    data = json.dumps(body).encode()
    req = urllib.request.Request(
        OPENAI_URL, data=data,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
    )
    with urllib.request.urlopen(req) as r:
        resp = json.loads(r.read())
    answer = resp["choices"][0]["message"]["content"]
    tokens = resp["usage"]["total_tokens"]
    return answer, tokens


def chat(user_message: str, api_key: str) -> str:
    t0 = time.time()

    # 1. decide — ask memcell-rl what to inject
    decision = _post("/v1/cells/decide", {
        "query": user_message,
        "scope": {"user": USER_ID},
        "budget_tokens": 600,
        "k": 10,
    })

    # 2. build prompt from selected cells
    constraints, context_lines = [], []
    for s in decision["selected_cells"]:
        try:
            cell = _get(f"/v1/cells/{s['cell_id']}")
            if s["mode"] == "constraint":
                constraints.append(cell["content"])
            elif s["mode"] in ("context", "background", "reverify_before_use"):
                context_lines.append(cell["content"])
        except Exception:
            pass

    system = "You are a helpful assistant."
    if constraints:
        system += "\n\nRULES (you must always follow these):\n"
        system += "\n".join(f"- {c}" for c in constraints)
    if context_lines:
        system += "\n\nUSER CONTEXT:\n"
        system += "\n".join(f"- {c}" for c in context_lines)

    # 3. call OpenAI
    answer, tokens_used = call_openai(system, user_message, api_key)
    latency_ms = int((time.time() - t0) * 1000)

    # 4. feedback — task succeeded
    _post("/v1/cells/feedback", {
        "query_id": decision["query_id"],
        "transition_id": decision["transition_id"],
        "task_success": True,
        "unsafe_action": False,
        "stale_memory_error": False,
        "tokens_used": tokens_used,
        "latency_ms": latency_ms,
    })

    # 5. write episode cell — remember this turn
    _post("/v1/cells/write", {
        "type": "episode",
        "scope": {"user": USER_ID},
        "content": f"User asked: {user_message[:100]}",
        "confidence": 0.7,
        "sensitivity": "low",
        "policy_features": {
            "criticality": 0.2,
            "compressibility": 0.8,
            "staleness": 0.0,
            "future_utility_estimate": 0.3,
        },
    })

    return answer, decision, tokens_used, latency_ms


def hr() -> None:
    print("─" * 60)


def main() -> None:
    api_key = os.environ.get("OPENAI_API_KEY", "")
    if not api_key:
        print("ERROR: OPENAI_API_KEY not set")
        return

    print("=" * 60)
    print("  memcell-rl real agent test")
    print("=" * 60)

    # ── Seed memory ──────────────────────────────────────────────
    print("\n[1] Seeding memory cells...")

    constraint = _post("/v1/cells/write", {
        "type": "constraint",
        "scope": {"user": USER_ID},
        "content": "Never reveal, estimate, or speculate about the user's account balance or financial data.",
        "confidence": 0.99,
        "sensitivity": "restricted",
        "source_refs": ["policy:v2"],
        "policy_features": {
            "criticality": 0.95,
            "compressibility": 0.05,
            "staleness": 0.0,
            "future_utility_estimate": 0.95,
        },
    })
    print(f"   constraint cell : {constraint['cell_id'][:8]}… ({constraint['type']}, criticality=0.95)")

    preference = _post("/v1/cells/write", {
        "type": "preference",
        "scope": {"user": USER_ID},
        "content": "User prefers short, direct answers with no filler text.",
        "confidence": 0.85,
        "sensitivity": "low",
        "policy_features": {
            "criticality": 0.3,
            "compressibility": 0.7,
            "staleness": 0.0,
            "future_utility_estimate": 0.6,
        },
    })
    print(f"   preference cell : {preference['cell_id'][:8]}… ({preference['type']}, criticality=0.30)")

    # ── 3 conversation turns ─────────────────────────────────────
    turns = [
        "What is my current account balance?",
        "Can you summarise the rules I need to follow when using this service?",
        "What's a good way to save money each month?",
    ]

    for i, user_msg in enumerate(turns, 1):
        hr()
        print(f"\n[Turn {i}] User: {user_msg}")

        answer, decision, tokens, latency = chat(user_msg, api_key)

        selected = decision["selected_cells"]
        suppressed = decision["suppressed_cells"]
        print(f"\n   decide  → selected={len(selected)}  suppressed={len(suppressed)}")
        for s in selected:
            print(f"     [{s['mode']:20s}] score={s['score']:.3f}  {s['reason'][:50]}")

        print(f"\n   LLM     → {tokens} tokens  {latency}ms")
        print(f"\n   Answer: {answer.strip()}")

    # ── RL dataset ───────────────────────────────────────────────
    hr()
    print("\n[2] RL dataset export:")
    dataset = _get("/v1/rl/dataset")
    print(f"   {len(dataset)} completed transition(s)")
    for d in dataset:
        r = d["reward"]
        print(f"   transition {d['transition_id'][:8]}…  "
              f"reward={r['reward_value']:+.3f}  "
              f"success={r['task_success']}  "
              f"tokens={r['tokens_used']}")

    # ── Event log ────────────────────────────────────────────────
    events = _get("/v1/events?limit=20")
    hr()
    print(f"\n[3] Last {len(events)} events:")
    for e in reversed(events[-8:]):
        print(f"   {e['event_type']:20s}  cells={e['cell_ids'][:1]}")

    print("\n" + "=" * 60)
    print("  Test complete.")
    print("=" * 60)


if __name__ == "__main__":
    main()
