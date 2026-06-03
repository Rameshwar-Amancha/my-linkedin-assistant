"""
trend_service.py — Business logic for trend discovery

Aggregates trends from multiple public sources:
- Hacker News (via official Algolia API, date-sorted for recency)
- RSS feeds (via feedparser — tech news, Google Trends, Reddit, ProductHunt, DEV.to)

All sources are publicly accessible. No private LinkedIn data is scraped.
Rate limiting and caching prevent aggressive scraping patterns.

Scoring:
  composite = engagement_potential × 0.6 + recency_score × 0.4

Deduplication uses word-set Jaccard similarity so near-duplicate headlines
(same story, different source wording) are merged into one result with a
cross-source engagement boost (+1 per additional confirming source, capped at +2).
"""

from __future__ import annotations

import logging
import re
from datetime import datetime, timezone

from app.models.schemas import TrendItem, TrendsResponse
from app.scraping.hn_client import HackerNewsClient
from app.scraping.rss_reader import RSSReader
from app.utils.cache import get_cache, set_cache

logger = logging.getLogger(__name__)

CACHE_KEY_PREFIX = "trends:"
CACHE_TTL_SECONDS = 900  # 15 minutes — fresh enough for real-time trends

CATEGORY_KEYWORDS: dict[str, list[str]] = {
    "tech": [
        "software", "programming", "developer", "cloud", "kubernetes", "web", "api",
        "open source", "devops", "platform", "infrastructure", "security", "breach",
    ],
    "ai": [
        "ai", "machine learning", "llm", "gpt", "neural", "model", "deep learning",
        "generative", "claude", "gemini", "copilot", "agent", "rag", "embedding",
        "transformer", "diffusion", "chatbot", "inference",
    ],
    "business": [
        "startup", "funding", "vc", "revenue", "saas", "growth", "enterprise",
        "ipo", "acquisition", "raise", "series", "valuation", "market", "profit",
    ],
    "leadership": [
        "management", "team", "culture", "hiring", "remote", "rto", "return to office",
        "ceo", "leadership", "layoff", "diversity", "inclusion", "productivity",
    ],
    "startups": [
        "yc", "y combinator", "seed", "series a", "founder", "product-market fit",
        "mvp", "bootstrap", "indie hacker", "b2b", "b2c", "pivot",
    ],
}

_STOP_WORDS = frozenset({
    "a", "an", "the", "and", "or", "but", "in", "on", "at", "to", "for",
    "of", "with", "is", "are", "was", "were", "be", "been", "has", "have",
    "it", "its", "that", "this", "by", "as", "from", "into", "about", "after",
    "new", "via", "will", "can", "your", "you", "how", "why", "what", "when",
})

JACCARD_THRESHOLD = 0.35  # titles sharing ≥35% non-stop words are treated as the same story


class TrendService:
    def __init__(self, db=None) -> None:
        self._hn = HackerNewsClient()
        self._rss = RSSReader()
        self._db = db  # optional; used for webhook notifications

    async def get_trends(self, category: str = "", limit: int = 15) -> TrendsResponse:
        """
        Fetch and aggregate trending topics.
        Returns cached results if available (TTL: 15 min).
        """
        cache_key = f"{CACHE_KEY_PREFIX}{category}:{limit}"

        cached = await get_cache(cache_key)
        if cached:
            logger.debug("Returning cached trends for key=%s", cache_key)
            return TrendsResponse(
                trends=[TrendItem(**t) for t in cached["trends"]],
                cached=True,
                fetched_at=cached["fetched_at"],
            )

        trends = await self._fetch_all_trends(category, limit)

        now_iso = datetime.now(timezone.utc).isoformat()
        payload = {
            "trends": [t.model_dump() for t in trends],
            "fetched_at": now_iso,
        }
        await set_cache(cache_key, payload, ttl_seconds=CACHE_TTL_SECONDS)

        # Fire webhook notification for fresh trends (non-blocking)
        if self._db and trends:
            try:
                from app.services.webhook_service import WebhookService
                webhook_svc = WebhookService(self._db)
                await webhook_svc.fire_event("trends_updated", {
                    "count": len(trends),
                    "category": category,
                    "top_topic": trends[0].topic if trends else "",
                })
            except Exception as e:
                logger.debug("Webhook fire_event failed (non-critical): %s", e)

        return TrendsResponse(
            trends=trends,
            cached=False,
            fetched_at=now_iso,
        )

    async def _fetch_all_trends(self, category: str, limit: int) -> list[TrendItem]:
        """
        Fetch from all sources, merge, semantically deduplicate, apply
        cross-source engagement boost, filter by category, and sort by
        composite score (engagement × 0.6 + recency × 0.4).
        """
        all_items: list[TrendItem] = []

        # Hacker News (date-sorted, last 48 h)
        try:
            hn_items = await self._hn.fetch_top_stories(limit=30)
            all_items.extend(hn_items)
        except Exception as e:
            logger.warning("HN fetch failed: %s", e)

        # RSS feeds (tech news + Google Trends + Reddit + ProductHunt + DEV.to)
        try:
            rss_items = await self._rss.fetch_all(limit=30)
            all_items.extend(rss_items)
        except Exception as e:
            logger.warning("RSS fetch failed: %s", e)

        if not all_items:
            return []

        # ── Semantic deduplication + cross-source boosting ─────────────────
        merged = _deduplicate_and_boost(all_items)

        # ── Category filter ────────────────────────────────────────────────
        if category and category in CATEGORY_KEYWORDS:
            keywords = CATEGORY_KEYWORDS[category]
            merged = [
                item for item in merged
                if any(
                    kw in item.topic.lower() or kw in item.suggested_angle.lower()
                    for kw in keywords
                )
            ]

        # ── Sort by composite score (engagement freshness blend) ───────────
        merged.sort(
            key=lambda x: x.engagement_potential * 0.6 + x.recency_score * 0.4,
            reverse=True,
        )

        return merged[:limit]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _word_set(text: str) -> frozenset[str]:
    """Tokenise text into meaningful lowercase words, stripping stop words."""
    words = re.findall(r"\b[a-z]{3,}\b", text.lower())
    return frozenset(w for w in words if w not in _STOP_WORDS)


def _jaccard(a: frozenset[str], b: frozenset[str]) -> float:
    union = a | b
    return len(a & b) / len(union) if union else 0.0


def _deduplicate_and_boost(items: list[TrendItem]) -> list[TrendItem]:
    """
    Group items whose titles share ≥ JACCARD_THRESHOLD word overlap.
    For each group: keep the highest-scoring representative and apply a
    cross-source engagement boost (+1 per additional confirming source, max +2).
    """
    word_sets = [_word_set(item.topic) for item in items]
    assigned = [False] * len(items)
    result: list[TrendItem] = []

    for i in range(len(items)):
        if assigned[i]:
            continue
        group_indices = [i]
        assigned[i] = True

        for j in range(i + 1, len(items)):
            if not assigned[j] and _jaccard(word_sets[i], word_sets[j]) >= JACCARD_THRESHOLD:
                group_indices.append(j)
                assigned[j] = True

        group = [items[k] for k in group_indices]
        best = max(group, key=lambda x: x.engagement_potential * 0.6 + x.recency_score * 0.4)

        unique_sources = len({g.source for g in group})
        boost = min(2, unique_sources - 1)  # +1 if 2 sources, +2 if 3+

        result.append(
            best.model_copy(update={"engagement_potential": min(10, best.engagement_potential + boost)})
        )

    return result
