from typing import Optional
import httpx
from src.config import BASE_URL
from src.infrastructure.session_repository import get_session_token


def create_moodle_client(token: Optional[str] = None) -> httpx.Client:
    """Create configured httpx.Client for Moodle communication.
    
    If token is not explicitly provided, retrieves active session token from session repository.
    """
    cookie_token = token if token is not None else get_session_token()
    return httpx.Client(
        base_url=BASE_URL,
        cookies={"MoodleSession": cookie_token},
        timeout=30.0,
        follow_redirects=True,
        headers={"User-Agent": "Mozilla/5.0 (myits-classroom-mcp)"},
    )
