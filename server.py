import os
import re
from typing import Optional

import httpx
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from fastmcp import FastMCP

load_dotenv()

BASE_URL = "https://classroom.its.ac.id"
ENV_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
mcp = FastMCP("myits-classroom")

_SESSION_OVERRIDE: Optional[str] = None


def _get_session() -> str:
    token = _SESSION_OVERRIDE or os.getenv("MOODLE_SESSION", "").strip()
    if not token:
        raise RuntimeError(
            "MOODLE_SESSION belum ada. Minta user memberikan nilai cookie MoodleSession "
            "(DevTools > Application > Cookies), lalu panggil tool set_session."
        )
    return token


def _save_session_env(token: str) -> None:
    lines = []
    if os.path.exists(ENV_FILE):
        with open(ENV_FILE, "r", encoding="utf-8") as fh:
            lines = [ln for ln in fh.readlines() if not ln.strip().startswith("MOODLE_SESSION=")]
    lines.append(f"MOODLE_SESSION={token}\n")
    tmp = ENV_FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        fh.writelines(lines)
    os.replace(tmp, ENV_FILE)


@mcp.tool()
def set_session(moodle_session: str) -> dict:
    """Set cookie MoodleSession dari classroom.its.ac.id, validasi ke server,
    lalu simpan permanen ke file .env agar dipakai juga saat restart.

    Cara ambil: login di browser -> DevTools (F12) -> Application -> Cookies
    -> classroom.its.ac.id -> copy nilai 'MoodleSession'.
    """
    global _SESSION_OVERRIDE
    token = moodle_session.strip()
    test = httpx.Client(
        base_url=BASE_URL,
        cookies={"MoodleSession": token},
        timeout=30.0,
        follow_redirects=True,
        headers={"User-Agent": "Mozilla/5.0 (myits-classroom-mcp)"},
    )
    r = test.get("/my/")
    test.close()
    if "page-login" in r.text[:8000]:
        raise ValueError("Cookie ditolak server (login page muncul). Pastikan menyalin nilai MoodleSession yang masih aktif.")
    m = re.search(r'"userId":(\d+)', r.text)
    _SESSION_OVERRIDE = token
    os.environ["MOODLE_SESSION"] = token
    _save_session_env(token)
    return {
        "status": "ok",
        "userid": int(m.group(1)) if m else None,
        "saved_to": ENV_FILE,
        "note": "Sesi aktif dan sudah tersimpan; akan dipakai ulang saat MCP direstart.",
    }


@mcp.tool()
def session_status() -> dict:
    """Cek apakah sesi saat ini valid dan siapa pemiliknya."""
    try:
        with _client() as c:
            r = c.get("/my/")
        if "page-login" in r.text[:8000]:
            return {"valid": False, "reason": "cookie expired/ditolak server"}
        m = re.search(r'"userId":(\d+)', r.text)
        return {"valid": True, "userid": int(m.group(1)) if m else None}
    except RuntimeError as e:
        return {"valid": False, "reason": str(e)}


def _client() -> httpx.Client:
    return httpx.Client(
        base_url=BASE_URL,
        cookies={"MoodleSession": _get_session()},
        timeout=30.0,
        follow_redirects=True,
        headers={"User-Agent": "Mozilla/5.0 (myits-classroom-mcp)"},
    )


def _sesskey(client: httpx.Client) -> str:
    r = client.get("/my/")
    m = re.search(r'"sesskey":"([^"]+)"', r.text)
    if not m:
        raise RuntimeError("Session expired: tidak bisa menemukan sesskey. Perbarui MOODLE_SESSION.")
    return m.group(1)


def _user_id(client: httpx.Client, page_html: str) -> int:
    m = re.search(r'"userId":(\d+)', page_html)
    if not m:
        raise RuntimeError("Tidak bisa menemukan userId.")
    return int(m.group(1))


def _ajax(client: httpx.Client, sesskey: str, methodname: str, args: dict):
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


