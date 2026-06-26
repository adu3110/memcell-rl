"""
Book 1 — Step 7: Context assembly via memcell-rl decide().

Requires: uvicorn memcell_rl.app:app --port 8000

Run: python examples/build/step07_memcell.py
"""

import json
import os
import urllib.request

MEMCELL = os.environ.get("MEMCELL_BASE", "http://localhost:8000")
SCOPE = {"case": "456"}


def post(path: str, body: dict) -> dict:
    req = urllib.request.Request(
        MEMCELL + path,
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=5) as r:
        return json.loads(r.read())


def seed() -> None:
    post("/v1/cells/write", {
        "type": "constraint",
        "scope": SCOPE,
        "content": "account_456_under_fraud_review: no_outbound_transfers",
        "policy_features": {"criticality": 0.95, "compressibility": 0.05, "staleness": 0.0, "future_utility_estimate": 0.95},
    })
    for i in range(8):
        post("/v1/cells/write", {
            "type": "episode",
            "scope": SCOPE,
            "content": f"turn {i} filler " + "z" * 100,
            "policy_features": {"criticality": 0.1, "compressibility": 0.9, "staleness": 0.5, "future_utility_estimate": 0.1},
        })


def fetch_context(task: str, budget: int) -> str:
    decision = post("/v1/cells/decide", {"query": task, "scope": SCOPE, "budget_tokens": budget, "k": 10})
    lines = []
    for sel in decision["selected_cells"]:
        with urllib.request.urlopen(f"{MEMCELL}/v1/cells/{sel['cell_id']}", timeout=5) as r:
            cell = json.loads(r.read())
        tag = "CONSTRAINT" if sel["mode"] == "constraint" else "CONTEXT"
        lines.append(f"{tag}: {cell['content'][:80]}")
    print(f"  suppressed: {len(decision.get('suppressed_cells', []))} cells")
    return "\n".join(lines)


if __name__ == "__main__":
    task = "Review account 456 for fraud"
    seed()
    for budget in [100, 400, 800]:
        print(f"\nbudget_tokens={budget}:")
        ctx = fetch_context(task, budget)
        print(ctx)
        print(f"  → {len(ctx)} chars, constraint present={'no_outbound' in ctx}")
