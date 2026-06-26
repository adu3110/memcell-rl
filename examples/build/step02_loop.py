"""
Book 1 — Step 2: Minimal loop — hardcoded actions, inline tools.

Run: python examples/build/step02_loop.py
"""

ACCOUNTS = {"456": {"balance_usd": 142.50, "status": "active"}}


def get_account(account_id: str) -> dict:
    return ACCOUNTS[account_id]


task = "Review account 456 for fraud indicators."
script = [
    ("getAccount", {"accountId": "456"}),
    ("getTransactions", {"accountId": "456"}),  # not implemented yet — will fail
    ("answer", {"text": "Case closed."}),
]

print(f"Task: {task}\n")

for step, (name, args) in enumerate(script):
    print(f"step {step}: {name} {args}")
    if name == "getAccount":
        data = get_account(args["accountId"])
        print(f"  → {data}")
    elif name == "answer":
        print(f"  → {args['text']}")
        break
    else:
        print("  → ERROR: tool not defined")
        break

print("\nWe have a loop shape. Next: a tool registry so dispatch is explicit.")
