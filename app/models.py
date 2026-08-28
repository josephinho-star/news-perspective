from datetime import datetime
from typing import Optional

from sqlmodel import SQLModel, Field


class Source(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    feed_url: str
    bias_label: str  # left | lean-left | center | lean-right | right
    topics: str  # comma-separated topic slugs, e.g. "world,us-politics"
    paywalled: bool = False


class StoryCluster(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    topics: str = ""  # union of member articles' topics
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class Article(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    source_id: int = Field(foreign_key="source.id")
    title: str
    url: str = Field(unique=True, index=True)
    summary: str = ""
    content: Optional[str] = None  # lazily populated full text for open sources
    topics: str = ""  # inherited from source at fetch time
    published_at: Optional[datetime] = None
    fetched_at: datetime = Field(default_factory=datetime.utcnow)
    cluster_id: Optional[int] = Field(default=None, foreign_key="storycluster.id", index=True)
    image_url: Optional[str] = None


class FollowedTopic(SQLModel, table=True):
    topic_slug: str = Field(primary_key=True)
    followed: bool = True


class Analysis(SQLModel, table=True):
    article_id: int = Field(primary_key=True, foreign_key="article.id")
    framing_notes: str
    claims: str  # newline-separated flagged claims
    bias_label: str = ""  # left | lean-left | center | lean-right | right, rated from this article's own text
    bias_explanation: str = ""
    generated_at: datetime = Field(default_factory=datetime.utcnow)
