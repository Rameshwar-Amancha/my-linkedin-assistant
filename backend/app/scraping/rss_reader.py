"""
rss_reader.py — RSS feed aggregator for trend discovery

Reads from public tech/business news feeds only.
Rate limited. All sources are publicly accessible.

Feed selection covers:
- Established tech news (TechCrunch, Ars Technica, Wired, VentureBeat, Techmeme)
- Real-time trending (Google Trends daily RSS, Reddit hot posts)
- Developer/startup community (DEV.to, ProductHunt)
"""

from __future__ import annotations

import asyncio
import calendar
import logging
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

import feedparser
import httpx

from app.models.schemas import TrendItem

logger = logging.getLogger(__name__)

REQUEST_TIMEOUT = 10.0
REQUEST_DELAY = 0.5  # seconds between feed fetches

FEEDS: list[dict] = [
    # ── Established tech news ──────────────────────────────────────────────
    {"url": "https://feeds.arstechnica.com/arstechnica/technology-lab", "source": "ars_technica"},
    {"url": "https://www.techmeme.com/feed.xml", "source": "techmeme"},
    {"url": "https://techcrunch.com/feed/", "source": "techcrunch"},
    {"url": "https://www.wired.com/feed/rss", "source": "wired"},
    {"url": "https://feeds.feedburner.com/venturebeat/SZYF", "source": "venturebeat"},
    # ── Real-time trending signals ─────────────────────────────────────────
    # Google Trends daily trending searches (US) — shows what people are searching RIGHT NOW
    {"url": "https://trends.google.com/trending/rss?geo=US", "source": "google_trends"},
    # Reddit hot posts — community-validated trending discussions
    {"url": "https://www.reddit.com/r/technology/hot/.rss?limit=20", "source": "reddit_tech"},
    {"url": "https://www.reddit.com/r/artificial/hot/.rss?limit=20", "source": "reddit_ai"},
    {"url": "https://www.reddit.com/r/programming/hot/.rss?limit=15", "source": "reddit_programming"},
    {"url": "https://www.reddit.com/r/startups/hot/.rss?limit=15", "source": "reddit_startups"},
    # ── Developer / startup community ─────────────────────────────────────
    {"url": "https://www.producthunt.com/feed", "source": "product_hunt"},
    {"url": "https://dev.to/feed", "source": "dev_to"},
]


class RSSReader:
    def __init__(self) -> None:
        self._client = httpx.AsyncClient(
            timeout=REQUEST_TIMEOUT,
            headers={"User-Agent": "LinkedIn-Assistant-Bot/1.0 (Educational tool)"},
        )

    async def fetch_all(self, limit: int = 20) -> list[TrendItem]:
        """Fetch from all configured RSS feeds."""
        all_items: list[TrendItem] = []

        for feed_config in FEEDS:
            try:
                items = await self._fetch_feed(feed_config["url"], feed_config["source"])
                all_items.extend(items)
                await asyncio.sleep(REQUEST_DELAY)
            except Exception as e:
                logger.warning("RSS feed fetch failed [%s]: %s", feed_config["source"], e)

        # Sort by composite score (engagement + recency) before truncating
        all_items.sort(
            key=lambda x: x.engagement_potential * 0.6 + x.recency_score * 0.4,
            reverse=True,
        )
        return all_items[:limit]

    async def _fetch_feed(self, url: str, source: str) -> list[TrendItem]:
        """Fetch and parse a single RSS feed."""
        try:
            response = await self._client.get(url)
            response.raise_for_status()
        except httpx.HTTPError as e:
            logger.debug("Failed to fetch %s: %s", url, e)
            return []

        # feedparser handles parsing synchronously
        feed = feedparser.parse(response.text)

        now_utc = datetime.now(timezone.utc)
        items: list[TrendItem] = []
        for entry in feed.entries[:15]:
            title = (entry.get("title") or "").strip()
            link = (entry.get("link") or "").strip()
            if not title or not link:
                continue

            published = _parse_published(entry)
            recency = _score_recency_from_iso(published, now_utc)
            base = _base_score_from_source(source)

            items.append(TrendItem(
                topic=title,
                source=source,
                url=link,
                engagement_potential=base,
                recency_score=recency,
                suggested_angle=_suggest_angle_for_rss(title, source),
                published_at=published,
            ))

        return items

    async def close(self) -> None:
        await self._client.aclose()


