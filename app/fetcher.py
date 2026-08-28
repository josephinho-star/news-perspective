import logging
import re
from datetime import datetime
from time import mktime

import feedparser
from sqlmodel import Session, select

from .database import engine
from .models import Article, Source
from .textutil import strip_html, unescape

logger = logging.getLogger("fetcher")

_IMG_TAG_RE = re.compile(r'<img[^>]+src="([^"]+)"')


def _extract_image(entry) -> str:
    thumb = entry.get("media_thumbnail")
    if thumb and thumb[0].get("url"):
        return thumb[0]["url"]

    for media in entry.get("media_content", []):
        if media.get("url") and (media.get("medium") == "image" or "image" in media.get("type", "")):
            return media["url"]

    for enc in entry.get("enclosures", []):
        if enc.get("type", "").startswith("image") and enc.get("href"):
            return enc["href"]

    match = _IMG_TAG_RE.search(entry.get("summary", ""))
    if match:
        return match.group(1)

    return ""


def fetch_all_sources() -> None:
    with Session(engine) as session:
        sources = session.exec(select(Source)).all()
        for source in sources:
            try:
                _fetch_source(session, source)
            except Exception as exc:  # a single bad feed shouldn't stop the rest
                logger.warning("failed to fetch %s: %s", source.name, exc)
        session.commit()


def _fetch_source(session: Session, source: Source) -> None:
    parsed = feedparser.parse(source.feed_url)
    for entry in parsed.entries:
        url = entry.get("link")
        if not url:
            continue
        existing = session.exec(select(Article).where(Article.url == url)).first()
        if existing:
            continue

        published_at = None
        if entry.get("published_parsed"):
            published_at = datetime.fromtimestamp(mktime(entry.published_parsed))

        summary = strip_html(entry.get("summary", ""))[:600]
        image_url = _extract_image(entry)

        session.add(
            Article(
                source_id=source.id,
                title=unescape(entry.get("title", "(untitled)")),
                url=url,
                summary=summary,
                topics=source.topics,
                published_at=published_at,
                image_url=image_url or None,
            )
        )
