# telegram-channel-stats

Subscribers, views, reach and posting frequency for any public Telegram channel, plus a benchmark against your size class. No API key, no login, no dependencies.

## Why

Telegram's official API needs an account, a phone number and an app registration, and the paid scraping and analytics services put the same public numbers behind a subscription. But every public channel with a web preview already shows its subscriber count and the view counter of each post at `https://t.me/s/<channel>`. This tool reads that page politely, does the arithmetic you would otherwise do by hand (average and median views, reach, posts per day, top posts) and tells you how the channel compares with channels of its size.

Python 3.9+, standard library only.

## Install

The package is not on PyPI yet. Install from GitHub:

```bash
pip install git+https://github.com/Pinlyx/telegram-channel-stats
```

## Quick start

```bash
tgstats durov
tgstats durov tgbeta --posts 100
tgstats tgbeta --json
tgstats tgbeta --csv posts.csv
```

Real output (20 November 2026):

```
Pavel Durov (@durov) [verified]
  Founder of Telegram.
  Subscribers:       9,940,000
  Posts analysed:    50  (2026-05-16 to 2026-11-19)
  Views per post:    avg 6,243,800, median 4,800,000
  Reach:             62.8% (average views / subscribers)
  Posting frequency: 0.26 posts/day
  Top 5 posts by views:
    24,500,000  https://t.me/durov/527  🏆 Telegram is launching a $200,000 co...
    23,300,000  https://t.me/durov/526  🖥 Don't be surprised if you see table...
    19,100,000  https://t.me/durov/528  ⛔️ The UK government wants to ban soc...
    16,600,000  https://t.me/durov/525  🔄 Telegram’s new update is out. Lots ...
    15,000,000  https://t.me/durov/524  ⌚️ Telegram is now on Wear OS. Owners...
  Benchmark:         median reach in its size band (500k+ subscribers) is 3.3%, this channel 62.8%: above (19.3x the band median)
                     Source: Pinlyx, Telegram Channel Reach 2026, https://pinlyx.com/research/telegram-channel-reach-2026
```

That reach is far above the band median because this channel's posts are forwarded and previewed everywhere; see Limits.

### As a library

```python
from tgstats import get_channel, compare_to_benchmark

stats = get_channel("tgbeta", posts=50)
print(stats.subscribers, stats.avg_views, stats.median_views, stats.reach)
print(stats.posts_per_day)
for post in stats.top_posts(5):
    print(post.views, post.url)

cmp = compare_to_benchmark(stats)
if cmp.available:
    print(cmp.band, cmp.band_median_reach, cmp.position, cmp.ratio)
else:
    print(cmp.reason)

data = stats.to_dict()  # JSON-serialisable, includes the benchmark
```

`get_channel(username, posts=50, client=None) -> ChannelStats` accepts `durov`, `@durov` or a `t.me` link. `ChannelStats` is a dataclass with `username`, `title`, `description`, `verified`, `subscribers`, `counters`, `posts` (newest first) and the derived `avg_views`, `median_views`, `reach` (a fraction, 0.31 means 31%), `posts_per_day` and `top_posts(n)`.

Errors derive from `tgstats.TgStatsError`. `PreviewDisabledError` means the channel has no public web preview; `RateLimitedError` means Telegram kept answering 429; `FetchError` covers network failures and other HTTP statuses.

## CLI reference

```
tgstats CHANNEL [CHANNEL ...] [--posts N] [--json] [--csv [FILE]] [--delay SEC] [--timeout SEC]
```

| Option | Meaning |
| --- | --- |
| `--posts N` | How many recent posts to read, default 50. Each preview page holds about 20. |
| `--json` | JSON instead of the text report: an object for one channel, a list for several. |
| `--csv [FILE]` | The post list as CSV (channel, post_id, url, date, views, forwarded, text) to FILE, or to stdout without FILE. |
| `--delay SEC` | Seconds between requests. The default and the minimum is 1. |
| `--timeout SEC` | Request timeout, default 20. |

The exit code is 1 when any channel failed, with the reason on stderr; the other channels are still reported.

## The benchmark

The package ships the median reach per subscriber band from the [Pinlyx Telegram Channel Reach 2026](https://pinlyx.com/research/telegram-channel-reach-2026) study, which measured the Pinlyx Data API catalogue of 3,205,346 public Telegram channels. In that study reach is average views per post divided by subscribers, and the medians are:

| Subscribers | Median reach |
| --- | --- |
| 1,000 to 5,000 | 31.4% |
| 5,000 to 20,000 | 15.8% |
| 20,000 to 100,000 | 9.1% |
| 100,000 to 500,000 | 6.0% |
| 500,000 and up | 3.3% |

The study does not cover channels under 1,000 subscribers, so for those the tool gives no comparison and says why. The three smaller bands are computed over samples; the two largest cover every channel in them. The CSV is bundled in `tgstats/data/`.

## How it works and its limits

- The tool downloads `https://t.me/s/<channel>` and, for more posts, follows `?before=<post_id>`. It reads the channel header (title, description, counters) and each post's views, date and text from the HTML.
- It is polite by construction: one request at a time, at least one second apart, an explicit User-Agent (`telegram-channel-stats/0.1 (+https://github.com/Pinlyx/telegram-channel-stats)`), a timeout, and exponential back-off on HTTP 429.
- Only channels with a public web preview work. When a channel has the preview disabled, `t.me/s/<name>` redirects to `t.me/<name>` and the tool reports "preview disabled". A channel that does not exist or is private looks the same from outside. Private channels, groups and anything behind a login are out of scope.
- Telegram's view counter counts every view of a post, including views through forwards and web previews by people who are not subscribers. Reach computed here can therefore overstate the share of subscribers who saw a post, most of all on channels whose posts travel, and values above 100% are possible. In the other direction, subscriber counts inflated by inactive or bought accounts pull reach down.
- Counts such as `1.2K` and `3.4M` are rounded by Telegram, so subscribers and views are approximate above 1,000. The newest posts have not finished collecting views, which pulls a short window down a little.
- This is an observation of public numbers, not a Telegram audit: nothing here shows who saw a post or whether views are real.
- Telegram can change its HTML at any time. The parser reads a small set of class names and degrades to missing fields rather than guessing; if it breaks, the tests in `tests/` and the saved pages in `tests/fixtures/` show what the markup used to look like. Please open an issue with the channel name.

## Contributing

Issues and pull requests are welcome; see [CONTRIBUTING.md](CONTRIBUTING.md). Tests run offline against saved pages:

```bash
pip install -e ".[test]"
python -m pytest
```

## License

The code is MIT, see [LICENSE](LICENSE). The bundled study data (`tgstats/data/telegram-channel-reach-2026.csv`) is CC BY 4.0, see [LICENSE-DATA](LICENSE-DATA); attribution: "Pinlyx, Telegram Channel Reach 2026", https://pinlyx.com/research/telegram-channel-reach-2026.

Built and maintained by [Pinlyx](https://pinlyx.com/?utm_source=github&utm_medium=readme&utm_campaign=telegram-channel-stats), a Telegram CRM and inbox for teams that run conversations on Telegram.
