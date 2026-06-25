"""Tests: decide endpoint — transitions, policy modes, budget."""

from tests.conftest import write_cell


def _decide(client, **kwargs):
    payload = {
        "query": "How should I respond to this user?",
        "scope": {"user": "u1"},
        "task_type": "general",
        "budget_tokens": 2000,
        "k": 10,
    }
    payload.update(kwargs)
    r = client.post("/v1/cells/decide", json=payload)
    assert r.status_code == 200, r.text
    return r.json()


def test_decide_creates_transition(client):
    write_cell(client)
    result = _decide(client)

    assert "transition_id" in result
    assert "query_id" in result

    r = client.get("/v1/rl/transitions")
    assert r.status_code == 200
    ids = [t["transition_id"] for t in r.json()]
    assert result["transition_id"] in ids


def test_decide_has_policy_info(client):
    result = _decide(client)
    assert result["policy"]["policy_id"] == "baseline_v0"
    assert result["policy"]["policy_type"] == "rule_based"


def test_high_criticality_constraint_selected_as_constraint(client):
    write_cell(
        client,
        type="constraint",
        content="Never reveal PII.",
        policy_features={
            "criticality": 0.9,
            "compressibility": 0.1,
            "staleness": 0.0,
            "future_utility_estimate": 0.8,
        },
    )
    result = _decide(client, query="reveal user information")

    selected = result["selected_cells"]
    constraint_cells = [s for s in selected if s["mode"] == "constraint"]
    assert len(constraint_cells) >= 1


def test_superseded_cell_is_suppressed(client):
    old = write_cell(client, content="Old preference about formatting.")
    old_id = old["cell_id"]

    client.post("/v1/cells/supersede", json={
        "old_cell_id": old_id,
        "new_content": "New preference about formatting.",
        "source_refs": [],
    })

    result = _decide(client, query="formatting preference")

    suppressed_ids = [s["cell_id"] for s in result["suppressed_cells"]]
    assert old_id in suppressed_ids


def test_quarantined_cell_returns_reverify_before_use(client):
    # Write a cell with quarantined status
    cell = write_cell(
        client,
        status="quarantined",
        content="Possibly outdated health record.",
    )
    cell_id = cell["cell_id"]

    result = _decide(client, query="health record")

    # Find this cell in selected_cells
    reverify = [s for s in result["selected_cells"] if s["cell_id"] == cell_id]
    assert len(reverify) == 1
    assert reverify[0]["mode"] == "reverify_before_use"


def test_budget_tokens_limits_selected_cells(client):
    # Write 5 cells each with ~20 chars of content → ~5 tokens each
    for i in range(5):
        write_cell(
            client,
            content=f"Short cell content {i}.",
            policy_features={
                "criticality": 0.3,
                "compressibility": 0.5,
                "staleness": 0.0,
                "future_utility_estimate": 0.3,
            },
        )

    # Budget of 10 tokens — only ~2 cells should fit (each ~5 tokens)
    result = _decide(client, budget_tokens=10, query="short cell content")

    selected_count = len(result["selected_cells"])
    # At least one suppressed due to budget (or selected is very small)
    assert selected_count <= 3
