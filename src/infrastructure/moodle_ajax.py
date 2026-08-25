import re
from typing import Any, Dict, List
import httpx


def fetch_sesskey(client: httpx.Client) -> str:
    """Extract sesskey CSRF token from /my/ page."""
    r = client.get("/my/")
    m = re.search(r'"sesskey":"([^"]+)"', r.text)
    if not m:
        raise RuntimeError("Session expired: tidak bisa menemukan sesskey. Perbarui MOODLE_SESSION.")
    return m.group(1)


def call_moodle_ajax(client: httpx.Client, sesskey: str, methodname: str, args: Dict[str, Any]) -> Any:
    """Execute Moodle internal AJAX RPC endpoint."""
    r = client.post(
        f"/lib/ajax/service.php?sesskey={sesskey}&info={methodname}",
        json=[{"index": 0, "methodname": methodname, "args": args}],
    )
    r.raise_for_status()
    data = r.json()
    if isinstance(data, list):
        entry = data[0]
        if entry.get("error"):
            exc = entry.get("exception", {})
            raise RuntimeError(f"AJAX error pada {methodname}: {exc.get('message')}")
        return entry.get("data")
    raise RuntimeError(f"Respons tak terduga dari {methodname}")


def fetch_courses_direct(client: httpx.Client, sesskey: str) -> List[Dict[str, Any]]:
    """Fetch basic in-progress course list via AJAX."""
    data = call_moodle_ajax(
        client,
        sesskey,
        "core_course_get_enrolled_courses_by_timeline_classification",
        {"offset": 0, "limit": 100, "classification": "inprogress"},
    )
    courses = data.get("courses", []) if isinstance(data, dict) else []
    return [{"id": c["id"], "fullname": c.get("fullname")} for c in courses]
