import os
import tempfile

_tmp = tempfile.mkdtemp(prefix="reframe_api_test_")
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp}/test.db"
os.environ["STORAGE_DIR"] = f"{_tmp}/storage"
os.environ["APP_SECRET_KEY"] = "test-secret-key"
os.environ["MODEL_API_KEY"] = ""

from fastapi.testclient import TestClient

from app.db import init_db
from app.main import create_app

init_db()
client = TestClient(create_app())


def _auth_headers():
    import uuid as _uuid

    email = f"t-{_uuid.uuid4().hex[:8]}@t.co"
    r = client.post("/api/auth/register", json={"email": email, "password": "password123"})
    assert r.status_code == 200, r.text
    token = r.json()["token"]
    return {"Authorization": f"Bearer {token}"}, email


def test_auth_and_me():
    h, email = _auth_headers()
    r = client.get("/api/auth/me", headers=h)
    assert r.status_code == 200 and r.json()["email"] == email
    r = client.get("/api/auth/me")
    assert r.status_code == 401


def test_projects_crud_and_providers():
    h, _ = _auth_headers()
    r = client.post("/api/projects", json={"name": "Demo"}, headers=h)
    assert r.status_code == 200, r.text
    pid = r.json()["id"]
    r = client.get("/api/projects", headers=h)
    assert any(p["id"] == pid for p in r.json())
    r = client.get(f"/api/projects/{pid}", headers=h)
    assert r.status_code == 200
    r = client.get("/api/providers")
    assert r.status_code == 200
    states = {p["name"]: p["state"] for p in r.json()}
    assert states["sam"] == "not_configured"  # no MODEL_API_KEY in tests
    r = client.delete(f"/api/projects/{pid}", headers=h)
    assert r.status_code == 200


def test_assistant_local_planner():
    h, _ = _auth_headers()
    r = client.post("/api/assistant/chat",
                    json={"messages": [{"role": "user", "content": "Remove the person behind me"}]},
                    headers=h)
    assert r.status_code == 200, r.text
    assert r.json()["plan"]["operation"] == "remove"


def test_health():
    r = client.get("/api/health")
    assert r.status_code == 200 and r.json()["ok"] is True
