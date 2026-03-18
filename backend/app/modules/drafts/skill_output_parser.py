"""Skill output parser — extracts structured asset-ingest blocks from AI output.

The parser scans AI-generated text for HTML-comment-delimited blocks that the AI
has autonomously decided should flow into the project's asset/evidence system.
Non-block content is returned as plain draft text.
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Block patterns
# ---------------------------------------------------------------------------

_ASSET_INGEST_RE = re.compile(
    r"<!--\s*ASSET_INGEST:\s*type=(\S+)\s*-->\s*(\{.*?\})\s*<!--\s*/ASSET_INGEST\s*-->",
    re.DOTALL,
)

_REVIEW_SCORE_RE = re.compile(
    r"<!--\s*REVIEW_SCORE\s*-->\s*(\{.*?\})\s*<!--\s*/REVIEW_SCORE\s*-->",
    re.DOTALL,
)

_REVISION_ITEM_RE = re.compile(
    r"<!--\s*REVISION_ITEM\s*-->\s*(\{.*?\})\s*<!--\s*/REVISION_ITEM\s*-->",
    re.DOTALL,
)


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass(slots=True)
class AssetIngestBlock:
    asset_type: str
    payload: dict

@dataclass(slots=True)
class ReviewScoreBlock:
    payload: dict

@dataclass(slots=True)
class RevisionItemBlock:
    payload: dict


@dataclass
class ParseResult:
    """Result of parsing skill output."""

    clean_text: str
    """Draft text with all structured blocks removed."""

    assets: list[AssetIngestBlock] = field(default_factory=list)
    review_scores: list[ReviewScoreBlock] = field(default_factory=list)
    revision_items: list[RevisionItemBlock] = field(default_factory=list)

    @property
    def has_structured_blocks(self) -> bool:
        return bool(self.assets or self.review_scores or self.revision_items)


# ---------------------------------------------------------------------------
# Parser
# ---------------------------------------------------------------------------

def parse_skill_output(raw_text: str) -> ParseResult:
    """Parse AI output, extracting structured blocks and returning clean text.

    The parser is lenient — malformed JSON in blocks is logged and skipped,
    never raising exceptions. This ensures draft text is always preserved.
    """
    assets: list[AssetIngestBlock] = []
    review_scores: list[ReviewScoreBlock] = []
    revision_items: list[RevisionItemBlock] = []

    working = raw_text

    # Extract ASSET_INGEST blocks
    for match in _ASSET_INGEST_RE.finditer(raw_text):
        asset_type = match.group(1)
        try:
            payload = json.loads(match.group(2))
            assets.append(AssetIngestBlock(asset_type=asset_type, payload=payload))
        except json.JSONDecodeError:
            logger.warning("Malformed ASSET_INGEST JSON, skipping: %s", match.group(2)[:100])
    working = _ASSET_INGEST_RE.sub("", working)

    # Extract REVIEW_SCORE blocks
    for match in _REVIEW_SCORE_RE.finditer(raw_text):
        try:
            payload = json.loads(match.group(1))
            review_scores.append(ReviewScoreBlock(payload=payload))
        except json.JSONDecodeError:
            logger.warning("Malformed REVIEW_SCORE JSON, skipping: %s", match.group(1)[:100])
    working = _REVIEW_SCORE_RE.sub("", working)

    # Extract REVISION_ITEM blocks
    for match in _REVISION_ITEM_RE.finditer(raw_text):
        try:
            payload = json.loads(match.group(1))
            revision_items.append(RevisionItemBlock(payload=payload))
        except json.JSONDecodeError:
            logger.warning("Malformed REVISION_ITEM JSON, skipping: %s", match.group(1)[:100])
    working = _REVISION_ITEM_RE.sub("", working)

    # Clean up extra blank lines left by block removal
    clean_text = re.sub(r"\n{3,}", "\n\n", working).strip()

    return ParseResult(
        clean_text=clean_text,
        assets=assets,
        review_scores=review_scores,
        revision_items=revision_items,
    )
