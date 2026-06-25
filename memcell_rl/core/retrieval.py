"""Deterministic lexical retrieval scorer — no embeddings."""

from datetime import UTC, datetime
from typing import Any

from sqlalchemy.orm import Session

from memcell_rl.core.cell_store import get_active_cells, touch_cell
from memcell_rl.models.enums import CellStatus, CellType
from memcell_rl.models.orm import MemoryCellORM


def _now() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def _is_expired(cell: MemoryCellORM) -> bool:
    if cell.valid_until is None:
        return False
    return cell.valid_until < _now()


def lexical_overlap(query: str, content: str) -> float:
    """Jaccard similarity over word sets."""
    q_words = set(query.lower().split())
    c_words = set(content.lower().split())
    if not q_words or not c_words:
        return 0.0
    return len(q_words & c_words) / len(q_words | c_words)


def score_cell(query: str, cell: MemoryCellORM) -> float:
    pf: dict[str, float] = cell.policy_features or {}
    criticality = pf.get("criticality", 0.0)
    future_utility = pf.get("future_utility_estimate", 0.0)
    staleness = pf.get("staleness", 0.0)

    return (
        lexical_overlap(query, cell.content)
        + 0.5 * cell.confidence
        + 0.5 * criticality
        + 0.3 * future_utility
        - 0.5 * staleness
    )


def scope_matches(cell_scope: dict[str, Any], query_scope: dict[str, Any]) -> bool:
    """Return True if every key in query_scope is present and equal in cell_scope."""
    for key, value in query_scope.items():
        if cell_scope.get(key) != value:
            return False
    return True


def retrieve_cells(
    db: Session,
    query: str,
    scope: dict[str, Any],
    types: list[CellType] | None,
    k: int,
    update_access: bool = True,
) -> tuple[list[MemoryCellORM], list[float]]:
    """
    Score and rank cells.  Returns (cells, scores) sorted descending by score.
    Ignores deleted and expired cells.  Filters by scope and type if provided.
    """
    candidates = get_active_cells(db)
    scored: list[tuple[MemoryCellORM, float]] = []

    for cell in candidates:
        # Skip deleted
        if cell.status == CellStatus.deleted.value:
            continue
        # Skip expired
        if _is_expired(cell):
            continue
        # Scope filter
        if not scope_matches(cell.scope, scope):
            continue
        # Type filter
        if types is not None and cell.type not in [t.value for t in types]:
            continue

        scored.append((cell, score_cell(query, cell)))

    scored.sort(key=lambda x: x[1], reverse=True)
    top = scored[:k]

    if update_access:
        for cell, _ in top:
            touch_cell(db, cell)

    cells = [c for c, _ in top]
    scores = [s for _, s in top]
    return cells, scores
