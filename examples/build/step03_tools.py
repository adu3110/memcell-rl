"""
Book 1 — Step 3: Tool registry — name, dispatch, structured result.

Run: python examples/build/step03_tools.py
"""

from dataclasses import dataclass


ACCOUNTS = {"456": {"account_id": "456", "balance_usd": 142.50, "status": "active"}}
TRANSACTIONS = {"456": [{"id": "tx1", "amount": 45.0}, {"id": "tx2", "amount": 12.5}]}


@dataclass
class ToolResult:
    success: bool
    data: dict | None = None
    error: str | None = None


class ToolRegistry:
    def run(self, name: str, args: dict) -> ToolResult:
        if name == "getAccount":
            aid = args.get("accountId", "")
            if aid not in ACCOUNTS:
                return ToolResult(success=False, error=f"account_not_found:{aid}")
            return ToolResult(success=True, data=ACCOUNTS[aid])
        if name == "getTransactions":
            aid = args.get("accountId", "")
            if aid not in TRANSACTIONS:
                return ToolResult(success=False, error=f"no_transactions:{aid}")
            return ToolResult(success=True, data={"transactions": TRANSACTIONS[aid]})
        return ToolResult(success=False, error=f"unknown_tool:{name}")


registry = ToolRegistry()
for tool, args in [
    ("getAccount", {"accountId": "456"}),
    ("getTransactions", {"accountId": "456"}),
    ("flagAccount", {"accountId": "456"}),  # not registered yet
]:
    result = registry.run(tool, args)
    print(f"{tool}: success={result.success}  data={result.data}  error={result.error}")
