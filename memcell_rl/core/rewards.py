"""Scalar reward computation for RL transitions."""

from memcell_rl.models.schemas import FeedbackRequest


def compute_reward(req: FeedbackRequest) -> dict:
    reward_value = (1.0 if req.task_success else -1.0)
    if req.unsafe_action:
        reward_value -= 2.0
    if req.stale_memory_error:
        reward_value -= 1.0
    reward_value -= 0.0001 * req.tokens_used
    reward_value -= 0.001 * req.latency_ms

    return {
        "reward_value": round(reward_value, 6),
        "task_success": req.task_success,
        "unsafe_action": req.unsafe_action,
        "stale_memory_error": req.stale_memory_error,
        "tokens_used": req.tokens_used,
        "latency_ms": req.latency_ms,
    }
