from .sources import BIAS_ORDER
from .textutil import time_ago


def build_cluster_card(cluster_id: int, members: list, sources: dict) -> dict:
    """members: Article rows sharing a cluster_id. sources: {source_id: Source}."""

    def sort_key(a):
        return a.published_at or a.fetched_at

    # one representative article per outlet (earliest), so one outlet posting
    # two updates about the same story doesn't get double-counted
    by_source = {}
    for a in members:
        existing = by_source.get(a.source_id)
        if not existing or sort_key(a) < sort_key(existing):
            by_source[a.source_id] = a
    reps = list(by_source.values())

    counts = {label: 0 for label in BIAS_ORDER}
    for a in reps:
        counts[sources[a.source_id].bias_label] += 1

    left_count = counts["left"] + counts["lean-left"]
    right_count = counts["lean-right"] + counts["right"]
    center_count = counts["center"]

    total = len(reps)
    dominant_label, dominant_count = max(
        (("left", left_count), ("center", center_count), ("right", right_count)),
        key=lambda pair: pair[1],
    )
    dominant_pct = round(100 * dominant_count / total) if total else 0

    thin_side = None
    if right_count >= 2 and left_count == 0:
        thin_side = "left"
    elif left_count >= 2 and right_count == 0:
        thin_side = "right"

    lead = min(reps, key=sort_key)
    body = (lead.summary or "")[:280]
    image_url = next((a.image_url for a in sorted(reps, key=sort_key) if a.image_url), None)

    examples = []
    for label in BIAS_ORDER:
        candidate = next((a for a in reps if sources[a.source_id].bias_label == label), None)
        if candidate:
            examples.append({
                "bias_label": label,
                "outlet": sources[candidate.source_id].name,
                "headline": candidate.title,
                "article_id": candidate.id,
            })
        if len(examples) >= 4:
            break

    topics = sorted({t for a in members for t in a.topics.split(",") if t})
    biases_present = [label for label in BIAS_ORDER if counts[label] > 0]

    return {
        "id": cluster_id,
        "headline": lead.title,
        "body": body,
        "image_url": image_url,
        "biases_present": ",".join(biases_present),
        "age": time_ago(lead.published_at),
        "topics": topics,
        "primary_topic": topics[0] if topics else "",
        "source_count": len(reps),
        "counts": counts,
        "left_count": left_count,
        "right_count": right_count,
        "dominant_label": dominant_label,
        "dominant_pct": dominant_pct,
        "thin_side": thin_side,
        "examples": examples,
        "members": sorted(reps, key=lambda a: BIAS_ORDER.index(sources[a.source_id].bias_label)),
    }
