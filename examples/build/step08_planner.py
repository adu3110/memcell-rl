"""
Book 1 — Step 8: Planner as a replaceable function (scripted vs future LLM).

Run: python examples/build/step08_planner.py
"""

from dataclasses import dataclass
from enum import Enum


class ActionType(str, Enum):
    TOOL_CALL = "tool_call"
    ANSWER = "answer"


@dataclass
class Action:
    type: ActionType
    tool: str | None = None
    args: dict | None = None
    text: str | None = None


def scripted_planner(step: int, tools_used: list[str]) -> Action:
    script = [
        Action(ActionType.TOOL_CALL, "getAccount", {"accountId": "456"}),
        Action(ActionType.TOOL_CALL, "getTransactions", {"accountId": "456"}),
        Action(ActionType.ANSWER, text="Case closed."),
    ]
    return script[step]


def bad_planner(step: int, tools_used: list[str]) -> Action:
    if step == 0:
        return Action(ActionType.TOOL_CALL, "flagAccount", {"accountId": "456"})
    return Action(ActionType.ANSWER, text="Flagged.")


def run_loop(planner, label: str) -> None:
    tools_used: list[str] = []
    print(f"\n--- {label} ---")
    for step in range(5):
        action = planner(step, tools_used)
        print(f"step {step}: {action.type.value} {action.tool or action.text}")
        if action.type == ActionType.TOOL_CALL:
            tools_used.append(action.tool or "")
        else:
            break
    print(f"tools_used: {tools_used}")


run_loop(scripted_planner, "good planner")
run_loop(bad_planner, "bad planner — flag before lookup")