def _parse_published(entry: object) -> str:
    """Parse publication date from RSS entry, preferring feedparser's structured time."""
    # feedparser parses RFC-2822 / Atom dates into a time.struct_time
    for attr in ("published_parsed", "updated_parsed", "created_parsed"):
        parsed = getattr(entry, attr, None)
        if parsed:
            try:
                ts = calendar.timegm(parsed)  # struct_time (UTC) → POSIX timestamp
                return datetime.fromtimestamp(ts, tz=timezone.utc).isoformat()
            except Exception:
                pass

    # Fallback: try raw string fields
    for field in ("published", "updated", "created"):
        value = getattr(entry, field, None)
        if value:
            try:
                dt = parsedate_to_datetime(value)
                return dt.astimezone(timezone.utc).isoformat()
            except Exception:
                pass

    return datetime.now(timezone.utc).isoformat()


def _score_recency_from_iso(published_at: str, now_utc: datetime) -> int:
    """Score freshness 1-10 based on article age relative to now."""
    try:
        pub_dt = datetime.fromisoformat(published_at)
        age_hours = (now_utc - pub_dt).total_seconds() / 3600
    except Exception:
        return 5  # unknown age → neutral score

    if age_hours < 1:
        return 10
    elif age_hours < 3:
        return 9
    elif age_hours < 6:
        return 8
    elif age_hours < 12:
        return 7
    elif age_hours < 24:
        return 6
    elif age_hours < 48:
        return 4
    else:
        return 2


def _base_score_from_source(source: str) -> int:
    """Base engagement potential by source authority for LinkedIn audiences."""
    source_scores = {
        "techmeme": 8,          # aggregates what tech journalists are covering
        "google_trends": 8,     # direct signal of what the public is searching
        "techcrunch": 7,
        "venturebeat": 7,
        "reddit_ai": 7,         # AI practitioners discussing real topics
        "reddit_tech": 6,
        "reddit_programming": 6,
        "ars_technica": 6,
        "wired": 6,
        "product_hunt": 6,      # new products = fresh discussion fodder
        "dev_to": 5,
        "reddit_startups": 5,
    }
    return source_scores.get(source, 5)


def _suggest_angle_for_rss(title: str, source: str = "") -> str:
    """Generate a LinkedIn-specific angle suggestion from a news headline."""
    title_lower = title.lower()

    # Google Trends topics are bare search terms — angle differs
    if source == "google_trends":
        return "This is trending in search right now — share your expert take before the wave peaks"

    if any(kw in title_lower for kw in ["raise", "funding", "million", "billion", "series a", "series b", "seed round", "acqui"]):
        return "Break down what this signals for the market — write a '3 implications' post"
    elif any(kw in title_lower for kw in ["layoff", "cut", "restructur", "job loss", "fired", "rif"]):
        return "Share perspective on navigating uncertainty — resilience, skills to develop, or hiring strategy"
    elif any(kw in title_lower for kw in ["regulation", "law", "policy", "ban", "eu ai act", "gdpr"]):
        return "Translate the regulatory news into practical implications for companies or developers in your space"
    elif any(kw in title_lower for kw in ["ai", "gpt", "llm", "claude", "gemini", "copilot", "model", "agent"]):
        return "Share a specific workflow change you're making because of this — concrete beats theoretical"
    elif any(kw in title_lower for kw in ["open source", "github", "repo", "release", "v2", "v3"]):
        return "Explain why engineers should care and describe a use case from your own work"
    elif any(kw in title_lower for kw in ["survey", "report", "study", "research", "%", "stats", "data"]):
        return "Pick the most surprising stat and share what it means for your industry in under 200 words"
    elif any(kw in title_lower for kw in ["launch", "new", "introducing", "ships", "just released", "announce"]):
        return "Analyze whether this solves a real problem — add hands-on perspective if you've tried it"
    elif any(kw in title_lower for kw in ["ceo", "leader", "founder", "executive", "management", "culture"]):
        return "Share what this leadership moment teaches about decision-making or building teams"
    elif any(kw in title_lower for kw in ["remote", "hybrid", "return to office", "rto", "wfh"]):
        return "Share your honest stance with evidence — this topic drives high engagement on LinkedIn"
    else:
        return "Share your industry perspective on why this matters and who should pay attention"
