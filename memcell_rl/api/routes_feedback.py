"""Feedback endpoint — attach reward to a transition."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from memcell_rl.core.event_log import log_event
from memcell_rl.core.rewards import compute_reward
from memcell_rl.core.transitions import complete_transition, get_transition
from memcell_rl.db import get_db
from memcell_rl.models.enums import EventType
from memcell_rl.models.schemas import FeedbackRequest, FeedbackResponse

router = APIRouter(prefix="/v1/cells", tags=["feedback"])


@router.post("/feedback", response_model=FeedbackResponse)
def feedback(req: FeedbackRequest, db: Session = Depends(get_db)) -> FeedbackResponse:
    transition = get_transition(db, req.transition_id)
    if transition is None:
        raise HTTPException(status_code=404, detail="Transition not found")

    reward = compute_reward(req)
    next_state = {
        "feedback_received": True,
        "task_success": req.task_success,
        "unsafe_action": req.unsafe_action,
        "stale_memory_error": req.stale_memory_error,
    }

    transition = complete_transition(db, transition, reward, next_state)

    log_event(
        db,
        EventType.feedback_received,
        [],
        {
            "transition_id": req.transition_id,
            "query_id": req.query_id,
            "reward_value": reward["reward_value"],
        },
        query_id=req.query_id,
    )

    return FeedbackResponse(
        transition_id=transition.transition_id,
        reward_value=reward["reward_value"],
        completed_at=transition.completed_at,
    )
