import sys
import os
import pytest
import unittest.mock as mock

# Force local testing database and storage settings
os.environ["DB_TYPE"] = "local"
os.environ["STORAGE_TYPE"] = "local"
os.environ["LOCAL_STORAGE_DIR"] = "storage_test"
os.environ["SQLITE_DB_PATH"] = "storage_test/metadata.db"

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

# Helper headers for User A and User B
USER_A_HEADERS = {"X-Beta-Auth-Token": "token_user_a"}
USER_B_HEADERS = {"X-Beta-Auth-Token": "token_user_b"}

def mock_verify_google_token(token: str):
    if token == "token_user_a":
        return {"email": "usera@gmail.com", "sub": "sub_user_a", "name": "User A"}
    elif token == "token_user_b":
        return {"email": "userb@gmail.com", "sub": "sub_user_b", "name": "User B"}
    return None

@pytest.fixture(autouse=True)
def setup_auth_environment():
    """Enable whitelist auth mode and mock Google token verification."""
    original_whitelist = os.environ.get("ALLOWED_BETA_EMAILS")
    os.environ["ALLOWED_BETA_EMAILS"] = "usera@gmail.com,userb@gmail.com"
    with mock.patch("app.auth.verify_google_id_token", side_effect=mock_verify_google_token):
        yield
    if original_whitelist is None:
        os.environ.pop("ALLOWED_BETA_EMAILS", None)
    else:
        os.environ["ALLOWED_BETA_EMAILS"] = original_whitelist

class TestMultiTenantIsolation:

    def test_user_a_creates_match_and_user_b_cannot_see_it(self):
        # 1. User A creates a match
        create_resp = client.post(
            "/api/matches",
            json={"name": "User A Match", "player1": "Alice", "player2": "Bob"},
            headers=USER_A_HEADERS
        )
        assert create_resp.status_code == 201
        match_a = create_resp.json()
        match_a_id = match_a["id"]
        assert match_a["owner_username"] == "usera@gmail.com"
        assert match_a["owner_id"] == "sub_user_a"

        # 2. User A fetches matches list -> should see match_a_id
        list_a = client.get("/api/matches", headers=USER_A_HEADERS)
        assert list_a.status_code == 200
        match_ids_a = [m["id"] for m in list_a.json()]
        assert match_a_id in match_ids_a

        # 3. User B fetches matches list -> match_a_id MUST NOT be present
        list_b = client.get("/api/matches", headers=USER_B_HEADERS)
        assert list_b.status_code == 200
        match_ids_b = [m["id"] for m in list_b.json()]
        assert match_a_id not in match_ids_b

    def test_user_b_forbidden_from_accessing_user_a_match(self):
        # 1. User A creates a match
        create_resp = client.post(
            "/api/matches",
            json={"name": "User A Private Match", "player1": "Alice", "player2": "Bob"},
            headers=USER_A_HEADERS
        )
        assert create_resp.status_code == 201
        match_a_id = create_resp.json()["id"]

        # 2. User B tries GET /api/matches/{match_a_id} -> 403 Forbidden
        get_b = client.get(f"/api/matches/{match_a_id}", headers=USER_B_HEADERS)
        assert get_b.status_code == 403
        assert "Access Denied" in get_b.json()["detail"]

        # 3. User B tries PUT /api/matches/{match_a_id} -> 403 Forbidden
        put_b = client.put(
            f"/api/matches/{match_a_id}",
            json={"name": "Hacked Title"},
            headers=USER_B_HEADERS
        )
        assert put_b.status_code == 403

        # 4. User B tries DELETE /api/matches/{match_a_id} -> 403 Forbidden
        del_b = client.delete(f"/api/matches/{match_a_id}", headers=USER_B_HEADERS)
        assert del_b.status_code == 403

    def test_user_b_forbidden_from_rendering_user_a_match(self):
        # 1. User A creates a match
        create_resp = client.post(
            "/api/matches",
            json={"name": "User A Render Match", "player1": "Alice", "player2": "Bob"},
            headers=USER_A_HEADERS
        )
        match_a_id = create_resp.json()["id"]

        # 2. User B tries POST /api/matches/{match_a_id}/renders -> 403 Forbidden
        render_b = client.post(
            f"/api/matches/{match_a_id}/renders",
            json={"type": "full_match", "label": "Unauthorized Render"},
            headers=USER_B_HEADERS
        )
        assert render_b.status_code == 403
