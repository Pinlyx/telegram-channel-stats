"""Statistics for public Telegram channels, from the public web preview.

No API key, no login. See the README for what this can and cannot measure.
"""

from .benchmark import ATTRIBUTION, SOURCE_URL, Band, Comparison, load_bands, pick_band
from .client import (
    Client,
    FetchError,
    InvalidUsernameError,
    PreviewDisabledError,
    RateLimitedError,
    TgStatsError,
    normalize_username,
)
from .core import ChannelStats, Post, compare_to_benchmark, get_channel
from .parser import parse_count, parse_page

__version__ = "0.1.0"

__all__ = [
    "ATTRIBUTION",
    "SOURCE_URL",
    "Band",
    "ChannelStats",
    "Client",
    "Comparison",
    "FetchError",
    "InvalidUsernameError",
    "Post",
    "PreviewDisabledError",
    "RateLimitedError",
    "TgStatsError",
    "compare_to_benchmark",
    "get_channel",
    "load_bands",
    "normalize_username",
    "parse_count",
    "parse_page",
    "pick_band",
    "__version__",
]
