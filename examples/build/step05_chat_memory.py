"""
Book 1 — Step 5: Chat history as memory — watch the constraint disappear.

Run: python examples/build/step05_chat_memory.py
"""

CONSTRAINT = "POLICY: account 456 — no outbound transfers until fraud review closes"
FILLER = "tool output line with account metadata and transaction details. " * 80  # ~640 tokens worth


def context_from_chat(messages: list[str], max_chars: int = 1200) -> str:
    """Naive: keep the last max_chars of chat. Like most demos."""
    blob = "\n".join(messages)
    if len(blob) <= max_chars:
        return blob
    return "…[truncated]…\n" + blob[-max_chars:]


messages = [CONSTRAINT]
for turn in range(12):
    messages.append(FILLER)
    ctx = context_from_chat(messages)
    has_constraint = "no outbound transfers" in ctx
    print(f"turn {turn + 1:2d}: context {len(ctx):5d} chars  constraint visible={has_constraint}")
    if turn == 11 and not has_constraint:
        print("\nConstraint from turn 1 is gone. Agent can violate policy.")
        print("Fix: store constraints outside the chat transcript (step 6).")
