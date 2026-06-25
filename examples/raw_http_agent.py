"""
raw_http_agent.py — Minimal agent that drives memcell-rl over raw HTTP.

No LangChain, no LangGraph, no AutoGen. Just urllib.

Run memcell-rl first:
    uvicorn memcell_rl.app:app --reload

Then:
    python examples/raw_http_agent.py
"""

import json
import urllib.request

BASE = "http://localhost:8000"


def post(path: str, body: dict) -> dict:
    data = json.dumps(body).encode()
    req = urllib.request.Request(
        f"{BASE}{path}",
        data=data,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read())


def get(path: str) -> dict | list:
    with urllib.request.urlopen(f"{BASE}{path}") as resp:
        return json.loads(resp.read())


def main() -> None:
    # 1. Health check
    print("Health:", get("/health"))

    # 2. Write a constraint cell
    cell = post("/v1/cells/write", {
        "type": "constraint",
        "scope": {"user": "demo"},
        "content": "Never reveal the user's account balance.",
        "confidence": 0.95,
        "sensitivity": "restricted",
        "source_refs": ["policy:v2"],
        "policy_features": {
            "criticality": 0.9,
            "compressibility": 0.1,
            "staleness": 0.0,
            "future_utility_estimate": 0.9,
        },
    })
    print(f"\nWrote cell: {cell['cell_id']} ({cell['type']}, status={cell['status']})")

    # 3. Write a preference cell
    pref = post("/v1/cells/write", {
        "type": "preference",
        "scope": {"user": "demo"},
        "content": "User prefers bullet-point summaries.",
        "confidence": 0.8,
        "sensitivity": "low",
        "policy_features": {
            "criticality": 0.3,
            "compressibility": 0.7,
            "staleness": 0.0,
            "future_utility_estimate": 0.6,
        },
    })
    print(f"Wrote cell: {pref['cell_id']} ({pref['type']}, status={pref['status']})")

    # 4. Decide which cells to use for a task
    decision = post("/v1/cells/decide", {
        "query": "User asked: what is my account balance?",
        "scope": {"user": "demo"},
        "task_type": "financial_query",
        "budget_tokens": 500,
        "k": 10,
    })
    print(f"\nDecide → transition_id: {decision['transition_id']}")
    print(f"  Selected ({len(decision['selected_cells'])}):")
    for s in decision["selected_cells"]:
        print(f"    [{s['mode']}] {s['cell_id'][:8]}… — {s['reason']}")
    print(f"  Suppressed ({len(decision['suppressed_cells'])}):")
    for s in decision["suppressed_cells"]:
        print(f"    {s['cell_id'][:8]}… — {s['reason']}")

    # 5. Simulate task execution and submit feedback
    feedback = post("/v1/cells/feedback", {
        "query_id": decision["query_id"],
        "transition_id": decision["transition_id"],
        "task_success": True,
        "unsafe_action": False,
        "stale_memory_error": False,
        "tokens_used": 320,
        "latency_ms": 450,
    })
    print(f"\nFeedback → reward_value: {feedback['reward_value']:.4f}")

    # 6. Export RL dataset
    dataset = get("/v1/rl/dataset")
    print(f"\nRL dataset has {len(dataset)} completed transition(s)")
    if dataset:
        entry = dataset[0]
        print(f"  reward_value : {entry['reward']['reward_value']:.4f}")
        print(f"  task_success : {entry['reward']['task_success']}")


if __name__ == "__main__":
    main()
