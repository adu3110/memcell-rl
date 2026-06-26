"""
Book 1 — Step 9: Stop conditions — duplicate calls, permissions, max steps.

Run: python examples/build/step09_stops.py
"""

import json
from dataclasses import dataclass


@dataclass
class ToolResult:
    success: bool
    error: str | None = None


class ToolRegistry:
    def __init__(self, permissions: set[str]):
        self.permissions = permissions

    def run(self, name: str, args: dict) -> ToolResult:
        if name == "flagAccount" and "write:accounts" not in self.permissions:
            return ToolResult(success=False, error="permission_denied: write:accounts required")
        return ToolResult(success=True)


MAX_STEPS = 5
seen: set[str] = set()
registry = ToolRegistry(permissions={"read:accounts"})  # no write

script = [
    ("getAccount", {"accountId": "456"}),
    ("getAccount", {"accountId": "456"}),  # duplicate
    ("flagAccount", {"accountId": "456"}),
]

for step in range(MAX_STEPS):
    if step >= len(script):
        print(f"step {step}: ESCALATED:max_steps_exceeded")
        break
    tool, args = script[step]
    sig = json.dumps({"tool": tool, "args": args}, sort_keys=True)
    if sig in seen:
        print(f"step {step}: ESCALATED:duplicate_tool_call")
        break
    seen.add(sig)
    result = registry.run(tool, args)
    if not result.success:
        print(f"step {step}: {tool} → ESCALATED:tool_error:{result.error}")
        break
    print(f"step {step}: {tool} → ok")
