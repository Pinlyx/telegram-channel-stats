"""Compare a channel's reach with the Pinlyx Telegram Channel Reach 2026 study.

The study defines reach as average views per post divided by subscribers,
measured across the Pinlyx Data API catalogue of 3,205,346 public Telegram
channels. It reports the median reach per subscriber band for channels with at
least 1,000 subscribers; smaller channels are outside the study.

Data: CC BY 4.0, "Pinlyx, Telegram Channel Reach 2026",
https://pinlyx.com/research/telegram-channel-reach-2026
"""

from __future__ import annotations

import csv
import io
from dataclasses import asdict, dataclass
from typing import List, Optional

try:  # Python 3.9+
    from importlib.resources import files as _files
except ImportError:  # pragma: no cover
    _files = None

ATTRIBUTION = "Pinlyx, Telegram Channel Reach 2026"
SOURCE_URL = "https://pinlyx.com/research/telegram-channel-reach-2026"
LICENSE = "CC BY 4.0"
DATA_NAME = "telegram-channel-reach-2026.csv"
MIN_SUBSCRIBERS = 1000


@dataclass(frozen=True)
class Band:
    key: str
    min_subscribers: int
    max_subscribers: Optional[int]  # exclusive; None means open ended
    median_reach: float  # fraction, 0.31 means 31%
    sample_size: int
    basis: str  # "sample" or "all_channels"

    def contains(self, subscribers: int) -> bool:
        if subscribers < self.min_subscribers:
            return False
        return self.max_subscribers is None or subscribers < self.max_subscribers


def parse_bands(csv_text: str) -> List[Band]:
    """Read the ``median_reach`` rows of the study CSV, sorted by size."""
    bands = []
    for row in csv.DictReader(io.StringIO(csv_text)):
        if row.get("table") != "median_reach":
            continue
        bands.append(
            Band(
                key=row["key"],
                min_subscribers=int(row["min_subscribers"]),
                max_subscribers=int(row["max_subscribers"]) if row.get("max_subscribers") else None,
                median_reach=float(row["value"]),
                sample_size=int(row["sample_size"]),
                basis=row.get("basis", ""),
            )
        )
    return sorted(bands, key=lambda b: b.min_subscribers)


def load_bands() -> List[Band]:
    """Load the bundled copy of the study data."""
    if _files is not None:
        text = _files("tgstats").joinpath("data", DATA_NAME).read_text(encoding="utf-8")
    else:  # pragma: no cover
        import os

        path = os.path.join(os.path.dirname(__file__), "data", DATA_NAME)
        with open(path, encoding="utf-8") as fh:
            text = fh.read()
    return parse_bands(text)


def pick_band(subscribers: int, bands: Optional[List[Band]] = None) -> Optional[Band]:
    """Band containing ``subscribers``, or ``None`` below the 1,000 floor."""
    for band in bands if bands is not None else load_bands():
        if band.contains(subscribers):
            return band
    return None


@dataclass
class Comparison:
    available: bool
    reason: Optional[str] = None  # set when available is False
    band: Optional[str] = None
    band_median_reach: Optional[float] = None
    band_sample_size: Optional[int] = None
    band_basis: Optional[str] = None
    channel_reach: Optional[float] = None
    position: Optional[str] = None  # "above", "below" or "at" the band median
    ratio: Optional[float] = None  # channel reach / band median
    difference_points: Optional[float] = None  # percentage points, channel minus band
    attribution: str = ATTRIBUTION
    source_url: str = SOURCE_URL
    license: str = LICENSE

    def to_dict(self) -> dict:
        return asdict(self)


def compare(
    subscribers: Optional[int],
    reach: Optional[float],
    bands: Optional[List[Band]] = None,
) -> Comparison:
    """Compare a reach fraction with the median of its subscriber band."""
    if subscribers is None:
        return Comparison(False, "the subscriber count could not be read from the preview page")
    if reach is None:
        return Comparison(False, "no post with a view count was found, so reach cannot be computed")
    band = pick_band(subscribers, bands)
    if band is None:
        return Comparison(
            False,
            "the study covers channels with at least %s subscribers; this channel has %s, "
            "so no comparison is given" % (format(MIN_SUBSCRIBERS, ","), format(subscribers, ",")),
        )
    ratio = reach / band.median_reach if band.median_reach else None
    if abs(reach - band.median_reach) < 0.0005:
        position = "at"
    else:
        position = "above" if reach > band.median_reach else "below"
    return Comparison(
        available=True,
        band=band.key,
        band_median_reach=band.median_reach,
        band_sample_size=band.sample_size,
        band_basis=band.basis,
        channel_reach=reach,
        position=position,
        ratio=ratio,
        difference_points=(reach - band.median_reach) * 100.0,
    )
