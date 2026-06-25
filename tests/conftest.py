"""Shared test fixtures."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from memcell_rl.app import app
from memcell_rl.db import get_db
from memcell_rl.models.orm import Base


@pytest.fixture
def client():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=engine)


# ── Helpers ──────────────────────────────────────────────────────────────────


def write_cell(client, **kwargs) -> dict:
    payload = {
        "type": "preference",
        "scope": {"user": "u1"},
        "content": "User prefers concise answers.",
        "confidence": 0.8,
        "sensitivity": "low",
        "policy_features": {
            "criticality": 0.3,
            "compressibility": 0.5,
            "staleness": 0.0,
            "future_utility_estimate": 0.5,
        },
    }
    payload.update(kwargs)
    r = client.post("/v1/cells/write", json=payload)
    assert r.status_code == 200, r.text
    return r.json()