def _parse_course_page(html: str) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    sections_out: list[dict] = []

    def parse_activity(li):
        name_el = li.select_one(".instancename")
        if not name_el:
            return None
        for hide in name_el.select(".accesshide"):
            hide.decompose()
        name = re.sub(r"\s+", " ", name_el.get_text(strip=True))
        link = li.select_one(".activityname a[href], a.aalink[href]")
        url = link["href"] if link else ""
        cmid = None
        m = re.search(r"[?&]id=(\d+)", url or "")
        if m:
            cmid = int(m.group(1))
        modtype = None
        for cls in li.get("class", []):
            if cls.startswith("modtype_"):
                modtype = cls[len("modtype_"):]
        if not modtype and li.has_attr("class"):
            for cls in li.get("class", []):
                if cls in ("resource", "assign", "quiz", "forum", "url", "zoom", "folder", "page", "book", "choice", "attendance", "lti"):
                    modtype = cls
        dates = [re.sub(r"\s+", " ", el.get_text(" ", strip=True)) for el in li.select(".activity-dates")]
        return {
            "cmid": cmid,
            "modtype": modtype,
            "name": name,
            "url": url,
            "dates": dates,
        }

    sections = soup.select("li.section")
    for sec in sections:
        title_el = sec.select_one(".sectionname")
        title = re.sub(r"\s+", " ", title_el.get_text(strip=True)) if title_el else "(tanpa judul)"
        acts = []
        for li in sec.select("li.activity"):
            a = parse_activity(li)
            if a:
                acts.append(a)
        sections_out.append({"section": title, "activities": acts})

    if not sections_out:
        acts = []
        for li in soup.select("li.activity"):
            a = parse_activity(li)
            if a:
                acts.append(a)
        if acts:
            sections_out.append({"section": "(semua aktivitas)", "activities": acts})

    return sections_out


def _extract_visible_text(html: str, selector: str, limit: int = 4000) -> str:
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "nav", "header", "footer"]):
        tag.decompose()
    region = soup.select_one(selector) or soup.body or soup
    text = region.get_text("\n", strip=True)
    text = re.sub(r"\n{2,}", "\n", text)
    return text[:limit]


_DATE_RE = re.compile(
    r"(?:Due date|Tanggal jatuh tempo|Dikumpulkan|Submitted|Grading due|Time remaining|Due)[^\n]*",
    re.IGNORECASE,
)


@mcp.tool()
def get_profile() -> dict:
    """Info akun myITS Classroom yang sedang login (userid, nama)."""
    with _client() as c:
        r = c.get("/my/")
        if "login/index.php" in str(r.url) or "page-login" in r.text[:5000]:
            raise RuntimeError("Session invalid/expired. Perbarui MOODLE_SESSION.")
        uid = _user_id(c, r.text)
        soup = BeautifulSoup(r.text, "html.parser")
        fullname = None
        m = re.search(r'"fullname":"([^"]+)"', r.text)
        if m:
            fullname = m.group(1)
        if not fullname:
            u = soup.select_one(".usertext, .userbutton .username")
            fullname = u.get_text(strip=True) if u else None
        return {"userid": uid, "fullname": fullname}


@mcp.tool()
def list_courses(status: str = "inprogress") -> list[dict]:
    """Daftar mata kuliah. status: 'inprogress' | 'future' | 'past' | 'all'."""
    classification = status if status != "all" else "inprogress"
    out: list[dict] = []
    seen = set()
    with _client() as c:
        sk = _sesskey(c)
        data = _ajax(c, sk, "core_course_get_enrolled_courses_by_timeline_classification", {
            "offset": 0,
            "limit": 100,
            "classification": classification,
        })
        for course in data.get("courses", []):
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


@mcp.tool()
def get_course_contents(course_id: int) -> list[dict]:
    """Semua section & aktivitas dalam satu mata kuliah (materi, tugas, kuis, zoom, dsb).

    Setiap aktivitas punya: cmid, modtype (assign/resource/zoom/url/...), name, url.
    """
    with _client() as c:
        r = c.get("/course/view.php", params={"id": course_id})
        if "page-login" in r.text[:8000]:
            raise RuntimeError("Session invalid/expired.")
        sections = _parse_course_page(r.text)
        if not sections:
            raise RuntimeError("Tidak ada aktivitas ditemukan. Course ID salah atau kosong?")
        return sections


MATERIAL_TYPES = {"resource", "url", "folder", "book", "page", "imscp"}


@mcp.tool()
def get_materials(course_id: int) -> list[dict]:
    """Daftar materi/file bahan ajar dalam satu mata kuliah."""
    sections = _list_sections(course_id)
    materials = []
    for sec in sections:
        for a in sec["activities"]:
            if (a.get("modtype") or "") in MATERIAL_TYPES:
                materials.append({**a, "section": sec["section"]})
    return materials


def _list_sections(course_id: int) -> list[dict]:
    with _client() as c:
        r = c.get("/course/view.php", params={"id": course_id})
        return _parse_course_page(r.text)


ASSIGN_TYPES = {"assign"}
QUIZ_TYPES = {"quiz"}


