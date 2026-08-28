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

Respond with ONLY a JSON object, no other text, in this exact shape:
{"framing_notes": "2-4 sentences on tone, loaded language, and framing choices in this piece", \
"claims": ["claim 1", "claim 2", "claim 3"]}

List 3-6 of the most load-bearing factual claims in the article as short standalone sentences. \
If the piece is mostly opinion/analysis with few checkable claims, say so in framing_notes and \
return an empty claims list."""


@dataclass
class AnalysisResult:
    framing_notes: str
    claims: list


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
            max_tokens=600,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": f"Title: {title}\n\nArticle text:\n{body}"}],
        )
    except Exception as exc:
        logger.warning("analysis request failed: %s", exc)
        return None

    raw = "".join(block.text for block in response.content if block.type == "text").strip()
    try:
        data = json.loads(raw)
        return AnalysisResult(
            framing_notes=data.get("framing_notes", "").strip(),
            claims=[c.strip() for c in data.get("claims", []) if c.strip()],
        )
    except (json.JSONDecodeError, AttributeError):
        logger.warning("could not parse analysis response: %s", raw[:200])
        return AnalysisResult(framing_notes=raw, claims=[])
