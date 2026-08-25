"""
Entry point for myITS Classroom MCP Server.

This module initializes the server environment and re-exports tool handlers
for backwards-compatibility with direct module imports.
"""
from dotenv import load_dotenv

load_dotenv()

from src.presentation.mcp_tools import (
    mcp,
    set_session,
    session_status,
    get_profile,
    list_courses,
    get_course_contents,
    get_materials,
    get_assignments,
    get_assignment_detail,
    download_file,
    get_deadlines,
    get_grades,
)

__all__ = [
    "mcp",
    "set_session",
    "session_status",
    "get_profile",
    "list_courses",
    "get_course_contents",
    "get_materials",
    "get_assignments",
    "get_assignment_detail",
    "download_file",
    "get_deadlines",
    "get_grades",
]

if __name__ == "__main__":
    mcp.run()
