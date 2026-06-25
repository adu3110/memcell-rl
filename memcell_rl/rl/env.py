"""
MemoryControlEnv — skeleton RL environment for memory control.

No gymnasium dependency.  Implement your own policy by subclassing and
overriding `step()`.  The action and observation spaces are described
via dictionaries rather than gym.Space objects so this file has zero
external dependencies.
"""

from typing import Any


class MemoryControlEnv:
    """
    A skeleton RL environment over a set of MemoryStateCell objects.

    State: a snapshot of candidate cells with their policy_features.
    Action: a dict mapping cell_id → retrieval or retention action.
    Reward: computed externally (via /v1/cells/feedback) and injected
            into the transition log.

    This class is intentionally framework-agnostic.  Wire it to a real
    policy network, bandits library, or offline RL trainer of your choice.
    """

    def __init__(self, cells: list[dict[str, Any]] | None = None) -> None:
        self._cells: list[dict[str, Any]] = cells or []
        self._step_count = 0
        self._done = False

    def reset(self, cells: list[dict[str, Any]] | None = None) -> dict[str, Any]:
        """
        Reset the environment with a new set of candidate cells.
        Returns the initial observation.
        """
        self._cells = cells or []
        self._step_count = 0
        self._done = False
        return self._observe()

    def step(self, action: dict[str, str]) -> tuple[dict[str, Any], float, bool, dict]:
        """
        Apply an action dict {cell_id: action_name} to the current state.

        Returns (observation, reward, done, info).
        Reward is 0.0 by default; inject real rewards via the feedback endpoint.
        """
        if self._done:
            raise RuntimeError("Episode finished — call reset()")

        self._step_count += 1
        obs = self._observe()
        reward = 0.0
        done = self._step_count >= len(self._cells)
        info: dict[str, Any] = {"step": self._step_count, "action": action}
        self._done = done
        return obs, reward, done, info

    def _observe(self) -> dict[str, Any]:
        return {
            "step": self._step_count,
            "cells": [
                {
                    "cell_id": c.get("cell_id"),
                    "type": c.get("type"),
                    "status": c.get("status"),
                    "confidence": c.get("confidence"),
                    "policy_features": c.get("policy_features", {}),
                    "retrieval_score": c.get("retrieval_score", 0.0),
                }
                for c in self._cells
            ],
        }

    def observation_space_description(self) -> dict[str, Any]:
        return {
            "type": "dict",
            "fields": {
                "step": "int — current step index",
                "cells": {
                    "type": "list of cell snapshots",
                    "per_cell": {
                        "cell_id": "str",
                        "type": "CellType enum value",
                        "status": "CellStatus enum value",
                        "confidence": "float [0, 1]",
                        "policy_features": {
                            "criticality": "float [0, 1]",
                            "compressibility": "float [0, 1]",
                            "staleness": "float [0, 1]",
                            "future_utility_estimate": "float [0, 1]",
                        },
                        "retrieval_score": "float — lexical + feature score",
                    },
                },
            },
        }

    def action_space_description(self) -> dict[str, Any]:
        return {
            "type": "dict",
            "description": "Map each cell_id to one retrieval or retention action",
            "retrieval_actions": {
                "retrieve_as_context": "Include cell as context in the prompt",
                "retrieve_as_constraint": "Include cell as a hard constraint",
                "retrieve_as_background": "Include cell as low-priority background",
                "suppress": "Do not include this cell",
                "reverify_before_use": "Flag for re-verification before including",
            },
            "retention_actions": {
                "keep": "Leave cell unchanged",
                "decay": "Reduce confidence over time",
                "compress": "Summarise/shorten cell content",
                "merge": "Merge with another cell",
                "promote": "Increase criticality / confidence",
                "quarantine": "Isolate for manual review",
                "supersede": "Replace with a newer cell",
                "delete": "Soft-delete the cell",
            },
        }
