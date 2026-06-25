"""Create and update MemoryTransition records."""

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.orm import Session

from memcell_rl.models.orm import MemoryTransitionORM


def _now() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def create_transition(
    db: Session,
    query_id: str,
    state: dict[str, Any],
    action: dict[str, Any],
) -> MemoryTransitionORM:
    transition = MemoryTransitionORM(
        transition_id=str(uuid.uuid4()),
        query_id=query_id,
        state=state,
        action=action,
        reward=None,
        next_state=None,
        created_at=_now(),
        completed_at=None,
    )
    db.add(transition)
    db.commit()
    db.refresh(transition)
    return transition


def complete_transition(
    db: Session,
    transition: MemoryTransitionORM,
    reward: dict[str, Any],
    next_state: dict[str, Any],
) -> MemoryTransitionORM:
    transition.reward = reward
    transition.next_state = next_state
    transition.completed_at = _now()
    db.commit()
    db.refresh(transition)
    return transition


def get_transition(db: Session, transition_id: str) -> MemoryTransitionORM | None:
    return (
        db.query(MemoryTransitionORM)
        .filter(MemoryTransitionORM.transition_id == transition_id)
        .first()
    )


def list_transitions(
    db: Session, limit: int = 100, offset: int = 0
) -> list[MemoryTransitionORM]:
    return (
        db.query(MemoryTransitionORM)
        .order_by(MemoryTransitionORM.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )


def list_completed_transitions(db: Session) -> list[MemoryTransitionORM]:
    return (
        db.query(MemoryTransitionORM)
        .filter(MemoryTransitionORM.completed_at.isnot(None))
        .order_by(MemoryTransitionORM.created_at.desc())
        .all()
    )
