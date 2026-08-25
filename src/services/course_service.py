from typing import List, Dict, Any
from src.config import MATERIAL_TYPES, ASSIGN_TYPES
from src.domain.models import CourseInfo, CourseSection, ActivityInfo
from src.infrastructure.moodle_client import create_moodle_client
from src.infrastructure.moodle_ajax import fetch_sesskey, call_moodle_ajax
from src.infrastructure.moodle_parser import parse_course_page


def list_courses(status: str = "inprogress") -> List[CourseInfo]:
    """Retrieve list of enrolled courses filtered by classification status."""
    classification = status if status != "all" else "inprogress"
    out: List[CourseInfo] = []
    seen = set()
    with create_moodle_client() as c:
        sk = fetch_sesskey(c)
        data = call_moodle_ajax(
            c,
            sk,
            "core_course_get_enrolled_courses_by_timeline_classification",
            {
                "offset": 0,
                "limit": 100,
                "classification": classification,
            },
        )
        courses = data.get("courses", []) if isinstance(data, dict) else []
        for course in courses:
            if course["id"] in seen:
                continue
            seen.add(course["id"])
            out.append({
                "id": course["id"],
                "fullname": course.get("fullname"),
                "shortname": course.get("shortname"),
                "progress_percent": course.get("progress"),
                "startdate": course.get("startdate"),
                "enddate": course.get("enddate"),
                "viewurl": course.get("viewurl"),
            })
    return out


def get_course_contents(course_id: int) -> List[CourseSection]:
    """Fetch sections and activities contained in a course."""
    with create_moodle_client() as c:
        r = c.get("/course/view.php", params={"id": course_id})
        if "page-login" in r.text[:8000]:
            raise RuntimeError("Session invalid/expired.")
        sections = parse_course_page(r.text)
        if not sections:
            raise RuntimeError("Tidak ada aktivitas ditemukan. Course ID salah atau kosong?")
        return sections


def list_sections(course_id: int) -> List[Dict[str, Any]]:
    """Helper to fetch course sections raw structure."""
    with create_moodle_client() as c:
        r = c.get("/course/view.php", params={"id": course_id})
        return parse_course_page(r.text)


def get_materials(course_id: int) -> List[ActivityInfo]:
    """Filter learning materials (resources, URLs, books, pages) in a course."""
    sections = list_sections(course_id)
    materials: List[ActivityInfo] = []
    for sec in sections:
        for a in sec.get("activities", []):
            if (a.get("modtype") or "") in MATERIAL_TYPES:
                materials.append({**a, "section": sec["section"]})
    return materials


def get_assignments(course_id: int) -> List[ActivityInfo]:
    """Filter assignment activities in a course."""
    sections = list_sections(course_id)
    assignments: List[ActivityInfo] = []
    for sec in sections:
        for a in sec.get("activities", []):
            if (a.get("modtype") or "") in ASSIGN_TYPES:
                assignments.append({**a, "section": sec["section"]})
    return assignments
