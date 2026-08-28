#!/usr/bin/env python3
"""Build a static snapshot of the site into docs/ for GitHub Pages.

Runs a fresh fetch + cluster cycle into a throwaway SQLite DB (never touches
the local dev news.db), eagerly extracts full text and images for every
article that will get its own page, then renders flat HTML files with
Jinja2 directly — no server involved at request time.
"""
import hashlib
import os
import shutil
import sys
import tempfile
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

# must happen before any `app.*` import binds to the engine
_tmp_dir = Path(tempfile.mkdtemp())
os.environ["NEWS_DB_PATH"] = str(_tmp_dir / "build.db")

import jinja2
from sqlmodel import Session, select

from app.cluster_present import build_cluster_card
from app.clustering import WINDOW_HOURS, assign_clusters
from app.database import engine, init_db
from app.fetcher import fetch_all_sources
from app.models import Article, Source
from app.reader import extract_article
from app.sources import BIAS_COLORS, BIAS_ORDER, BIAS_SHORT, TOPICS
from app.textutil import clean_paragraphs, time_ago

DOCS_DIR = ROOT / "docs"


def article_slug(url: str) -> str:
    """Stable filename derived from the article's own URL.

    The build DB is a fresh throwaway per run, so its autoincrement ids are
    not stable across rebuilds — using them for filenames meant every
    3-hourly rebuild silently deleted/renamed previously-linked article
    pages, breaking any tab or bookmark left open from an older build.
    """
    return hashlib.sha1(url.encode("utf-8")).hexdigest()[:12]


def cluster_slug(card: dict) -> str:
    member_urls = sorted(a.url for a in card["members"])
    return hashlib.sha1("|".join(member_urls).encode("utf-8")).hexdigest()[:12]


def main() -> None:
    print(f"Building into throwaway DB at {os.environ['NEWS_DB_PATH']}")
    init_db()
    fetch_all_sources()
    assign_clusters()

    with Session(engine) as session:
        sources = {s.id: s for s in session.exec(select(Source)).all()}

        cutoff = datetime.utcnow() - timedelta(hours=WINDOW_HOURS)
        recent = session.exec(
            select(Article).where(Article.published_at >= cutoff).order_by(Article.published_at.desc())
        ).all()

        river_articles = [a for a in recent if not a.cluster_id][:60]

        by_cluster = defaultdict(list)
        for a in recent:
            if a.cluster_id:
                by_cluster[a.cluster_id].append(a)

        clusters = [build_cluster_card(cid, members, sources) for cid, members in by_cluster.items()]
        clusters.sort(key=lambda c: c["source_count"], reverse=True)

        # only representative articles (cluster "members") plus river articles are
        # ever linked to, so only those need their own static page
        linked_articles = {a.id: a for a in river_articles}
        for card in clusters:
            for a in card["members"]:
                linked_articles[a.id] = a

        print(f"Extracting full text/images for {len(linked_articles)} articles...")
        for i, article in enumerate(linked_articles.values()):
            source = sources[article.source_id]
            if source.paywalled or article.content:
                continue
            text, image_url = extract_article(article.url)
            if text:
                article.content = text
            if image_url and not article.image_url:
                article.image_url = image_url
            if text or image_url:
                session.add(article)
            if (i + 1) % 25 == 0:
                print(f"  {i + 1}/{len(linked_articles)}")
        session.commit()

        # re-build cards now that content/images have been backfilled
        clusters = [build_cluster_card(cid, members, sources) for cid, members in by_cluster.items()]
        clusters.sort(key=lambda c: c["source_count"], reverse=True)
        clusters_by_id = {c["id"]: c for c in clusters}

        by_size_desc = sorted(clusters, key=lambda c: c["source_count"], reverse=True)
        barely_left = next((c for c in by_size_desc if c["right_count"] >= 2 and c["left_count"] == 0), None)
        barely_right = next(
            (c for c in by_size_desc if c["left_count"] >= 2 and c["right_count"] == 0 and c is not barely_left),
            None,
        )
        featured_ids = {c["id"] for c in (barely_left, barely_right) if c}
        remaining = [c for c in clusters if c["id"] not in featured_ids]
        barely_anyone = min(remaining, key=lambda c: c["source_count"]) if remaining else None

        now = datetime.now()
        build_time = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")

        article_slugs = {a.id: article_slug(a.url) for a in linked_articles.values()}
        cluster_slugs = {cid: cluster_slug(card) for cid, card in clusters_by_id.items()}

        env = jinja2.Environment(loader=jinja2.FileSystemLoader(str(ROOT / "app" / "templates")))
        env.filters["time_ago"] = time_ago
        env.globals.update({
            "BIAS_COLORS": BIAS_COLORS,
            "BIAS_SHORT": BIAS_SHORT,
            "TOPIC_LABELS": dict(TOPICS),
            "css_href": "static/style.css",
            "STATIC": True,
            "build_time": build_time,
            "url_home": lambda: "index.html",
            "url_article": lambda article_id: f"article-{article_slugs[article_id]}.html",
            "url_cluster": lambda cluster_id: f"cluster-{cluster_slugs[cluster_id]}.html",
        })

        if DOCS_DIR.exists():
            shutil.rmtree(DOCS_DIR)
        DOCS_DIR.mkdir(parents=True)
        (DOCS_DIR / "static").mkdir()
        (DOCS_DIR / ".nojekyll").touch()

        for name in ("style.css", "filter.js"):
            shutil.copy(ROOT / "app" / "static" / name, DOCS_DIR / "static" / name)

        index_tpl = env.get_template("index.html")
        (DOCS_DIR / "index.html").write_text(index_tpl.render(
            clusters=clusters,
            river_articles=river_articles,
            sources=sources,
            has_followed=False,
            all_topics=TOPICS,
            followed_slugs=set(),
            bias_order=BIAS_ORDER,
            current_bias="",
            barely_left=barely_left,
            barely_right=barely_right,
            barely_anyone=barely_anyone,
            day_abbr=now.strftime("%a").upper(),
            day_num=now.strftime("%d"),
            month_abbr=now.strftime("%b").upper(),
            year=now.strftime("%Y"),
        ))

        cluster_tpl = env.get_template("cluster.html")
        for cid, card in clusters_by_id.items():
            (DOCS_DIR / f"cluster-{cluster_slugs[cid]}.html").write_text(cluster_tpl.render(
                cluster=card, sources=sources, bias_order=BIAS_ORDER,
            ))

        article_tpl = env.get_template("article.html")
        for article in linked_articles.values():
            source = sources[article.source_id]
            paragraphs = clean_paragraphs(article.content, article.title) if article.content else []
            (DOCS_DIR / f"article-{article_slugs[article.id]}.html").write_text(article_tpl.render(
                article=article, source=source, paragraphs=paragraphs,
                analysis=None, analysis_configured=False,
            ))

    total_pages = 1 + len(clusters_by_id) + len(linked_articles)
    print(f"Built {total_pages} pages into {DOCS_DIR}")


if __name__ == "__main__":
    main()
