import re
from collections import defaultdict
from datetime import datetime, timedelta

from sqlmodel import Session, select

from .database import engine
from .models import Article, StoryCluster

WINDOW_HOURS = 72
JACCARD_THRESHOLD = 0.32
MIN_OVERLAP = 3
MIN_CLUSTER_SOURCES = 2

TOKEN_RE = re.compile(r"[A-Za-z0-9']+")

STOPWORDS = {
    "the", "a", "an", "and", "or", "but", "of", "to", "in", "on", "for", "with", "as", "by",
    "at", "from", "is", "are", "was", "were", "be", "been", "being", "it", "its", "this",
    "that", "these", "those", "after", "amid", "amidst", "over", "under", "into", "about",
    "against", "between", "new", "says", "say", "said", "report", "reports", "reported",
    "how", "what", "why", "who", "which", "will", "has", "have", "had", "not", "no", "up",
    "down", "out", "off", "than", "then", "their", "his", "her", "he", "she", "they", "we",
    "you", "i", "if", "so", "just", "more", "most", "some", "all", "one", "two", "first",
    "last", "year", "years", "week", "weeks", "day", "days", "today", "could", "would",
    "should", "can", "may", "might", "amid", "amidst", "into", "your", "our",
}


def tokenize(text: str) -> set:
    return {
        w for w in (t.lower() for t in TOKEN_RE.findall(text or ""))
        if len(w) > 2 and w not in STOPWORDS
    }


def jaccard(a: set, b: set) -> float:
    if not a or not b:
        return 0.0
    union = len(a | b)
    return len(a & b) / union if union else 0.0


def assign_clusters() -> None:
    """Group newly-fetched articles into cross-outlet story clusters.

    Runs after every fetch cycle. New articles are matched against recently-active
    clusters first, then self-clustered against each other (blocked by shared topic,
    same outlet excluded so it can't corroborate itself), and finally promoted to a
    real StoryCluster only once at least two distinct outlets are covering the same
    story. Everything else stays unclustered and shows up in the river instead.
    """
    with Session(engine) as session:
        cutoff = datetime.utcnow() - timedelta(hours=WINDOW_HOURS)

        unclustered = session.exec(
            select(Article).where(Article.cluster_id.is_(None), Article.published_at >= cutoff)
        ).all()
        if not unclustered:
            return

        recent_clusters = session.exec(
            select(StoryCluster).where(StoryCluster.updated_at >= cutoff)
        ).all()

        cluster_tokens = {}
        for c in recent_clusters:
            members = session.exec(select(Article).where(Article.cluster_id == c.id)).all()
            toks = set()
            for m in members:
                toks |= tokenize(m.title)
            cluster_tokens[c.id] = toks

        pending = []
        for art in unclustered:
            art_tokens = tokenize(art.title)
            best_cluster, best_score = None, 0.0
            for cid, toks in cluster_tokens.items():
                score = jaccard(art_tokens, toks)
                if score >= JACCARD_THRESHOLD and len(art_tokens & toks) >= MIN_OVERLAP and score > best_score:
                    best_cluster, best_score = cid, score

            if best_cluster is not None:
                art.cluster_id = best_cluster
                session.add(art)
                cluster_tokens[best_cluster] |= art_tokens
                cluster = session.get(StoryCluster, best_cluster)
                cluster.updated_at = datetime.utcnow()
                session.add(cluster)
            else:
                pending.append(art)

        # union-find over the leftovers, blocked by shared topic to keep comparisons cheap
        parent = {a.id: a.id for a in pending}

        def find(x):
            while parent[x] != x:
                parent[x] = parent[parent[x]]
                x = parent[x]
            return x

        def union(x, y):
            rx, ry = find(x), find(y)
            if rx != ry:
                parent[rx] = ry

        token_cache = {a.id: tokenize(a.title) for a in pending}
        topic_buckets = defaultdict(list)
        for a in pending:
            for t in a.topics.split(","):
                if t:
                    topic_buckets[t].append(a)

        compared = set()
        for bucket in topic_buckets.values():
            for i in range(len(bucket)):
                for j in range(i + 1, len(bucket)):
                    a1, a2 = bucket[i], bucket[j]
                    if a1.source_id == a2.source_id:
                        continue
                    key = (min(a1.id, a2.id), max(a1.id, a2.id))
                    if key in compared:
                        continue
                    compared.add(key)
                    t1, t2 = token_cache[a1.id], token_cache[a2.id]
                    if jaccard(t1, t2) >= JACCARD_THRESHOLD and len(t1 & t2) >= MIN_OVERLAP:
                        union(a1.id, a2.id)

        groups = defaultdict(list)
        for a in pending:
            groups[find(a.id)].append(a)

        for members in groups.values():
            distinct_sources = {a.source_id for a in members}
            if len(distinct_sources) < MIN_CLUSTER_SOURCES:
                continue
            topics = sorted({t for a in members for t in a.topics.split(",") if t})
            cluster = StoryCluster(topics=",".join(topics))
            session.add(cluster)
            session.flush()
            for a in members:
                a.cluster_id = cluster.id
                session.add(a)

        session.commit()
