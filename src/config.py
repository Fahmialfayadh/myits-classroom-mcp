import os
import re

BASE_URL = "https://classroom.its.ac.id"
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENV_FILE = os.path.join(PROJECT_ROOT, ".env")

MATERIAL_TYPES = {"resource", "url", "folder", "book", "page", "imscp"}
ASSIGN_TYPES = {"assign"}
QUIZ_TYPES = {"quiz"}

DATE_RE = re.compile(
    r"(?:Due date|Tanggal jatuh tempo|Dikumpulkan|Submitted|Grading due|Time remaining|Due)[^\n]*",
    re.IGNORECASE,
)
