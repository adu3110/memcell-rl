"""baseline_v0 policy — deterministic rule-based memory decision."""

from datetime import UTC, datetime
from typing import Any

from memcell_rl.models.enums import CellStatus, CellType, RetrievalMode, Sensitivity
from memcell_rl.models.orm import MemoryCellORM
from memcell_rl.models.schemas import PolicyInfo, SelectedCell, SuppressedCell

POLICY_ID = "baseline_v0"
POLICY_TYPE = "rule_based"
POLICY_CONFIDENCE = 0.75


def _now() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def _is_expired(cell: MemoryCellORM) -> bool:
    if cell.valid_until is None:
        return False
    return cell.valid_until < _now()


def _token_estimate(cell: MemoryCellORM) -> int:
    return max(1, len(cell.content) // 4)


def _priority_key(item: tuple[MemoryCellORM, str, float]) -> tuple:
    """Sort key for budget enforcement (descending)."""
    cell, mode, score = item
    pf: dict[str, float] = cell.policy_features or {}
    is_constraint = 1 if mode == RetrievalMode.constraint.value else 0
    criticality = pf.get("criticality", 0.0)
    future_utility = pf.get("future_utility_estimate", 0.0)
    return (is_constraint, criticality, future_utility, score, cell.confidence)


def apply_baseline_v0(
    candidates: list[tuple[MemoryCellORM, float]],
    budget_tokens: int,
) -> tuple[list[SelectedCell], list[SuppressedCell]]:
    """
    Apply baseline_v0 rules.

    Passes:
    1. Filter deleted / expired / superseded → suppress immediately.
    2. Quarantined → reverify_before_use (always included, counted against budget).
    3. Remaining active cells → assign mode, then sort by priority for budget.
    """
    selected: list[SelectedCell] = []
    suppressed: list[SuppressedCell] = []
    eligible: list[tuple[MemoryCellORM, str, float]] = []

    for cell, score in candidates:
        pf: dict[str, float] = cell.policy_features or {}
        criticality = pf.get("criticality", 0.0)

        # ── Hard suppression rules ──────────────────────────────────────────
        if cell.status == CellStatus.deleted.value:
            suppressed.append(SuppressedCell(cell_id=cell.cell_id, reason="deleted"))
            continue

        if _is_expired(cell):
            suppressed.append(SuppressedCell(cell_id=cell.cell_id, reason="expired"))
            continue

        if cell.status == CellStatus.superseded.value:
            suppressed.append(SuppressedCell(cell_id=cell.cell_id, reason="superseded"))
            continue

        # ── Quarantined → always reverify ───────────────────────────────────
        if cell.status == CellStatus.quarantined.value:
            eligible.append((cell, RetrievalMode.reverify_before_use.value, score))
            continue

        # ── Assign retrieval mode ───────────────────────────────────────────
        is_high_sensitivity = cell.sensitivity in (
            Sensitivity.high.value,
            Sensitivity.restricted.value,
        )

        if cell.type == CellType.constraint.value and criticality >= 0.7:
            mode = RetrievalMode.constraint.value
        elif is_high_sensitivity and criticality >= 0.7:
            mode = RetrievalMode.constraint.value
        elif cell.type in (CellType.episode.value, CellType.reflection.value):
            mode = RetrievalMode.context.value if criticality >= 0.7 else RetrievalMode.background.value
        else:
            mode = RetrievalMode.context.value

        eligible.append((cell, mode, score))

    # ── Budget enforcement ──────────────────────────────────────────────────
    eligible.sort(key=_priority_key, reverse=True)

    remaining = budget_tokens
    for cell, mode, score in eligible:
        tokens = _token_estimate(cell)
        if remaining - tokens < 0:
            suppressed.append(
                SuppressedCell(cell_id=cell.cell_id, reason="budget_exceeded")
            )
            continue
        remaining -= tokens
        reason = _reason_for_mode(cell, mode, score)
        selected.append(
            SelectedCell(cell_id=cell.cell_id, mode=RetrievalMode(mode), score=score, reason=reason)
        )

    return selected, suppressed


def _reason_for_mode(cell: MemoryCellORM, mode: str, score: float) -> str:
    pf: dict[str, float] = cell.policy_features or {}
    criticality = pf.get("criticality", 0.0)

    if mode == RetrievalMode.reverify_before_use.value:
        return "quarantined — must reverify before use"
    if mode == RetrievalMode.constraint.value:
        return f"high criticality constraint (criticality={criticality:.2f})"
    if mode == RetrievalMode.background.value:
        return "episode/reflection — low criticality, providing background"
    return f"active {cell.type} cell (score={score:.3f})"


def policy_info() -> PolicyInfo:
    return PolicyInfo(
        policy_id=POLICY_ID,
        policy_type=POLICY_TYPE,
        confidence=POLICY_CONFIDENCE,
    )


def policy_description() -> dict[str, Any]:
    return {
        "policy_id": POLICY_ID,
        "policy_type": POLICY_TYPE,
        "confidence": POLICY_CONFIDENCE,
        "description": (
            "Rule-based baseline. Suppresses deleted, expired, and superseded cells. "
            "Quarantined cells are always returned as reverify_before_use. "
            "Constraints and high-sensitivity cells with criticality >= 0.7 are "
            "selected as constraint mode. Budget is enforced by token estimate (len/4), "
            "prioritising constraints > criticality > future_utility > score > confidence."
        ),
        "retrieval_action_space": [m.value for m in RetrievalMode],
        "retention_action_space": [
            "keep", "decay", "compress", "merge",
            "promote", "quarantine", "supersede", "delete",
        ],
    }
