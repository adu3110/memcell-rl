"""Baseline policy classes for the MemoryControlEnv."""

from typing import Any


class BasePolicy:
    """Abstract base.  Subclasses implement decide()."""

    def decide(
        self,
        cells: list[dict[str, Any]],
        query: str = "",
        budget_tokens: int = 2000,
    ) -> dict[str, str]:
        """Return {cell_id: action_name} for each cell."""
        raise NotImplementedError


class KeepAllPolicy(BasePolicy):
    """Keep every cell regardless of features. Useful as a no-op baseline."""

    def decide(
        self,
        cells: list[dict[str, Any]],
        query: str = "",
        budget_tokens: int = 2000,
    ) -> dict[str, str]:
        return {c["cell_id"]: "keep" for c in cells}


class TTLPolicy(BasePolicy):
    """
    Time-to-live policy: suppress cells that exceed a staleness threshold,
    keep the rest.
    """

    def __init__(self, staleness_threshold: float = 0.7) -> None:
        self.staleness_threshold = staleness_threshold

    def decide(
        self,
        cells: list[dict[str, Any]],
        query: str = "",
        budget_tokens: int = 2000,
    ) -> dict[str, str]:
        actions: dict[str, str] = {}
        for c in cells:
            pf = c.get("policy_features", {})
            staleness = pf.get("staleness", 0.0)
            if staleness >= self.staleness_threshold:
                actions[c["cell_id"]] = "decay"
            else:
                actions[c["cell_id"]] = "keep"
        return actions


class AccessFrequencyPolicy(BasePolicy):
    """
    Promote frequently-accessed cells; decay low-access cells.
    Uses access_count from the cell snapshot.
    """

    def __init__(self, promote_threshold: int = 5, decay_threshold: int = 1) -> None:
        self.promote_threshold = promote_threshold
        self.decay_threshold = decay_threshold

    def decide(
        self,
        cells: list[dict[str, Any]],
        query: str = "",
        budget_tokens: int = 2000,
    ) -> dict[str, str]:
        actions: dict[str, str] = {}
        for c in cells:
            access_count = c.get("access_count", 0)
            if access_count >= self.promote_threshold:
                actions[c["cell_id"]] = "promote"
            elif access_count <= self.decay_threshold:
                actions[c["cell_id"]] = "decay"
            else:
                actions[c["cell_id"]] = "keep"
        return actions


class BaselineV0Policy(BasePolicy):
    """
    Python-native version of the baseline_v0 HTTP policy.
    Mirrors the rule logic in memcell_rl.core.policy without DB access.
    """

    CONSTRAINT_CRITICALITY_THRESHOLD = 0.7

    def decide(
        self,
        cells: list[dict[str, Any]],
        query: str = "",
        budget_tokens: int = 2000,
    ) -> dict[str, str]:
        actions: dict[str, str] = {}
        remaining = budget_tokens

        # Sort: constraints first, then by criticality desc
        def sort_key(c: dict[str, Any]) -> tuple:
            pf = c.get("policy_features", {})
            is_constraint = c.get("type") == "constraint"
            return (is_constraint, pf.get("criticality", 0.0), pf.get("future_utility_estimate", 0.0))

        sorted_cells = sorted(cells, key=sort_key, reverse=True)

        for c in sorted_cells:
            status = c.get("status", "active")
            cell_id = c["cell_id"]
            pf = c.get("policy_features", {})
            criticality = pf.get("criticality", 0.0)

            if status in ("deleted", "superseded"):
                actions[cell_id] = "suppress"
                continue

            if status == "quarantined":
                actions[cell_id] = "reverify_before_use"
                continue

            tokens = max(1, len(c.get("content", "")) // 4)
            if remaining - tokens < 0:
                actions[cell_id] = "suppress"
                continue

            if c.get("type") == "constraint" and criticality >= self.CONSTRAINT_CRITICALITY_THRESHOLD:
                actions[cell_id] = "retrieve_as_constraint"
            elif c.get("type") in ("episode", "reflection"):
                actions[cell_id] = "retrieve_as_background"
            else:
                actions[cell_id] = "retrieve_as_context"

            remaining -= tokens

        return actions
