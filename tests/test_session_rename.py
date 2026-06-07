from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from open_paxel.api.app import create_app
from open_paxel.config import Settings
from open_paxel.models.domain import DimensionScore, SessionScore
from open_paxel.pipeline import AnalysisPipeline


class MockScorer:
    async def score_session(self, facts, metrics, excerpts):
        return SessionScore(
            dimensions={
                d: DimensionScore(score=70.0, narrative="mock", evidence=["e1"])
                for d in ("steering", "execution", "engineering", "product_instinct", "planning")
            },
            archetype="Architect",
            signature_moves=["Plans before coding"],
            growth_edge=["Add more tests"],
        )


@pytest.fixture
def client(tmp_path):
    settings = Settings(home=tmp_path / "home", ephemeral_jobs=True)
    settings.home.mkdir(parents=True)
    app = create_app(settings)

    original_init = AnalysisPipeline.__init__

    def patched_init(self, s, repository, parser=None, scorer=None):
        original_init(self, s, repository, parser=parser, scorer=MockScorer())

    with patch.object(AnalysisPipeline, "__init__", patched_init):
        with TestClient(app) as test_client:
            yield test_client


def test_rename_session(client):
    fixture = Path(__file__).parent / "fixtures" / "sample.jsonl"
    files = [("files", ("sample.jsonl", fixture.read_bytes(), "application/jsonl"))]
    resp = client.post("/api/upload?sync=true", files=files)
    assert resp.status_code == 200
    session_id = resp.json()["results"][0]["session_id"]

    patch = client.patch(f"/api/sessions/{session_id}", json={"title": "My custom name"})
    assert patch.status_code == 200
    assert patch.json()["title"] == "My custom name"

    listed = client.get("/api/sessions").json()
    match = next(i for i in listed["items"] if i["session_id"] == session_id)
    assert match["title"] == "My custom name"
