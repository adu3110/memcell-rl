"""Tests: RL dataset export — only completed transitions."""

from tests.conftest import write_cell


def _full_cycle(client, task_success: bool = True) -> str:
    """Write a cell, decide, feedback.  Returns transition_id."""
    write_cell(client)

    r = client.post("/v1/cells/decide", json={
        "query": "test",
        "scope": {"user": "u1"},
        "budget_tokens": 2000,
        "k": 5,
    })
    data = r.json()

    client.post("/v1/cells/feedback", json={
        "query_id": data["query_id"],
        "transition_id": data["transition_id"],
        "task_success": task_success,
        "unsafe_action": False,
        "stale_memory_error": False,
        "tokens_used": 100,
        "latency_ms": 50,
    })
    return data["transition_id"]


def test_dataset_returns_only_completed_transitions(client):
    write_cell(client)

    # Create one incomplete transition
    r = client.post("/v1/cells/decide", json={
        "query": "incomplete",
        "scope": {"user": "u1"},
        "budget_tokens": 2000,
        "k": 5,
    })
    incomplete_id = r.json()["transition_id"]

    # Create one complete transition
    complete_id = _full_cycle(client)

    r = client.get("/v1/rl/dataset")
    assert r.status_code == 200
    dataset = r.json()

    ids = [d["transition_id"] for d in dataset]
    assert complete_id in ids
    assert incomplete_id not in ids


def test_dataset_entry_has_all_rl_fields(client):
    _full_cycle(client)

    r = client.get("/v1/rl/dataset")
    assert len(r.json()) >= 1
    entry = r.json()[0]

    assert "transition_id" in entry
    assert "state" in entry
    assert "action" in entry
    assert "reward" in entry
    assert "next_state" in entry


def test_dataset_reward_structure(client):
    _full_cycle(client, task_success=True)

    r = client.get("/v1/rl/dataset")
    reward = r.json()[0]["reward"]

    assert "reward_value" in reward
    assert "task_success" in reward
    assert reward["task_success"] is True


def test_empty_dataset_when_no_feedback(client):
    write_cell(client)
    client.post("/v1/cells/decide", json={
        "query": "no feedback",
        "scope": {"user": "u1"},
        "budget_tokens": 2000,
        "k": 5,
    })

    r = client.get("/v1/rl/dataset")
    assert r.json() == []
