"""
Book 1 — Step 4: Log every step to a trajectory file.

Run: python examples/build/step04_trajectory.py
       cat logs/step04.json
"""

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path

# --- tools (from step 3) ---
ACCOUNTS = {"456": {"balance_usd": 142.50}}
TRANSACTIONS = {"456": [{"id": "tx1"}]}


@dataclass
class ToolResult:
    success: bool
    data: dict | None = None
    error: str | None = None


class ToolRegistry:
    def run(self, name: str, args: dict) -> ToolResult:
        if name == "getAccount":
            return ToolResult(success=True, data=ACCOUNTS[args["accountId"]])
        if name == "getTransactions":
            return ToolResult(success=True, data={"transactions": TRANSACTIONS[args["accountId"]]})
        return ToolResult(success=False, error=f"unknown_tool:{name}")


@dataclass
class TrajectoryStep:
    step: int
    tool: str
    args: dict
    result: dict


@dataclass
class Trajectory:
    case_id: str
    steps: list[TrajectoryStep] = field(default_factory=list)

    def log(self, step: int, tool: str, args: dict, result: ToolResult) -> None:
        self.steps.append(
            TrajectoryStep(step, tool, args, {"success": result.success, "data": result.data, "error": result.error})
        )

    def tools_used(self) -> list[str]:
        return [s.tool for s in self.steps]

    def save(self, path: str) -> None:
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        Path(path).write_text(json.dumps({"case_id": self.case_id, "steps": [asdict(s) for s in self.steps]}, indent=2))


# --- loop ---
registry = ToolRegistry()
traj = Trajectory(case_id="456")
script = [
    ("getAccount", {"accountId": "456"}),
    ("getTransactions", {"accountId": "456"}),
]

for step, (tool, args) in enumerate(script):
    result = registry.run(tool, args)
    traj.log(step, tool, args, result)
    print(f"step {step}: {tool} → success={result.success}")

out = "logs/step04.json"
traj.save(out)
print(f"\nTools used: {traj.tools_used()}")
print(f"Saved: {out}")
