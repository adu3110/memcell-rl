"""CRUD helpers for MemoryCellORM."""

import uuid
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from memcell_rl.models.enums import CellStatus
from memcell_rl.models.orm import MemoryCellORM
from memcell_rl.models.schemas import PolicyFeatures, WriteCellRequest

_DEFAULT_POLICY_FEATURES = PolicyFeatures()


def _now() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def _policy_features_dict(pf: PolicyFeatures | None) -> dict[str, float]:
    base = _DEFAULT_POLICY_FEATURES.model_dump()
    if pf is not None:
        base.update(pf.model_dump())
    return base


def create_cell(db: Session, req: WriteCellRequest) -> MemoryCellORM:
    now = _now()
    cell = MemoryCellORM(
        cell_id=str(uuid.uuid4()),
        type=req.type.value,
        scope=req.scope,
        content=req.content,
        status=req.status.value,
        confidence=req.confidence,
        sensitivity=req.sensitivity.value,
        source_refs=req.source_refs,
        valid_from=req.valid_from.replace(tzinfo=None) if req.valid_from else None,
        valid_until=req.valid_until.replace(tzinfo=None) if req.valid_until else None,
        supersedes=req.supersedes,
        contradicted_by=req.contradicted_by,
        access_count=0,
        last_retrieved_at=None,
        version=1,
        created_at=now,
        updated_at=now,
        policy_features=_policy_features_dict(req.policy_features),
    )
    db.add(cell)
    db.commit()
    db.refresh(cell)
    return cell


def get_cell(db: Session, cell_id: str) -> MemoryCellORM | None:
    return db.query(MemoryCellORM).filter(MemoryCellORM.cell_id == cell_id).first()


def get_active_cells(db: Session) -> list[MemoryCellORM]:
    """Return all cells that are not hard-deleted."""
    return (
        db.query(MemoryCellORM)
        .filter(MemoryCellORM.status != CellStatus.deleted.value)
        .all()
    )


def soft_delete_cell(db: Session, cell: MemoryCellORM) -> MemoryCellORM:
    cell.status = CellStatus.deleted.value
    cell.content = "[deleted]"
    cell.updated_at = _now()
    db.commit()
    db.refresh(cell)
    return cell


def mark_superseded(db: Session, cell: MemoryCellORM) -> MemoryCellORM:
    cell.status = CellStatus.superseded.value
    cell.updated_at = _now()
    db.commit()
    db.refresh(cell)
    return cell


def touch_cell(db: Session, cell: MemoryCellORM) -> None:
    """Increment access_count and update last_retrieved_at."""
    cell.access_count = (cell.access_count or 0) + 1
    cell.last_retrieved_at = _now()
    cell.updated_at = _now()
    db.commit()
