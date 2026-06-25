"""Tests: feedback attaches reward to transition."""

from tests.conftest import write_cell


def test_feedback_attaches_reward(client):
    write_cell(client)

    # Trigger a decide to create a transition
    r = client.post("/v1/cells/decide", json={
        "query": "test query",
        "scope": {"user": "u1"},
        "budget_tokens": 2000,
        "k": 5,
    })
    assert r.status_code == 200
    decide_data = r.json()
    transition_id = decide_data["transition_id"]
    query_id = decide_data["query_id"]

    # Transition should have no reward yet
    r = client.get("/v1/rl/transitions")
    transitions = {t["transition_id"]: t for t in r.json()}
    assert transitions[transition_id]["reward"] is None
    assert transitions[transition_id]["completed_at"] is None

    # Submit feedback
    r = client.post("/v1/cells/feedback", json={
        "query_id": query_id,
        "transition_id": transition_id,
        "task_success": True,
        "unsafe_action": False,
        "stale_memory_error": False,
        "tokens_used": 500,
        "latency_ms": 200,
    })
    assert r.status_code == 200
    fb = r.json()
    assert fb["transition_id"] == transition_id
    # reward = +1 - 0.0001*500 - 0.001*200 = +1 - 0.05 - 0.2 = 0.75
    assert abs(fb["reward_value"] - 0.75) < 0.001

    # Transition should now have reward
    r = client.get("/v1/rl/transitions")
    transitions = {t["transition_id"]: t for t in r.json()}
    assert transitions[transition_id]["reward"] is not None
    assert transitions[transition_id]["completed_at"] is not None


def test_feedback_unsuccessful_task_is_negative(client):
    write_cell(client)

    r = client.post("/v1/cells/decide", json={
        "query": "test",
        "scope": {"user": "u1"},
        "budget_tokens": 2000,
        "k": 5,
    })
    data = r.json()

    r = client.post("/v1/cells/feedback", json={
        "query_id": data["query_id"],
        "transition_id": data["transition_id"],
        "task_success": False,
        "unsafe_action": False,
        "stale_memory_error": False,
        "tokens_used": 0,
        "latency_ms": 0,
    })
    assert r.json()["reward_value"] == -1.0


def test_feedback_unsafe_action_large_penalty(client):
    write_cell(client)

    r = client.post("/v1/cells/decide", json={
        "query": "test",
        "scope": {"user": "u1"},
        "budget_tokens": 2000,
        "k": 5,
    })
    data = r.json()

    r = client.post("/v1/cells/feedback", json={
        "query_id": data["query_id"],
        "transition_id": data["transition_id"],
        "task_success": True,
        "unsafe_action": True,
        "stale_memory_error": False,
        "tokens_used": 0,
        "latency_ms": 0,
    })
    # +1 - 2 = -1
    assert r.json()["reward_value"] == -1.0


def test_feedback_nonexistent_transition_returns_404(client):
    r = client.post("/v1/cells/feedback", json={
        "query_id": "00000000-0000-0000-0000-000000000001",
        "transition_id": "00000000-0000-0000-0000-000000000000",
        "task_success": True,
        "unsafe_action": False,
        "stale_memory_error": False,
        "tokens_used": 0,
        "latency_ms": 0,
    })
    assert r.status_code == 404
