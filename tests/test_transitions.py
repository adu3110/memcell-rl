"""Tests: transition creation and listing."""

from tests.conftest import write_cell


def test_decide_transition_state_contains_query(client):
    write_cell(client)

    r = client.post("/v1/cells/decide", json={
        "query": "my unique query string xyz",
        "scope": {"user": "u1"},
        "budget_tokens": 2000,
        "k": 5,
    })
    assert r.status_code == 200
    transition_id = r.json()["transition_id"]

    r = client.get("/v1/rl/transitions")
    transitions = {t["transition_id"]: t for t in r.json()}
    t = transitions[transition_id]

    assert t["state"]["query"] == "my unique query string xyz"
    assert t["reward"] is None
    assert t["next_state"] is None


def test_multiple_transitions_are_listed(client):
    write_cell(client)

    for _ in range(3):
        client.post("/v1/cells/decide", json={
            "query": "query",
            "scope": {"user": "u1"},
            "budget_tokens": 2000,
            "k": 5,
        })

    r = client.get("/v1/rl/transitions")
    assert len(r.json()) >= 3


def test_transitions_pagination(client):
    write_cell(client)

    for _ in range(5):
        client.post("/v1/cells/decide", json={
            "query": "q",
            "scope": {"user": "u1"},
            "budget_tokens": 2000,
            "k": 5,
        })

    r = client.get("/v1/rl/transitions?limit=2&offset=0")
    assert len(r.json()) == 2
