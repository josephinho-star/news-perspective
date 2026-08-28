import logging

import httpx
import trafilatura

logger = logging.getLogger("reader")

_HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; personal-news-reader/1.0)"}


def extract_article(url: str):
    """Fetch the page once and pull both the reading-view text and og:image."""
    try:
        resp = httpx.get(url, headers=_HEADERS, timeout=10, follow_redirects=True)
        resp.raise_for_status()
    except Exception as exc:
        logger.warning("could not fetch %s: %s", url, exc)
        return "", ""

    text = trafilatura.extract(
        resp.text,
        include_comments=False,
        include_tables=False,
        favor_precision=True,
    )

    image_url = ""
    try:
        metadata = trafilatura.extract_metadata(resp.text)
        if metadata and metadata.image:
            image_url = metadata.image
    except Exception as exc:
        logger.warning("could not extract metadata for %s: %s", url, exc)

    return text or "", image_url
