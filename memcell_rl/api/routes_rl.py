"""RL endpoints: transitions list and dataset export."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from memcell_rl.core.transitions import list_completed_transitions, list_transitions
from memcell_rl.db import get_db
from memcell_rl.models.schemas import MemoryTransitionSchema, RLDatasetEntry

router = APIRouter(prefix="/v1/rl", tags=["rl"])


@router.get("/transitions", response_model=list[MemoryTransitionSchema])
def get_transitions(
    limit: int = Query(default=100, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
) -> list[MemoryTransitionSchema]:
    rows = list_transitions(db, limit=limit, offset=offset)
    return [MemoryTransitionSchema.model_validate(r) for r in rows]


@router.get("/dataset", response_model=list[RLDatasetEntry])
def get_dataset(db: Session = Depends(get_db)) -> list[RLDatasetEntry]:
    """Return completed transitions only (those with reward attached)."""
    rows = list_completed_transitions(db)
    return [
        RLDatasetEntry(
            transition_id=r.transition_id,
            state=r.state,
            action=r.action,
            reward=r.reward,
            next_state=r.next_state,
        )
        for r in rows
    ]
