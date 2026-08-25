import re
from bs4 import BeautifulSoup
from src.config import BASE_URL, DATE_RE
from src.domain.models import AssignmentDetail, DownloadResult
from src.infrastructure.moodle_client import create_moodle_client
from src.infrastructure.moodle_parser import extract_visible_text
from src.infrastructure.file_downloader import download_moodle_file


def get_assignment_detail(cmid: int) -> AssignmentDetail:
    """Fetch details of a single assignment: description, due dates, submission status, grade."""
    with create_moodle_client() as c:
        r = c.get("/mod/assign/view.php", params={"id": cmid})
        page = r.text
    soup = BeautifulSoup(page, "html.parser")
    title_el = soup.select_one("#region-main h2, #region-main .page-header-headings h2, h2")
    title = title_el.get_text(strip=True) if title_el else None

    dates = sorted(set(m.strip() for m in DATE_RE.findall(extract_visible_text(page, "#region-main"))))
    description = extract_visible_text(
        page, ".qtext, [data-region='assign-intro'], .box.generalbox.description", 2500
    )
    body_text = extract_visible_text(page, "#region-main", 3500)

    submission_status = None
    st = soup.select_one("[data-region='submission-status'], .submissionstatustable")
    if st:
        submission_status = re.sub(r"\s+", " ", st.get_text(" ", strip=True))[:600]
    grade = None
    gr = soup.select_one(".gradestable, [data-region='grade']")
    if gr:
        grade = re.sub(r"\s+", " ", gr.get_text(" ", strip=True))[:400]

    files = []
    for f in soup.select("#region-main a[href*='pluginfile.php']"):
        files.append({"name": f.get_text(strip=True) or (f.get("href") or "").split("/")[-1], "url": f["href"]})
    files = [f for i, f in enumerate(files) if f not in files[:i]]

    return {
        "title": title,
        "dates": dates,
        "submission_status": submission_status,
        "grade": grade,
        "description": description or None,
        "files": files,
        "text_excerpt": body_text,
        "url": f"{BASE_URL}/mod/assign/view.php?id={cmid}",
    }


def download_file(url: str, dest_dir: str = "./downloads") -> DownloadResult:
    """Download material or assignment file from classroom to local folder."""
    with create_moodle_client() as c:
        return download_moodle_file(c, url, dest_dir)
