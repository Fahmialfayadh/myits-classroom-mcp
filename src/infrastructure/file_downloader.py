import re
from pathlib import Path
from typing import Dict, Any
import httpx
from src.config import BASE_URL


def download_moodle_file(client: httpx.Client, url: str, dest_dir: str = "./downloads") -> Dict[str, Any]:
    """Stream and save authenticated Moodle file to local directory."""
    if not url.startswith(BASE_URL):
        raise ValueError("Hanya URL di domain classroom.its.ac.id yang boleh didownload.")
    dest = Path(dest_dir).expanduser()
    dest.mkdir(parents=True, exist_ok=True)
    filename = url.split("?")[0].rstrip("/").split("/")[-1] or "file"
    with client.stream("GET", url) as r:
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
