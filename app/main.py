import os
from collections import defaultdict
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from pathlib import Path

from apscheduler.schedulers.background import BackgroundScheduler
from fastapi import Depends, FastAPI, Request
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlmodel import Session, select

from .analyzer import analyze_article, is_configured
from .cluster_present import build_cluster_card, build_related
from .clustering import WINDOW_HOURS, assign_clusters
from .database import get_session, init_db
from .fetcher import fetch_all_sources
from .models import Analysis, Article, FollowedTopic, Source, StoryCluster
from .reader import extract_article
from .sources import BIAS_COLORS, BIAS_ORDER, BIAS_SHORT, TOPICS
from .textutil import clean_paragraphs, time_ago

scheduler = BackgroundScheduler()


def fetch_and_cluster() -> None:
    fetch_all_sources()
    assign_clusters()


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    fetch_and_cluster()
    scheduler.add_job(fetch_and_cluster, "interval", minutes=45, id="fetch_and_cluster")
    scheduler.start()
    yield
    scheduler.shutdown()


app = FastAPI(lifespan=lifespan)


class NoCacheStaticFiles(StaticFiles):
    async def get_response(self, path: str, scope):
        response = await super().get_response(path, scope)
        response.headers["Cache-Control"] = "no-cache"
        return response


app.mount("/static", NoCacheStaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")
templates.env.globals["BIAS_COLORS"] = BIAS_COLORS
templates.env.globals["BIAS_SHORT"] = BIAS_SHORT
templates.env.globals["BIAS_ORDER"] = BIAS_ORDER
templates.env.globals["TOPIC_LABELS"] = dict(TOPICS)
templates.env.globals["TOPICS"] = TOPICS
templates.env.globals["css_href"] = f"/static/style.css?v={int(os.path.getmtime(Path('app/static/style.css')))}"
templates.env.globals["STATIC"] = False
templates.env.globals["url_home"] = lambda: "/"
templates.env.globals["url_article"] = lambda article_id: f"/article/{article_id}"
templates.env.globals["url_cluster"] = lambda cluster_id: f"/cluster/{cluster_id}"
templates.env.filters["time_ago"] = time_ago


@app.get("/")
def index(request: Request, bias: str = "", topic: str = "", session: Session = Depends(get_session)):
    followed_rows = session.exec(select(FollowedTopic)).all()
    followed = {f.topic_slug for f in followed_rows if f.followed}
    if topic:
        followed = {topic}

    sources = {s.id: s for s in session.exec(select(Source)).all()}

    cutoff = datetime.utcnow() - timedelta(hours=WINDOW_HOURS)
    recent = session.exec(
        select(Article).where(Article.published_at >= cutoff).order_by(Article.published_at.desc())
    ).all()

    def visible(article: Article) -> bool:
        if followed and not (set(article.topics.split(",")) & followed):
            return False
        if bias in BIAS_ORDER and sources[article.source_id].bias_label != bias:
            return False
        return True

    recent = [a for a in recent if visible(a)]
    river_articles = [a for a in recent if not a.cluster_id][:60]

    by_cluster = defaultdict(list)
    for a in recent:
        if a.cluster_id:
            by_cluster[a.cluster_id].append(a)

    clusters = [build_cluster_card(cid, members, sources) for cid, members in by_cluster.items()]
    clusters.sort(key=lambda c: c["source_count"], reverse=True)

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

    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "clusters": clusters,
            "river_articles": river_articles,
            "sources": sources,
            "has_followed": bool(followed),
            "all_topics": TOPICS,
            "followed_slugs": followed,
            "bias_order": BIAS_ORDER,
            "current_bias": bias,
            "barely_left": barely_left,
            "barely_right": barely_right,
            "barely_anyone": barely_anyone,
            "day_abbr": now.strftime("%a").upper(),
            "day_num": now.strftime("%d"),
            "month_abbr": now.strftime("%b").upper(),
            "year": now.strftime("%Y"),
        },
    )


@app.get("/cluster/{cluster_id}")
def cluster_page(cluster_id: int, request: Request, session: Session = Depends(get_session)):
    cluster = session.get(StoryCluster, cluster_id)
    members = session.exec(select(Article).where(Article.cluster_id == cluster_id)).all()
    sources = {s.id: s for s in session.exec(select(Source)).all()}
    card = build_cluster_card(cluster_id, members, sources)

    return templates.TemplateResponse(
        "cluster.html",
        {"request": request, "cluster": card, "sources": sources, "bias_order": BIAS_ORDER},
    )


@app.get("/topics")
def topics_page(request: Request, session: Session = Depends(get_session)):
    followed = {f.topic_slug for f in session.exec(select(FollowedTopic))}
    followed_map = {f.topic_slug: f.followed for f in session.exec(select(FollowedTopic))}
    return templates.TemplateResponse(
        "topics.html",
        {"request": request, "topics": TOPICS, "followed_map": followed_map},
    )


@app.post("/topics/toggle")
async def toggle_topic(request: Request, session: Session = Depends(get_session)):
    form = await request.form()
    slug = form.get("slug")
    next_url = form.get("next") or "/"
    if not next_url.startswith("/"):
        next_url = "/"
    row = session.get(FollowedTopic, slug)
    if row:
        row.followed = not row.followed
        session.add(row)
        session.commit()
    return RedirectResponse(url=next_url, status_code=303)


@app.post("/topics")
async def save_topics(request: Request, session: Session = Depends(get_session)):
    form = await request.form()
    selected = set(form.getlist("topic"))
    for slug, _label in TOPICS:
        row = session.get(FollowedTopic, slug)
        row.followed = slug in selected
        session.add(row)
    session.commit()
    return RedirectResponse(url="/", status_code=303)


@app.get("/article/{article_id}")
def article_page(article_id: int, request: Request, session: Session = Depends(get_session)):
    article = session.get(Article, article_id)
    source = session.get(Source, article.source_id)

    if not source.paywalled and not article.content:
        text, image_url = extract_article(article.url)
        if text:
            article.content = text
        if image_url and not article.image_url:
            article.image_url = image_url
        if text or image_url:
            session.add(article)
            session.commit()

    paragraphs = clean_paragraphs(article.content, article.title) if article.content else []
    analysis = session.get(Analysis, article_id)

    sources = {s.id: s for s in session.exec(select(Source)).all()}
    cutoff = datetime.utcnow() - timedelta(hours=WINDOW_HOURS)
    candidates = session.exec(
        select(Article).where(Article.published_at >= cutoff).order_by(Article.published_at.desc())
    ).all()
    related = build_related(candidates, sources, article)

    return templates.TemplateResponse(
        "article.html",
        {
            "request": request,
            "article": article,
            "source": source,
            "paragraphs": paragraphs,
            "analysis": analysis,
            "analysis_configured": is_configured(),
            "related": related,
        },
    )


@app.post("/article/{article_id}/analyze")
def analyze(article_id: int, session: Session = Depends(get_session)):
    article = session.get(Article, article_id)
    text = article.content or article.summary

    result = analyze_article(article.title, text)
    if result:
        analysis = Analysis(
            article_id=article_id,
            framing_notes=result.framing_notes,
            claims="\n".join(result.claims),
            bias_label=result.bias_label,
            bias_explanation=result.bias_explanation,
        )
        session.merge(analysis)
        session.commit()

    return RedirectResponse(url=f"/article/{article_id}", status_code=303)


@app.post("/refresh")
def refresh():
    fetch_and_cluster()
    return RedirectResponse(url="/", status_code=303)
