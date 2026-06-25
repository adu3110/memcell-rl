"""Append-only event log."""

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.orm import Session

from memcell_rl.models.enums import EventType
from memcell_rl.models.orm import MemoryEventORM


def _now() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def log_event(
    db: Session,
    event_type: EventType,
    cell_ids: list[str],
    payload: dict[str, Any],
    query_id: str | None = None,
) -> MemoryEventORM:
    event = MemoryEventORM(
        event_id=str(uuid.uuid4()),
        timestamp=_now(),
        event_type=event_type.value,
        cell_ids=cell_ids,
        query_id=query_id,
        payload=payload,
    )
    db.add(event)
    db.commit()
    db.refresh(event)
    return event
