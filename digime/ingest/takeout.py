import json
import mailbox
import os
from pathlib import Path

from digime.models import Memory


def _clean(text):
    if not text:
        return ""
    return " ".join(str(text).split())


def _find_files(base: Path, names):
    for name in names:
        p = base / name
        if p.exists():
            yield p


def _yield_json_files(dir_path: Path):
    for root, _, files in os.walk(dir_path):
        for f in files:
            if f.endswith(".json"):
                yield Path(root) / f


def load_watch_history(path: Path):
    data = json.loads(path.read_text(encoding="utf-8", errors="ignore"))
    for item in data:
        if not isinstance(item, dict):
            continue
        title = _clean(item.get("title") or item.get("header"))
        url = item.get("titleUrl") or item.get("url") or ""
        if not title:
            continue
        channel = ""
        subtitles = item.get("subtitles")
        if isinstance(subtitles, list) and subtitles:
            channel = _clean(subtitles[0].get("name", ""))
        text = title if not channel else f"{title} — {channel}"
        yield Memory(
            source="youtube",
            title=title,
            text=text,
            url=url,
            ts=item.get("time", ""),
            metadata={"channel": channel, "products": item.get("products", [])},
        )


def load_my_activity(path: Path):
    data = json.loads(path.read_text(encoding="utf-8", errors="ignore"))
    if isinstance(data, dict):
        data = data.get("data", [])
    for item in data:
        if not isinstance(item, dict):
            continue
        title = _clean(item.get("title") or item.get("header"))
        if not title:
            continue
        yield Memory(
            source="activity",
            title=title,
            text=title,
            url=item.get("titleUrl") or "",
            ts=item.get("time", ""),
            metadata={"products": item.get("products", [])},
        )


def load_mbox(path: Path):
    mbox = mailbox.mbox(str(path))
    for msg in mbox:
        subject = _clean(msg.get("Subject", ""))
        body = _clean(msg.get_payload(decode=False) if msg.is_multipart() else msg.get_payload())
        if not subject and not body:
            continue
        body = body[:2000]
        text = f"{subject}\n{body}" if subject else body
        yield Memory(
            source="gmail",
            title=subject or "(no subject)",
            text=text,
            ts=msg.get("Date", ""),
            metadata={
                "from": msg.get("From", ""),
                "to": msg.get("To", ""),
            },
        )


def ingest_takeout(takeout_dir: Path):
    memories = []
    for path in _yield_json_files(takeout_dir / "YouTube and YouTube Music"):
        if path.name == "watch-history.json":
            memories.extend(load_watch_history(path))

    for path in _yield_json_files(takeout_dir / "My Activity"):
        memories.extend(load_my_activity(path))

    for path in _find_files(takeout_dir, ["Mail"]):
        if path.is_dir():
            for mbox in path.glob("*.mbox"):
                memories.extend(load_mbox(mbox))

    return memories
