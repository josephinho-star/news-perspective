import html
import re
from datetime import datetime

_TAG_RE = re.compile(r"<[^>]+>")


def time_ago(when) -> str:
    if not when:
        return ""
    delta = datetime.utcnow() - when
    seconds = delta.total_seconds()
    if seconds < 3600:
        return f"{max(1, int(seconds // 60))}m ago"
    if seconds < 86400:
        return f"{int(seconds // 3600)}h ago"
    return f"{int(seconds // 86400)}d ago"


def unescape(raw: str) -> str:
    return html.unescape(raw or "").strip()


def strip_html(raw: str) -> str:
    return unescape(_TAG_RE.sub("", raw or ""))


def clean_paragraphs(content: str, title: str) -> list:
    """Drop short byline/metadata cruft lines that extractors often leave behind."""
    title_norm = title.strip().lower()
    paragraphs = []
    for line in (content or "").split("\n"):
        line = line.strip()
        if not line:
            continue
        if line.lower() == title_norm:
            continue
        if len(line) < 25 and not line.endswith((".", "?", "!", '"')):
            continue
        paragraphs.append(line)
    return paragraphs
