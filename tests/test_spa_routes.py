from pathlib import Path

from fastapi.testclient import TestClient

from brain_dump.api.app import STATIC_DIR, create_app
from brain_dump.config import Settings


def test_api_uploads_json():
    settings = Settings(home=Path("/tmp/brain-dump-test-unused"))
    client = TestClient(create_app(settings))
    resp = client.get("/api/uploads")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


def test_spa_routes_serve_index():
    if not (STATIC_DIR / "index.html").exists():
        return
    settings = Settings(home=Path("/tmp/brain-dump-test-unused"))
    client = TestClient(create_app(settings))
    for path in ("/uploads", "/sessions", "/sessions/abc-123"):
        resp = client.get(path)
        assert resp.status_code == 200, path
        assert "html" in resp.headers.get("content-type", ""), path
        assert "root" in resp.text, path
