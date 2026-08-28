import json
import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

logger = logging.getLogger("analyzer")

MODEL = os.environ.get("ANALYSIS_MODEL", "claude-sonnet-5")

SYSTEM_PROMPT = """You are a media-literacy assistant. Given a news article, analyze how it is \
framed and what factual claims it makes. You are not fact-checking against the outside world — \
you don't have search access — you are only describing what is on the page: tone, word choice, \
what's emphasized or omitted, and which concrete claims a reader would need to verify elsewhere.

You also rate the political lean of THIS PIECE OF WRITING specifically — based only on its tone, \
word choice, framing, and what it chooses to emphasize or leave out — not the outlet's general \
reputation. A "center" outlet can still publish a slanted piece, and a "left" or "right" outlet \
can publish a straight one; judge the text in front of you.

Respond with ONLY a JSON object, no other text, in this exact shape:
{"framing_notes": "2-4 sentences on tone, loaded language, and framing choices in this piece", \
"claims": ["claim 1", "claim 2", "claim 3"], \
"bias_label": "one of: left, lean-left, center, lean-right, right", \
"bias_explanation": "1 sentence pointing to specific wording/framing in the text that drove this rating"}

List 3-6 of the most load-bearing factual claims in the article as short standalone sentences. \
If the piece is mostly opinion/analysis with few checkable claims, say so in framing_notes and \
return an empty claims list. If the piece reads as straight, neutral reporting, use "center" for \
bias_label and say so in bias_explanation."""

BIAS_LABELS = {"left", "lean-left", "center", "lean-right", "right"}


@dataclass
class AnalysisResult:
    framing_notes: str
    claims: list
    bias_label: str = ""
    bias_explanation: str = ""


def is_configured() -> bool:
    return bool(os.environ.get("ANTHROPIC_API_KEY"))


def analyze_article(title: str, text: str) -> Optional[AnalysisResult]:
    if not is_configured():
        return None

    import anthropic

    client = anthropic.Anthropic()
    body = text[:8000]

    try:
        response = client.messages.create(
            model=MODEL,
            max_tokens=900,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": f"Title: {title}\n\nArticle text:\n{body}"}],
        )
    except Exception as exc:
        logger.warning("analysis request failed: %s", exc)
        return None

    raw = "".join(block.text for block in response.content if block.type == "text").strip()
    try:
        data = json.loads(raw)
        bias_label = data.get("bias_label", "").strip().lower()
        return AnalysisResult(
            framing_notes=data.get("framing_notes", "").strip(),
            claims=[c.strip() for c in data.get("claims", []) if c.strip()],
            bias_label=bias_label if bias_label in BIAS_LABELS else "",
            bias_explanation=data.get("bias_explanation", "").strip(),
        )
    except (json.JSONDecodeError, AttributeError):
        logger.warning("could not parse analysis response: %s", raw[:200])
        return AnalysisResult(framing_notes=raw, claims=[])
