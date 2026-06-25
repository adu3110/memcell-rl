"""Decide endpoint — RL-native memory selection."""

import uuid
from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from memcell_rl.core.event_log import log_event
from memcell_rl.core.policy import apply_baseline_v0, policy_description, policy_info
from memcell_rl.core.retrieval import retrieve_cells
from memcell_rl.core.transitions import create_transition
from memcell_rl.db import get_db
from memcell_rl.models.enums import EventType
from memcell_rl.models.orm import MemoryCellORM
from memcell_rl.models.schemas import DecideRequest, DecideResponse

router = APIRouter(prefix="/v1/cells", tags=["decide"])


def _cell_state_snapshot(cell: MemoryCellORM, retrieval_score: float) -> dict[str, Any]:
    return {
        "cell_id": cell.cell_id,
        "type": cell.type,
        "status": cell.status,
        "confidence": cell.confidence,
        "sensitivity": cell.sensitivity,
        "policy_features": cell.policy_features,
        "retrieval_score": retrieval_score,
    }


@router.post("/decide", response_model=DecideResponse)
def decide(req: DecideRequest, db: Session = Depends(get_db)) -> DecideResponse:
    query_id = str(uuid.uuid4())

    # Retrieve candidate cells (no access_count update — decide does its own accounting)
    candidates, scores = retrieve_cells(
        db, req.query, req.scope, types=None, k=req.k, update_access=False
    )

    candidate_snapshots = [
        _cell_state_snapshot(cell, score) for cell, score in zip(candidates, scores)
    ]

    state: dict[str, Any] = {
        "query": req.query,
        "task_type": req.task_type,
        "scope": req.scope,
        "budget_tokens": req.budget_tokens,
        "candidate_cells": candidate_snapshots,
    }

    selected, suppressed = apply_baseline_v0(list(zip(candidates, scores)), req.budget_tokens)

    action: dict[str, Any] = {
        "selected": [s.model_dump() for s in selected],
        "suppressed": [s.model_dump() for s in suppressed],
        "policy_id": "baseline_v0",
    }

    transition = create_transition(db, query_id, state, action)

    log_event(
        db,
        EventType.decide_cells,
        [s.cell_id for s in selected],
        {
            "query_id": query_id,
            "transition_id": transition.transition_id,
            "selected_count": len(selected),
            "suppressed_count": len(suppressed),
        },
        query_id=query_id,
    )

    return DecideResponse(
        query_id=query_id,
        selected_cells=selected,
        suppressed_cells=suppressed,
        policy=policy_info(),
        transition_id=transition.transition_id,
    )


@router.get("/policies/baseline")
def get_baseline_policy() -> dict:
    return policy_description()
