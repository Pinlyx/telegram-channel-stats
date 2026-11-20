"""Public API: ``get_channel`` and ``compare_to_benchmark``."""

from __future__ import annotations

import statistics
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional

from .benchmark import Comparison, compare
from .client import Client, PreviewDisabledError, TgStatsError, normalize_username
from .parser import ParsedPost, parse_page

DEFAULT_POSTS = 50
MAX_PAGES = 60  # hard stop so a bad parse can never loop forever


@dataclass
class Post:
    id: int
    url: str
    date: Optional[str]
    views: Optional[int]
    text: str = ""
    forwarded: bool = False

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "url": self.url,
            "date": self.date,
            "views": self.views,
            "forwarded": self.forwarded,
            "text": self.text,
        }


def _parse_dt(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


@dataclass
class ChannelStats:
    username: str
    title: Optional[str]
    description: Optional[str]
    verified: bool
    subscribers: Optional[int]
    counters: Dict[str, int] = field(default_factory=dict)
    posts: List[Post] = field(default_factory=list)  # newest first
    fetched_at: str = ""

    @property
    def _views(self) -> List[int]:
        return [p.views for p in self.posts if p.views is not None]

    @property
    def avg_views(self) -> Optional[float]:
        v = self._views
        return sum(v) / len(v) if v else None

    @property
    def median_views(self) -> Optional[float]:
        v = self._views
        return float(statistics.median(v)) if v else None

    @property
    def reach(self) -> Optional[float]:
        """Average views per post divided by subscribers, as a fraction."""
        if not self.subscribers or self.avg_views is None:
            return None
        return self.avg_views / self.subscribers

    @property
    def posts_per_day(self) -> Optional[float]:
        dates = [d for d in (_parse_dt(p.date) for p in self.posts) if d is not None]
        if len(dates) < 2:
            return None
        span = (max(dates) - min(dates)).total_seconds() / 86400.0
        if span <= 0:
            return None
        return (len(dates) - 1) / span

    def top_posts(self, n: int = 5) -> List[Post]:
        ranked = [p for p in self.posts if p.views is not None]
        return sorted(ranked, key=lambda p: p.views, reverse=True)[:n]

    def to_dict(self, benchmark: bool = True) -> dict:
        out = {
            "username": self.username,
            "url": "https://t.me/s/" + self.username,
            "title": self.title,
            "description": self.description,
            "verified": self.verified,
            "subscribers": self.subscribers,
            "counters": dict(self.counters),
            "fetched_at": self.fetched_at,
            "posts_analyzed": len(self.posts),
            "avg_views": self.avg_views,
            "median_views": self.median_views,
            "reach": self.reach,
            "posts_per_day": self.posts_per_day,
            "top_posts": [p.to_dict() for p in self.top_posts(5)],
            "posts": [p.to_dict() for p in self.posts],
        }
        if benchmark:
            out["benchmark"] = compare_to_benchmark(self).to_dict()
        return out


def compare_to_benchmark(stats: ChannelStats) -> Comparison:
    """Compare ``stats.reach`` with the median reach of its subscriber band."""
    return compare(stats.subscribers, stats.reach)


def _to_post(p: ParsedPost) -> Post:
    return Post(id=p.id, url=p.url, date=p.date, views=p.views, text=p.text, forwarded=p.forwarded)


def get_channel(
    username: str,
    posts: int = DEFAULT_POSTS,
    client: Optional[Client] = None,
) -> ChannelStats:
    """Fetch a public channel's preview pages and compute its statistics.

    Raises ``PreviewDisabledError`` when the channel has no public web preview.
    """
    if posts < 1:
        raise ValueError("posts must be at least 1")
    name = normalize_username(username)
    client = client or Client()

    first = parse_page(client.get_page(name))
    if first.title is None and not first.posts and not first.counters:
        raise TgStatsError(
            "the page for @%s did not look like a channel preview (Telegram may have changed its HTML)" % name
        )
    collected: Dict[int, ParsedPost] = {p.id: p for p in first.posts}
    oldest = min(collected) if collected else None
    pages = 1
    while len(collected) < posts and oldest is not None and oldest > 1 and pages < MAX_PAGES:
        page = parse_page(client.get_page(name, before=oldest))
        pages += 1
        fresh = [p for p in page.posts if p.id not in collected]
        if not fresh:
            break
        for p in fresh:
            collected[p.id] = p
        oldest = min(collected)

    newest_first = sorted(collected.values(), key=lambda p: p.id, reverse=True)[:posts]
    return ChannelStats(
        username=(first.username or name),
        title=first.title,
        description=first.description,
        verified=first.verified,
        subscribers=first.subscribers,
        counters=dict(first.counters),
        posts=[_to_post(p) for p in newest_first],
        fetched_at=datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
    )


__all__ = [
    "ChannelStats",
    "Post",
    "PreviewDisabledError",
    "compare_to_benchmark",
    "get_channel",
]
