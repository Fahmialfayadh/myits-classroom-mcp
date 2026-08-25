import re
from typing import List, Dict, Any, Optional
from bs4 import BeautifulSoup


def extract_user_id(page_html: str) -> int:
    """Extract user ID from HTML content."""
    m = re.search(r'"userId":(\d+)', page_html)
    if not m:
        raise RuntimeError("Tidak bisa menemukan userId.")
    return int(m.group(1))


def parse_course_page(html: str) -> List[Dict[str, Any]]:
    """Parse course sections and activities from course view page HTML."""
    soup = BeautifulSoup(html, "html.parser")
    sections_out: List[Dict[str, Any]] = []

    def parse_activity(li) -> Optional[Dict[str, Any]]:
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
                modtype = cls[len("modtype_") :]
        if not modtype and li.has_attr("class"):
            for cls in li.get("class", []):
                if cls in (
                    "resource",
                    "assign",
                    "quiz",
                    "forum",
                    "url",
                    "zoom",
                    "folder",
                    "page",
                    "book",
                    "choice",
                    "attendance",
                    "lti",
                ):
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


def extract_visible_text(html: str, selector: str, limit: int = 4000) -> str:
    """Extract clean visible text inside a CSS selector region."""
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "nav", "header", "footer"]):
        tag.decompose()
    region = soup.select_one(selector) or soup.body or soup
    text = region.get_text("\n", strip=True)
    text = re.sub(r"\n{2,}", "\n", text)
    return text[:limit]
