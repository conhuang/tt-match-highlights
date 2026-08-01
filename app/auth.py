import os
import logging
import urllib.request
import json
from typing import Optional, Set
from fastapi import Request, HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

logger = logging.getLogger(__name__)
security = HTTPBearer(auto_error=False)

def get_allowed_emails() -> Set[str]:
    """Parses ALLOWED_BETA_EMAILS environment variable into a set of lowercased emails."""
    raw = os.getenv("ALLOWED_BETA_EMAILS", "")
    if not raw.strip():
        return set()
    return {email.strip().strip('"').strip("'").lower() for email in raw.split(",") if email.strip()}

def verify_google_id_token(id_token: str) -> Optional[dict]:
    """
    Verifies a Google OAuth ID Token via Google's tokeninfo endpoint.
    Returns token payload dict if valid, None otherwise.
    """
    if not id_token:
        return None
    
    url = f"https://oauth2.googleapis.com/tokeninfo?id_token={id_token}"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "FastAPI-Auth"})
        with urllib.request.urlopen(req, timeout=5) as response:
            if response.status == 200:
                payload = json.loads(response.read().decode("utf-8"))
                google_client_id = os.getenv("GOOGLE_CLIENT_ID")
                if google_client_id and payload.get("aud") != google_client_id:
                    logger.warning(f"Google Token audience mismatch: {payload.get('aud')} != {google_client_id}")
                    return None
                return payload
    except Exception as e:
        logger.warning(f"Google ID token verification failed: {e}")
        return None

def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    request: Request = None
) -> dict:
    """
    FastAPI Dependency enforcing Google OAuth + Email Whitelist verification.
    If ALLOWED_BETA_EMAILS is not configured or DISABLE_AUTH=true, auth is bypassed for local dev.
    """
    allowed_emails = get_allowed_emails()
    disable_auth = os.getenv("DISABLE_AUTH", "false").lower() in ("true", "1", "yes")

    # Bypass authentication for local development when no whitelist is configured
    if not allowed_emails or disable_auth:
        return {
            "email": "dev@local",
            "name": "Local Developer",
            "sub": "dev-local-id",
            "authenticated": False
        }

    token = None
    if credentials and credentials.credentials:
        token = credentials.credentials
    elif request:
        token = request.headers.get("X-Beta-Auth-Token")

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required. Please sign in with Google.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = verify_google_id_token(token)
    if not payload or "email" not in payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired Google Authentication token. Please sign in again.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_email = payload["email"].strip().lower()

    if user_email not in allowed_emails:
        logger.warning(f"Unauthorized login attempt by: {user_email}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Access Denied: '{user_email}' is not authorized for this Beta release.",
        )

    return {
        "email": user_email,
        "name": payload.get("name", user_email),
        "picture": payload.get("picture"),
        "sub": payload.get("sub"),
        "authenticated": True
    }
