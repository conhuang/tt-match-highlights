import pytest
from unittest.mock import patch
from fastapi import HTTPException

from app.auth import get_current_user, get_allowed_emails, verify_google_id_token

def test_get_allowed_emails_parsing(monkeypatch):
    monkeypatch.setenv("ALLOWED_BETA_EMAILS", " User1@Gmail.com , USER2@gmail.com ")
    emails = get_allowed_emails()
    assert emails == {"user1@gmail.com", "user2@gmail.com"}

def test_get_current_user_unauthenticated(monkeypatch):
    monkeypatch.setenv("ALLOWED_BETA_EMAILS", "allowed@gmail.com")
    with pytest.raises(HTTPException) as exc_info:
        get_current_user(credentials=None, request=None)
    assert exc_info.value.status_code == 401
    assert "Authentication required" in exc_info.value.detail

def test_get_current_user_unapproved_email(monkeypatch):
    monkeypatch.setenv("ALLOWED_BETA_EMAILS", "allowed@gmail.com")
    with patch("app.auth.verify_google_id_token") as mock_verify:
        mock_verify.return_value = {"email": "unapproved@gmail.com", "name": "Unapproved User"}
        
        class MockCredentials:
            credentials = "mock-unapproved-token"
            
        with pytest.raises(HTTPException) as exc_info:
            get_current_user(credentials=MockCredentials(), request=None)
        assert exc_info.value.status_code == 403
        assert "Access Denied" in exc_info.value.detail

def test_get_current_user_approved_email(monkeypatch):
    monkeypatch.setenv("ALLOWED_BETA_EMAILS", "allowed@gmail.com")
    with patch("app.auth.verify_google_id_token") as mock_verify:
        mock_verify.return_value = {"email": "allowed@gmail.com", "name": "Allowed User", "sub": "12345"}
        
        class MockCredentials:
            credentials = "mock-approved-token"
            
        user = get_current_user(credentials=MockCredentials(), request=None)
        assert user["email"] == "allowed@gmail.com"
        assert user["authenticated"] is True

def test_get_current_user_local_dev_bypass(monkeypatch):
    monkeypatch.delenv("ALLOWED_BETA_EMAILS", raising=False)
    user = get_current_user(credentials=None, request=None)
    assert user["email"] == "dev@local"
    assert user["authenticated"] is False

def test_get_auth_config_endpoint(monkeypatch):
    from fastapi.testclient import TestClient
    from app.main import app
    client = TestClient(app)
    
    monkeypatch.setenv("GOOGLE_CLIENT_ID", "test-client-id-123.apps.googleusercontent.com")
    monkeypatch.setenv("ALLOWED_BETA_EMAILS", "allowed@gmail.com")
    
    response = client.get("/api/auth/config")
    assert response.status_code == 200
    data = response.json()
    assert data["google_client_id"] == "test-client-id-123.apps.googleusercontent.com"
    assert data["auth_enabled"] is True

