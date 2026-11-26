import datetime
import shutil
import sqlite3
import tempfile
from pathlib import Path

from digime.models import Memory

WINDOWS_EPOCH = 11644473600


def _chrome_time_to_iso(micros):
    if not micros:
        return ""
    seconds = micros / 1_000_000 - WINDOWS_EPOCH
    try:
        return datetime.datetime.fromtimestamp(seconds, tz=datetime.timezone.utc).isoformat()
    except (ValueError, OSError):
        return ""


def load_chrome_history(chrome_profile: Path, youtube_only: bool = False, limit: int = 10000):
    history_db = chrome_profile / "History"
    if not history_db.exists():
        raise FileNotFoundError(f"Chrome History not found at {history_db}")

    with tempfile.NamedTemporaryFile(suffix=".sqlite", delete=False) as tmp:
        shutil.copyfile(history_db, tmp.name)
        tmp_path = tmp.name

    conn = sqlite3.connect(tmp_path)
    conn.row_factory = sqlite3.Row
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT url, title, last_visit_time FROM urls ORDER BY last_visit_time DESC LIMIT ?",
            (limit,),
        )
        rows = cur.fetchall()
    finally:
        conn.close()
        Path(tmp_path).unlink(missing_ok=True)

    for row in rows:
        url = row["url"] or ""
        if youtube_only and "youtube.com" not in url:
            continue
        title = (row["title"] or url).strip()
        if not title:
            continue
        source = "youtube" if "youtube.com" in url else "browser"
        yield Memory(
            source=source,
            title=title,
            text=title,
            url=url,
            ts=_chrome_time_to_iso(row["last_visit_time"]),
        )
