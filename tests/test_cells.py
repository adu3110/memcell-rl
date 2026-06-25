"""Tests: cell write, read, forget, scope filtering."""

from tests.conftest import write_cell


def test_write_cell_persists(client):
    cell = write_cell(client)
    cell_id = cell["cell_id"]

    r = client.get(f"/v1/cells/{cell_id}")
    assert r.status_code == 200
    data = r.json()
    assert data["cell_id"] == cell_id
    assert data["status"] == "active"
    assert data["version"] == 1
    assert data["access_count"] == 0


def test_deleted_cell_not_returned_by_get(client):
    cell = write_cell(client)
    cell_id = cell["cell_id"]

    r = client.post("/v1/cells/forget", json={"cell_id": cell_id, "reason": "test"})
    assert r.status_code == 200

    r = client.get(f"/v1/cells/{cell_id}")
    assert r.status_code == 404


def test_deleted_cell_not_returned_by_retrieve(client):
    cell = write_cell(client, content="This is the cell to delete.")
    cell_id = cell["cell_id"]

    client.post("/v1/cells/forget", json={"cell_id": cell_id, "reason": "test"})

    r = client.post("/v1/cells/retrieve", json={
        "query": "cell to delete",
        "scope": {"user": "u1"},
        "k": 10,
    })
    assert r.status_code == 200
    returned_ids = [c["cell_id"] for c in r.json()["cells"]]
    assert cell_id not in returned_ids


def test_retrieve_filters_by_scope(client):
    write_cell(client, scope={"user": "u1"}, content="User one preference")
    write_cell(client, scope={"user": "u2"}, content="User two preference")

    r = client.post("/v1/cells/retrieve", json={
        "query": "preference",
        "scope": {"user": "u1"},
        "k": 10,
    })
    assert r.status_code == 200
    cells = r.json()["cells"]
    for c in cells:
        assert c["scope"]["user"] == "u1"


def test_get_nonexistent_cell_returns_404(client):
    r = client.get("/v1/cells/00000000-0000-0000-0000-000000000000")
    assert r.status_code == 404


def test_forget_soft_deletes_content(client):
    cell = write_cell(client)
    cell_id = cell["cell_id"]

    r = client.post("/v1/cells/forget", json={"cell_id": cell_id, "reason": "user_request"})
    assert r.status_code == 200
    assert r.json()["ok"] is True


def test_supersede_creates_new_version(client):
    old = write_cell(client)
    old_id = old["cell_id"]

    r = client.post("/v1/cells/supersede", json={
        "old_cell_id": old_id,
        "new_content": "Updated preference.",
        "source_refs": ["chat:99"],
    })
    assert r.status_code == 200
    data = r.json()
    assert data["old_cell"]["status"] == "superseded"
    assert data["new_cell"]["version"] == 2
    assert old_id in data["new_cell"]["supersedes"]
