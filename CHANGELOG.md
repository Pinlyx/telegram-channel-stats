# Changelog

## 0.1.0 - 2026-11-20

- First release.
- `get_channel` and `compare_to_benchmark` library API, `tgstats` command line tool.
- Reads the public Telegram web preview (`t.me/s/<channel>`): channel info, subscribers, posts, views and dates.
- Average and median views, reach, posts per day, top posts, JSON and CSV output, several channels per run.
- Benchmark against the Pinlyx Telegram Channel Reach 2026 study (CC BY 4.0), no comparison under 1,000 subscribers.
- Polite crawling: one request per second at most, explicit User-Agent, timeout, back-off on HTTP 429.
