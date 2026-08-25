import os
from typing import Optional
from src.config import ENV_FILE

_SESSION_OVERRIDE: Optional[str] = None


def get_session_token() -> str:
    """Retrieve active MoodleSession token from override or environment."""
    token = _SESSION_OVERRIDE or os.getenv("MOODLE_SESSION", "").strip()
    if not token:
        raise RuntimeError(
            "MOODLE_SESSION belum ada. Minta user memberikan nilai cookie MoodleSession "
            "(DevTools > Application > Cookies), lalu panggil tool set_session."
        )
    return token


def set_session_override(token: str) -> None:
    """Set in-memory session override and environment variable."""
    global _SESSION_OVERRIDE
    _SESSION_OVERRIDE = token
    os.environ["MOODLE_SESSION"] = token


def save_session_to_env(token: str) -> None:
    """Persist session token atomically to .env file."""
    lines = []
    if os.path.exists(ENV_FILE):
        with open(ENV_FILE, "r", encoding="utf-8") as fh:
            lines = [ln for ln in fh.readlines() if not ln.strip().startswith("MOODLE_SESSION=")]
    lines.append(f"MOODLE_SESSION={token}\n")
    tmp = ENV_FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        fh.writelines(lines)
    os.replace(tmp, ENV_FILE)
