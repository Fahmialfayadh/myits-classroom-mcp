import re
from src.config import ENV_FILE
from src.domain.models import SetSessionResult, SessionStatus
from src.infrastructure.moodle_client import create_moodle_client
from src.infrastructure.session_repository import set_session_override, save_session_to_env


def set_session(moodle_session: str) -> SetSessionResult:
    """Validate and persist MoodleSession cookie token."""
    token = moodle_session.strip()
    client = create_moodle_client(token=token)
    try:
        r = client.get("/my/")
    finally:
        client.close()

    if "page-login" in r.text[:8000]:
        raise ValueError(
            "Cookie ditolak server (login page muncul). Pastikan menyalin nilai MoodleSession yang masih aktif."
        )

    m = re.search(r'"userId":(\d+)', r.text)
    user_id = int(m.group(1)) if m else None

    set_session_override(token)
    save_session_to_env(token)

    return {
        "status": "ok",
        "userid": user_id,
        "saved_to": ENV_FILE,
        "note": "Sesi aktif dan sudah tersimpan; akan dipakai ulang saat MCP direstart.",
    }


def session_status() -> SessionStatus:
    """Check whether current session token is valid and return owner info."""
    try:
        with create_moodle_client() as c:
            r = c.get("/my/")
        if "page-login" in r.text[:8000]:
            return {"valid": False, "reason": "cookie expired/ditolak server"}
        m = re.search(r'"userId":(\d+)', r.text)
        return {"valid": True, "userid": int(m.group(1)) if m else None}
    except RuntimeError as e:
        return {"valid": False, "reason": str(e)}
