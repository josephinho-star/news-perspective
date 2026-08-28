import os
from pathlib import Path

from sqlalchemy import event, text
from sqlmodel import SQLModel, Session, create_engine, select

from .models import FollowedTopic, Source
from .sources import SEED_SOURCES, TOPICS

DB_PATH = Path(os.environ.get("NEWS_DB_PATH") or (Path(__file__).resolve().parent.parent / "news.db"))
engine = create_engine(
    f"sqlite:///{DB_PATH}",
    connect_args={"check_same_thread": False, "timeout": 30},
)


@event.listens_for(engine, "connect")
def _set_sqlite_pragma(dbapi_connection, _record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA busy_timeout=30000")
    cursor.close()


def init_db() -> None:
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        article_cols = {row[1] for row in session.exec(text("PRAGMA table_info(article)"))}
        if "cluster_id" not in article_cols:
            session.exec(text("ALTER TABLE article ADD COLUMN cluster_id INTEGER"))
            session.commit()
        if "image_url" not in article_cols:
            session.exec(text("ALTER TABLE article ADD COLUMN image_url TEXT"))
            session.commit()

        analysis_cols = {row[1] for row in session.exec(text("PRAGMA table_info(analysis)"))}
        if "bias_label" not in analysis_cols:
            session.exec(text("ALTER TABLE analysis ADD COLUMN bias_label TEXT DEFAULT ''"))
            session.commit()
        if "bias_explanation" not in analysis_cols:
            session.exec(text("ALTER TABLE analysis ADD COLUMN bias_explanation TEXT DEFAULT ''"))
            session.commit()

        existing_source_names = {s.name for s in session.exec(select(Source)).all()}
        for row in SEED_SOURCES:
            if row["name"] not in existing_source_names:
                session.add(Source(**row))

        existing_topic_slugs = {f.topic_slug for f in session.exec(select(FollowedTopic)).all()}
        for slug, _label in TOPICS:
            if slug not in existing_topic_slugs:
                session.add(FollowedTopic(topic_slug=slug, followed=True))

        session.commit()


def get_session():
    with Session(engine) as session:
        yield session
