from src.infrastructure.moodle_client import create_moodle_client
from src.infrastructure.moodle_parser import extract_user_id, extract_visible_text


def get_grades(course_id: int) -> str:
    """Scrape and extract grade report table for a course."""
    with create_moodle_client() as c:
        home = c.get("/my/")
        uid = extract_user_id(home.text)
        r = c.get("/grade/report/user/index.php", params={"id": course_id, "userid": uid})
        page = r.text
    return extract_visible_text(page, "#grading-report, .user-grade, #region-main table", 4000)
