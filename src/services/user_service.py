import re
from bs4 import BeautifulSoup
from src.domain.models import UserProfile
from src.infrastructure.moodle_client import create_moodle_client
from src.infrastructure.moodle_parser import extract_user_id


def get_profile() -> UserProfile:
    """Fetch profile info of currently authenticated user."""
    with create_moodle_client() as c:
        r = c.get("/my/")
        if "login/index.php" in str(r.url) or "page-login" in r.text[:5000]:
            raise RuntimeError("Session invalid/expired. Perbarui MOODLE_SESSION.")
        uid = extract_user_id(r.text)
        soup = BeautifulSoup(r.text, "html.parser")
        fullname = None
        m = re.search(r'"fullname":"([^"]+)"', r.text)
        if m:
            fullname = m.group(1)
        if not fullname:
            u = soup.select_one(".usertext, .userbutton .username")
            fullname = u.get_text(strip=True) if u else None
        return {"userid": uid, "fullname": fullname}
