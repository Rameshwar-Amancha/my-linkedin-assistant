"""
text_utils.py — Text processing utilities for post analysis and formatting
"""

from __future__ import annotations

import re
import unicodedata


def word_count(text: str) -> int:
    """Count words in text."""
    return len(text.split())


def char_count(text: str) -> int:
    """Count non-whitespace characters."""
    return len(text.replace(" ", "").replace("\n", ""))


def extract_hashtags(text: str) -> list[str]:
    """Extract all hashtags from text."""
    return list(dict.fromkeys(re.findall(r"#\w+", text)))


def extract_mentions(text: str) -> list[str]:
    """Extract all @mentions from text."""
    return re.findall(r"@[\w.]+", text)


def truncate(text: str, max_chars: int = 200, suffix: str = "...") -> str:
    """Truncate text to max_chars, breaking at word boundary."""
    if len(text) <= max_chars:
        return text
    truncated = text[:max_chars - len(suffix)].rsplit(" ", 1)[0]
    return truncated + suffix


def normalize_whitespace(text: str) -> str:
    """Collapse multiple spaces/newlines into single spaces."""
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def remove_html(text: str) -> str:
    """Strip HTML tags from text."""
    return re.sub(r"<[^>]+>", "", text)


def slug(text: str) -> str:
    """Convert text to URL-friendly slug."""
    text = unicodedata.normalize("NFD", text)
    text = text.encode("ascii", "ignore").decode("ascii")
    text = re.sub(r"[^\w\s-]", "", text.lower())
    return re.sub(r"[-\s]+", "-", text).strip("-")


def count_paragraphs(text: str) -> int:
    """Count non-empty paragraphs (separated by blank lines)."""
    paragraphs = re.split(r"\n\s*\n", text)
    return len([p for p in paragraphs if p.strip()])


def avg_sentence_length(text: str) -> float:
    """Average number of words per sentence."""
    sentences = re.split(r"[.!?]+", text)
    sentences = [s.strip() for s in sentences if s.strip()]
    if not sentences:
        return 0.0
    total_words = sum(len(s.split()) for s in sentences)
    return total_words / len(sentences)


def is_likely_ai_generated(text: str) -> bool:
    """
    Heuristic check for common AI-generated LinkedIn patterns.
    Returns True if multiple red flags are found.
    """
    red_flags = [
        r"\bdelve\b",
        r"\bfacilitate\b.*\bsynergy\b",
        r"\bin today's (fast-)?paced world\b",
        r"\bnow more than ever\b",
        r"\bthe bottom line is\b",
        r"\bas an ai\b",
        r"absolutely[,!]",
        r"^(great|excellent) (post|insight|share)",
        r"i'm thrilled to (announce|share)",
        r"i'm excited to (announce|share)",
    ]
    text_lower = text.lower()
    matches = sum(1 for pattern in red_flags if re.search(pattern, text_lower))
    return matches >= 2
