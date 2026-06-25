"""Events log endpoint."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from memcell_rl.db import get_db
from memcell_rl.models.orm import MemoryEventORM
from memcell_rl.models.schemas import MemoryEventSchema

router = APIRouter(prefix="/v1", tags=["events"])


@router.get("/events", response_model=list[MemoryEventSchema])
def list_events(
    limit: int = Query(default=100, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
) -> list[MemoryEventSchema]:
    rows = (
        db.query(MemoryEventORM)
        .order_by(MemoryEventORM.timestamp.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    return [MemoryEventSchema.model_validate(r) for r in rows]
