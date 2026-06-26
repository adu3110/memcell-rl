"""
casebot_regulated.py — Regulated case-resolution agent (Book 1 running example).

Case 456: review account for fraud indicators in a financially regulated workflow.
Runs without an LLM in --dry-run mode (scripted policy). With --live, calls OpenAI.

Memory: memcell-rl HTTP API (start server first: uvicorn memcell_rl.app:app --port 8000)

Usage:
    python examples/casebot_regulated.py --dry-run
    python examples/casebot_regulated.py --dry-run --bad-run   # compliance failure demo
    OPENAI_API_KEY=sk-... python examples/casebot_regulated.py --live

Companion book: Building Agentic Systems — Book 1
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Callable

MEMCELL_BASE = os.environ.get("MEMCELL_BASE", "http://localhost:8000")
CASE_SCOPE = {"case": "456"}
MAX_STEPS = 12

# ── Fixture: regulated case data ─────────────────────────────────────────────

ACCOUNTS = {
    "456": {
        "account_id": "456",
        "status": "active",
        "balance_usd": 142.50,
        "fraud_review": True,
    }
}

TRANSACTIONS = {
    "456": [
        {"id": "tx1", "amount": 45.00, "status": "settled"},
        {"id": "tx2", "amount": 12.50, "status": "settled"},
    ]
}


class ActionType(str, Enum):
    TOOL_CALL = "tool_call"
    ANSWER = "answer"
    ESCALATE = "escalate"


@dataclass
class Action:
    type: ActionType
    tool: str | None = None
    args: dict[str, Any] = field(default_factory=dict)
    text: str | None = None
    reason: str | None = None


@dataclass
class ToolResult:
    success: bool
    data: dict[str, Any] | None = None
    error: str | None = None


# ── Trajectory ─────────────────────────────────────────────────────────────────

@dataclass
class TrajectoryStep:
    step: int
    action_type: str
    action: dict[str, Any]
    result: dict[str, Any] | None = None
    timestamp: str = ""


@dataclass
class Trajectory:
    case_id: str
    task: str
    steps: list[TrajectoryStep] = field(default_factory=list)
    outcome: str = ""

    def log(self, step: int, action: Action, result: ToolResult | None = None) -> None:
        self.steps.append(
            TrajectoryStep(
                step=step,
                action_type=action.type.value,
                action={"type": action.type.value, "tool": action.tool, "args": action.args, "text": action.text},
                result=asdict(result) if result else None,
                timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            )
        )

    def tools_used(self) -> list[str]:
        out: list[str] = []
        for s in self.steps:
            if s.action_type == ActionType.TOOL_CALL.value and s.action.get("tool"):
                out.append(s.action["tool"])
        return out

    def save(self, path: str | Path) -> None:
        payload = {
            "case_id": self.case_id,
            "task": self.task,
            "outcome": self.outcome,
            "tools_used": self.tools_used(),
            "step_count": len(self.steps),
            "steps": [asdict(s) for s in self.steps],
        }
        Path(path).write_text(json.dumps(payload, indent=2))


def lookup_before_flag(traj: Trajectory) -> tuple[bool, str]:
    tools = traj.tools_used()
    if "flagAccount" not in tools:
        return True, "no flag attempted"
    if "getAccount" not in tools:
        return False, "flagAccount without prior getAccount"
    return tools.index("getAccount") < tools.index("flagAccount"), "ok"


def bounded_steps(traj: Trajectory, limit: int = MAX_STEPS) -> tuple[bool, str]:
    ok = len(traj.steps) <= limit
    return ok, f"{len(traj.steps)} steps (limit {limit})"


PROPERTY_CHECKS: list[tuple[str, Callable[[Trajectory], tuple[bool, str]]]] = [
    ("lookup_before_flag", lookup_before_flag),
    ("bounded_steps", bounded_steps),
]


# ── Tools ──────────────────────────────────────────────────────────────────────

DESTRUCTIVE_TOOLS = {"flagAccount"}
READ_TOOLS = {"getAccount", "getTransactions"}


class ToolRegistry:
    def __init__(self, permissions: set[str]):
        self.permissions = permissions

    def run(self, name: str, args: dict[str, Any]) -> ToolResult:
        if name in DESTRUCTIVE_TOOLS and "write:accounts" not in self.permissions:
            return ToolResult(success=False, error="permission_denied: write:accounts required")
        if name in READ_TOOLS and "read:accounts" not in self.permissions:
            return ToolResult(success=False, error="permission_denied: read:accounts required")

        if name == "getAccount":
            aid = str(args.get("accountId", ""))
            if aid not in ACCOUNTS:
                return ToolResult(success=False, error=f"account_not_found:{aid}")
            return ToolResult(success=True, data=ACCOUNTS[aid])

        if name == "getTransactions":
            aid = str(args.get("accountId", ""))
            if aid not in TRANSACTIONS:
                return ToolResult(success=False, error=f"no_transactions:{aid}")
            return ToolResult(success=True, data={"transactions": TRANSACTIONS[aid]})

        if name == "flagAccount":
            aid = str(args.get("accountId", ""))
            reason = args.get("reason", "unspecified")
            return ToolResult(success=True, data={"account_id": aid, "flagged": True, "reason": reason})

        return ToolResult(success=False, error=f"unknown_tool:{name}")


# ── memcell-rl client ──────────────────────────────────────────────────────────

def memcell_post(path: str, body: dict) -> dict:
    data = json.dumps(body).encode()
    req = urllib.request.Request(
        f"{MEMCELL_BASE}{path}",
        data=data,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=5) as r:
        return json.loads(r.read())


def seed_case_memory() -> None:
    """Load fraud-review constraint for case 456 into memcell-rl."""
    memcell_post("/v1/cells/write", {
        "type": "constraint",
        "scope": CASE_SCOPE,
        "content": "account_456_under_fraud_review: no_outbound_transfers until review closes",
        "confidence": 0.99,
        "sensitivity": "restricted",
        "source_refs": ["policy:fraud_engine"],
        "policy_features": {
            "criticality": 0.95,
            "compressibility": 0.05,
            "staleness": 0.0,
            "future_utility_estimate": 0.95,
        },
    })


def fetch_memcell_context(task: str) -> str:
    decision = memcell_post("/v1/cells/decide", {
        "query": task,
        "scope": CASE_SCOPE,
        "budget_tokens": 800,
        "k": 10,
    })
    lines: list[str] = []
    for sel in decision["selected_cells"]:
        req = urllib.request.Request(f"{MEMCELL_BASE}/v1/cells/{sel['cell_id']}")
        with urllib.request.urlopen(req, timeout=5) as r:
            c = json.loads(r.read())
        if sel["mode"] == "constraint":
            lines.append(f"CONSTRAINT: {c['content']}")
        else:
            lines.append(f"CONTEXT: {c['content']}")
    return "\n".join(lines) if lines else "(no cells selected)"


# ── Agent loop ─────────────────────────────────────────────────────────────────

class AgentLoop:
    def __init__(
        self,
        task: str,
        tools: ToolRegistry,
        planner: Callable[[int, Trajectory, str], Action],
        memory_context: str = "",
    ):
        self.task = task
        self.tools = tools
        self.planner = planner
        self.memory_context = memory_context
        self.seen_calls: set[str] = set()
        self.trajectory = Trajectory(case_id="456", task=task)

    def run(self) -> str:
        for step in range(MAX_STEPS):
            action = self.planner(step, self.trajectory, self.memory_context)

            if action.type == ActionType.TOOL_CALL:
                sig = json.dumps({"tool": action.tool, "args": action.args}, sort_keys=True)
                if sig in self.seen_calls:
                    self.trajectory.outcome = f"ESCALATED:duplicate_tool_call at step {step}"
                    self.trajectory.log(step, Action(type=ActionType.ESCALATE, reason="duplicate_tool_call"))
                    return self.trajectory.outcome
                self.seen_calls.add(sig)

                result = self.tools.run(action.tool or "", action.args)
                self.trajectory.log(step, action, result)
                if not result.success:
                    self.trajectory.outcome = f"ESCALATED:tool_error:{result.error}"
                    return self.trajectory.outcome

            elif action.type == ActionType.ANSWER:
                self.trajectory.log(step, action)
                self.trajectory.outcome = action.text or ""
                return self.trajectory.outcome

            elif action.type == ActionType.ESCALATE:
                self.trajectory.log(step, action)
                self.trajectory.outcome = f"ESCALATED:{action.reason}"
                return self.trajectory.outcome

        self.trajectory.outcome = f"ESCALATED:max_steps_exceeded"
        return self.trajectory.outcome


# ── Planners ───────────────────────────────────────────────────────────────────

def good_run_planner(step: int, traj: Trajectory, memory: str) -> Action:
    """Compliant path: lookup → transactions → close case."""
    _ = memory
    script = [
        Action(type=ActionType.TOOL_CALL, tool="getAccount", args={"accountId": "456"}),
        Action(type=ActionType.TOOL_CALL, tool="getTransactions", args={"accountId": "456"}),
        Action(
            type=ActionType.ANSWER,
            text="Account 456 reviewed. Balance $142.50. Two settled transactions. No fraud indicators. Case closed.",
        ),
    ]
    return script[step] if step < len(script) else Action(type=ActionType.ESCALATE, reason="planner_exhausted")


def bad_run_planner(step: int, traj: Trajectory, memory: str) -> Action:
    """Compliance failure: flag without lookup (Run A from the book)."""
    _ = memory
    if step == 0:
        return Action(type=ActionType.TOOL_CALL, tool="flagAccount", args={"accountId": "456", "reason": "suspicious"})
    return Action(type=ActionType.ANSWER, text="Flagged account 456.")


# ── Main ───────────────────────────────────────────────────────────────────────

def run_case(*, bad_run: bool = False, export: str = "logs/case456.json") -> int:
    task = "Review account 456 for fraud indicators. Flag only if suspicious after full lookup."

    try:
        seed_case_memory()
        memory_ctx = fetch_memcell_context(task)
        print(f"[memcell] context loaded ({len(memory_ctx)} chars)")
    except (urllib.error.URLError, TimeoutError) as e:
        print(f"[memcell] server not reachable ({e}); continuing without live memory")
        memory_ctx = "CONSTRAINT: account_456_under_fraud_review: no_outbound_transfers"

    registry = ToolRegistry(permissions={"read:accounts", "read:transactions"})
    planner = bad_run_planner if bad_run else good_run_planner

    loop = AgentLoop(task, registry, planner, memory_context=memory_ctx)
    outcome = loop.run()

    Path(export).parent.mkdir(parents=True, exist_ok=True)
    loop.trajectory.save(export)

    print(f"\nOutcome: {outcome}")
    print(f"Tools:   {loop.trajectory.tools_used()}")
    print(f"Steps:   {len(loop.trajectory.steps)}")
    print(f"Saved:   {export}")

    print("\nProperty checks:")
    all_ok = True
    for name, fn in PROPERTY_CHECKS:
        ok, msg = fn(loop.trajectory)
        print(f"  {'PASS' if ok else 'FAIL'}  {name}: {msg}")
        all_ok = all_ok and ok

    return 0 if all_ok else 1


def main() -> None:
    parser = argparse.ArgumentParser(description="CaseBot — regulated case-resolution agent")
    parser.add_argument("--dry-run", action="store_true", default=True, help="Scripted planner (default)")
    parser.add_argument("--bad-run", action="store_true", help="Demo compliance failure (flag without lookup)")
    parser.add_argument("--export", default="logs/case456.json", help="Trajectory export path")
    args = parser.parse_args()

    if not args.dry_run:
        print("--live mode not yet wired; use --dry-run for Book 1 walkthrough")
        sys.exit(1)

    sys.exit(run_case(bad_run=args.bad_run, export=args.export))


if __name__ == "__main__":
    main()
