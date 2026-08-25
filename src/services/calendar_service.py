import time
from typing import Optional, List
from bs4 import BeautifulSoup
from src.domain.models import CalendarEvent
from src.infrastructure.moodle_client import create_moodle_client
from src.infrastructure.moodle_ajax import fetch_sesskey, call_moodle_ajax, fetch_courses_direct


def get_deadlines(course_id: Optional[int] = None, days_ahead: int = 30) -> List[CalendarEvent]:
    """Fetch upcoming agenda/deadlines sorted by event start time."""
    now = int(time.time())
    end = now + days_ahead * 86400
    events_out: List[CalendarEvent] = []
    with create_moodle_client() as c:
        sk = fetch_sesskey(c)
        if course_id:
            data = call_moodle_ajax(c, sk, "core_calendar_get_calendar_upcoming_view", {"courseid": course_id})
            events = data.get("events", []) if isinstance(data, dict) else []
        else:
            courses = fetch_courses_direct(c, sk)
            courseids = [e["id"] for e in courses] or []
            grouped = call_moodle_ajax(c, sk, "core_calendar_get_action_events_by_courses", {"courseids": courseids})
            groupedbycourse = grouped.get("groupedbycourse", []) if isinstance(grouped, dict) else []
            events = [ev for g in groupedbycourse for ev in g.get("events", [])]

        for ev in events:
            timestart = ev.get("timestart")
            events_out.append({
                "name": ev.get("name"),
                "type": ev.get("eventtype"),
                "module": ev.get("modulename"),
                "timestart_epoch": timestart,
                "time": time.strftime("%Y-%m-%d %H:%M", time.localtime(timestart)) if timestart else None,
                "course_id": ev.get("course", {}).get("id") if isinstance(ev.get("course"), dict) else ev.get("courseid"),
                "url": ev.get("url") or (ev.get("action", {}).get("url") if isinstance(ev.get("action"), dict) else None),
                "description": BeautifulSoup(ev.get("description") or "", "html.parser").get_text(" ", strip=True)[:300],
            })

    events_out.sort(key=lambda e: e.get("timestart_epoch") or 0)
    return events_out
