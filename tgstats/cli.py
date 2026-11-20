"""Command line interface: ``tgstats <channel> [<channel> ...]``."""

from __future__ import annotations

import argparse
import csv
import json
import sys
from typing import List, Optional

from . import __version__
from .benchmark import ATTRIBUTION, SOURCE_URL
from .client import MIN_INTERVAL, Client, TgStatsError
from .core import DEFAULT_POSTS, ChannelStats, compare_to_benchmark, get_channel


def _pct(x: Optional[float]) -> str:
    return "n/a" if x is None else "%.1f%%" % (x * 100.0)


def _num(x: Optional[float]) -> str:
    return "n/a" if x is None else format(int(round(x)), ",")


def _excerpt(text: str, width: int = 60) -> str:
    one = " ".join(text.split())
    return one if len(one) <= width else one[: width - 3] + "..."


def format_report(stats: ChannelStats) -> str:
    lines: List[str] = []
    name = "%s (@%s)" % (stats.title or stats.username, stats.username)
    if stats.verified:
        name += " [verified]"
    lines.append(name)
    if stats.description:
        lines.append("  " + _excerpt(stats.description, 100))
    lines.append("  Subscribers:       %s" % _num(stats.subscribers))
    dates = [p.date for p in stats.posts if p.date]
    span = "  (%s to %s)" % (min(dates)[:10], max(dates)[:10]) if dates else ""
    lines.append("  Posts analysed:    %d%s" % (len(stats.posts), span))
    lines.append("  Views per post:    avg %s, median %s" % (_num(stats.avg_views), _num(stats.median_views)))
    lines.append("  Reach:             %s (average views / subscribers)" % _pct(stats.reach))
    ppd = stats.posts_per_day
    lines.append("  Posting frequency: %s" % ("n/a" if ppd is None else "%.2f posts/day" % ppd))
    top = stats.top_posts(5)
    if top:
        lines.append("  Top %d posts by views:" % len(top))
        for p in top:
            lines.append("    %10s  %s  %s" % (format(p.views, ","), p.url, _excerpt(p.text, 40)))
    cmp = compare_to_benchmark(stats)
    if cmp.available:
        lines.append(
            "  Benchmark:         median reach in its size band (%s subscribers) is %s, "
            "this channel %s: %s (%.1fx the band median)"
            % (cmp.band, _pct(cmp.band_median_reach), _pct(cmp.channel_reach), cmp.position, cmp.ratio or 0.0)
        )
        lines.append("                     Source: %s, %s" % (ATTRIBUTION, SOURCE_URL))
    else:
        lines.append("  Benchmark:         not available: %s" % cmp.reason)
    return "\n".join(lines)


def _write_csv(all_stats: List[ChannelStats], out) -> None:
    w = csv.writer(out, lineterminator="\n")
    w.writerow(["channel", "post_id", "url", "date", "views", "forwarded", "text"])
    for s in all_stats:
        for p in s.posts:
            w.writerow([s.username, p.id, p.url, p.date or "", "" if p.views is None else p.views, int(p.forwarded), p.text])


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="tgstats",
        description="Statistics for public Telegram channels from the public web preview. No API key, no login.",
    )
    p.add_argument("channels", nargs="+", metavar="channel", help="channel username, @name or t.me link")
    p.add_argument("--posts", type=int, default=DEFAULT_POSTS, metavar="N", help="how many recent posts to read (default %d)" % DEFAULT_POSTS)
    p.add_argument("--json", action="store_true", help="print JSON (an object for one channel, a list for several)")
    p.add_argument("--csv", nargs="?", const="-", default=None, metavar="FILE", help="write the post list as CSV to FILE, or to stdout when no FILE is given")
    p.add_argument("--delay", type=float, default=MIN_INTERVAL, metavar="SEC", help="seconds between requests (minimum and default %.0f)" % MIN_INTERVAL)
    p.add_argument("--timeout", type=float, default=20.0, metavar="SEC", help="request timeout (default 20)")
    p.add_argument("--version", action="version", version="tgstats " + __version__)
    return p


def main(argv: Optional[List[str]] = None, client: Optional[Client] = None) -> int:
    args = build_parser().parse_args(argv)
    if args.posts < 1:
        print("tgstats: --posts must be at least 1", file=sys.stderr)
        return 2
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass
    client = client or Client(min_interval=args.delay, timeout=args.timeout)

    results: List[ChannelStats] = []
    failed = 0
    for name in args.channels:
        try:
            results.append(get_channel(name, posts=args.posts, client=client))
        except TgStatsError as err:
            failed += 1
            print("tgstats: %s: %s" % (name, err), file=sys.stderr)

    csv_to_stdout = args.csv == "-"
    if args.csv and not csv_to_stdout:
        with open(args.csv, "w", encoding="utf-8", newline="") as fh:
            _write_csv(results, fh)
    elif csv_to_stdout:
        _write_csv(results, sys.stdout)

    if args.json and not csv_to_stdout:
        payload = [s.to_dict() for s in results]
        print(json.dumps(payload[0] if len(payload) == 1 and len(args.channels) == 1 else payload, indent=2, ensure_ascii=False))
    elif not csv_to_stdout:
        print("\n\n".join(format_report(s) for s in results))

    return 1 if failed else 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
