"""Dataset utilities for offline RL training."""

from typing import Any

from sqlalchemy.orm import Session

from memcell_rl.core.transitions import list_completed_transitions


def export_dataset(db: Session) -> list[dict[str, Any]]:
    """Return completed transitions as a list of (s, a, r, s') dicts."""
    transitions = list_completed_transitions(db)
    return [
        {
            "transition_id": t.transition_id,
            "state": t.state,
            "action": t.action,
            "reward": t.reward,
            "next_state": t.next_state,
        }
        for t in transitions
    ]