@mcp.tool()
def get_assignments(course_id: int) -> list[dict]:
    """Daftar tugas (assignment) dalam satu mata kuliah beserta tanggal jika tersedia."""
    sections = _list_sections(course_id)
    assignments = []
    for sec in sections:
        for a in sec["activities"]:
            if (a.get("modtype") or "") in ASSIGN_TYPES:
                assignments.append({**a, "section": sec["section"]})
    return assignments


@mcp.tool()
def get_assignment_detail(cmid: int) -> dict:
    """Detail satu tugas: deskripsi, due date, status pengumpulan, nilai."""
    with _client() as c:
        r = c.get("/mod/assign/view.php", params={"id": cmid})
        page = r.text
    soup = BeautifulSoup(page, "html.parser")
    title_el = soup.select_one("#region-main h2, #region-main .page-header-headings h2, h2")
    title = title_el.get_text(strip=True) if title_el else None

    dates = sorted(set(m.strip() for m in _DATE_RE.findall(_extract_visible_text(page, "#region-main"))))
    description = _extract_visible_text(page, ".qtext, [data-region='assign-intro'], .box.generalbox.description", 2500)
    body_text = _extract_visible_text(page, "#region-main", 3500)

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


@mcp.tool()
def download_file(url: str, dest_dir: str = "./downloads") -> dict:
    """Download file materi/tugas dari classroom ke folder lokal (butuh URL pluginfile)."""
    from pathlib import Path

    if not url.startswith(BASE_URL):
        raise ValueError("Hanya URL di domain classroom.its.ac.id yang boleh didownload.")
    dest = Path(dest_dir).expanduser()
    dest.mkdir(parents=True, exist_ok=True)
    filename = url.split("?")[0].rstrip("/").split("/")[-1] or "file"
    with _client() as c:
        with c.stream("GET", url) as r:
            r.raise_for_status()
            cd = r.headers.get("content-disposition", "")
            m = re.search(r'filename="?([^";]+)"?', cd)
            if m:
                filename = m.group(1)
            path = dest / filename
            with open(path, "wb") as fh:
                for chunk in r.iter_bytes():
                    fh.write(chunk)
    return {"saved_to": str(path), "size_bytes": path.stat().st_size}


@mcp.tool()
def get_deadlines(course_id: Optional[int] = None, days_ahead: int = 30) -> list[dict]:
    """Agenda/deadline mendatang. Tanpa course_id = semua mata kuliah."""
    import time

    now = int(time.time())
    end = now + days_ahead * 86400
    events_out: list[dict] = []
    with _client() as c:
        sk = _sesskey(c)
        if course_id:
            data = _ajax(c, sk, "core_calendar_get_calendar_upcoming_view", {"courseid": course_id})
            events = data.get("events", [])
        else:
            courses = _courses_direct(c, sk)
            courseids = [e["id"] for e in courses] or []
            grouped = _ajax(c, sk, "core_calendar_get_action_events_by_courses", {"courseids": courseids})
            events = [ev for g in grouped.get("groupedbycourse", []) for ev in g.get("events", [])]
        for ev in events:
            events_out.append({
                "name": ev.get("name"),
                "type": ev.get("eventtype"),
                "module": ev.get("modulename"),
                "timestart_epoch": ev.get("timestart"),
                "time": time.strftime("%Y-%m-%d %H:%M", time.localtime(ev.get("timestart", 0))) if ev.get("timestart") else None,
                "course_id": ev.get("course", {}).get("id") if isinstance(ev.get("course"), dict) else ev.get("courseid"),
                "url": ev.get("url") or ev.get("action", {}).get("url") if isinstance(ev.get("action"), dict) else ev.get("url"),
                "description": BeautifulSoup(ev.get("description") or "", "html.parser").get_text(" ", strip=True)[:300],
            })
    events_out.sort(key=lambda e: e.get("timestart_epoch") or 0)
    return events_out


def _courses_direct(client: httpx.Client, sesskey: str) -> list[dict]:
    data = _ajax(client, sesskey, "core_course_get_enrolled_courses_by_timeline_classification", {
        "offset": 0, "limit": 100, "classification": "inprogress",
    })
    return [{"id": c["id"], "fullname": c.get("fullname")} for c in data.get("courses", [])]


@mcp.tool()
def get_grades(course_id: int) -> str:
    """Tabel nilai untuk satu mata kuliah (scraping laporan nilai)."""
    with _client() as c:
        home = c.get("/my/")
        uid = _user_id(c, home.text)
        r = c.get("/grade/report/user/index.php", params={"id": course_id, "userid": uid})
        page = r.text
    return _extract_visible_text(page, "#grading-report, .user-grade, #region-main table", 4000)


if __name__ == "__main__":
    mcp.run()
