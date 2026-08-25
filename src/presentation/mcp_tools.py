from typing import Optional, List, Dict, Any
from fastmcp import FastMCP

from src.services import (
    session_service,
    user_service,
    course_service,
    assignment_service,
    calendar_service,
    grade_service,
)

mcp = FastMCP("myits-classroom")


@mcp.tool()
def set_session(moodle_session: str) -> dict:
    """Set cookie MoodleSession dari classroom.its.ac.id, validasi ke server,
    lalu simpan permanen ke file .env agar dipakai juga saat restart.

    Cara ambil: login di browser -> DevTools (F12) -> Application -> Cookies
    -> classroom.its.ac.id -> copy nilai 'MoodleSession'.
    """
    return session_service.set_session(moodle_session)


@mcp.tool()
def session_status() -> dict:
    """Cek apakah sesi saat ini valid dan siapa pemiliknya."""
    return session_service.session_status()


@mcp.tool()
def get_profile() -> dict:
    """Info akun myITS Classroom yang sedang login (userid, nama)."""
    return user_service.get_profile()


@mcp.tool()
def list_courses(status: str = "inprogress") -> list[dict]:
    """Daftar mata kuliah. status: 'inprogress' | 'future' | 'past' | 'all'."""
    return course_service.list_courses(status)


@mcp.tool()
def get_course_contents(course_id: int) -> list[dict]:
    """Semua section & aktivitas dalam satu mata kuliah (materi, tugas, kuis, zoom, dsb).

    Setiap aktivitas punya: cmid, modtype (assign/resource/zoom/url/...), name, url.
    """
    return course_service.get_course_contents(course_id)


@mcp.tool()
def get_materials(course_id: int) -> list[dict]:
    """Daftar materi/file bahan ajar dalam satu mata kuliah."""
    return course_service.get_materials(course_id)


@mcp.tool()
def get_assignments(course_id: int) -> list[dict]:
    """Daftar tugas (assignment) dalam satu mata kuliah beserta tanggal jika tersedia."""
    return course_service.get_assignments(course_id)


@mcp.tool()
def get_assignment_detail(cmid: int) -> dict:
    """Detail satu tugas: deskripsi, due date, status pengumpulan, nilai."""
    return assignment_service.get_assignment_detail(cmid)


@mcp.tool()
def download_file(url: str, dest_dir: str = "./downloads") -> dict:
    """Download file materi/tugas dari classroom ke folder lokal (butuh URL pluginfile)."""
    return assignment_service.download_file(url, dest_dir)


@mcp.tool()
def get_deadlines(course_id: Optional[int] = None, days_ahead: int = 30) -> list[dict]:
    """Agenda/deadline mendatang. Tanpa course_id = semua mata kuliah."""
    return calendar_service.get_deadlines(course_id, days_ahead)


@mcp.tool()
def get_grades(course_id: int) -> str:
    """Tabel nilai untuk satu mata kuliah (scraping laporan nilai)."""
    return grade_service.get_grades(course_id)
