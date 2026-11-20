import json

import pytest

from tgstats import PreviewDisabledError, TgStatsError, compare_to_benchmark, get_channel
from tgstats.client import BASE_URL, Response
from tgstats.core import ChannelStats, Post


def _durov_routes(ok):
    return {
        BASE_URL + "durov": ok("durov_page1"),
        BASE_URL + "durov?before=545": ok("durov_page2"),
    }


def test_get_channel_paginates_and_trims(make_client, ok):
    client, net = make_client(_durov_routes(ok))
    stats = get_channel("durov", posts=30, client=client)
    assert len(stats.posts) == 30
    assert len(net.calls) == 2
    ids = [p.id for p in stats.posts]
    assert ids == sorted(ids, reverse=True)  # newest first
    assert stats.posts[0].id == 566
    assert stats.subscribers == 9940000 and stats.title == "Pavel Durov"


def test_single_page_is_enough_when_posts_small(make_client, ok):
    client, net = make_client(_durov_routes(ok))
    stats = get_channel("@durov", posts=10, client=client)
    assert len(stats.posts) == 10 and len(net.calls) == 1


def test_stats_math_and_top_posts(make_client, ok):
    client, _ = make_client({BASE_URL + "golang_news": ok("golang_news")})
    stats = get_channel("golang_news", posts=20, client=client)
    views = [p.views for p in stats.posts]
    assert stats.avg_views == pytest.approx(sum(views) / len(views))
    assert stats.reach == pytest.approx(stats.avg_views / 119)
    top = stats.top_posts(5)
    assert len(top) == 5 and top[0].views == max(views)
    assert [p.views for p in top] == sorted((p.views for p in top), reverse=True)
    assert stats.posts_per_day and stats.posts_per_day > 0


def test_posts_per_day_exact():
    posts = [
        Post(3, "u3", "2026-01-03T00:00:00+00:00", 30),
        Post(2, "u2", "2026-01-02T00:00:00+00:00", 20),
        Post(1, "u1", "2026-01-01T00:00:00+00:00", 10),
    ]
    s = ChannelStats("x", None, None, False, 1000, posts=posts)
    assert s.posts_per_day == pytest.approx(1.0)
    assert s.avg_views == 20 and s.median_views == 20 and s.reach == pytest.approx(0.02)


def test_benchmark_for_mid_size_channel(make_client, ok):
    client, _ = make_client({BASE_URL + "tgbeta": ok("tgbeta")})
    cmp = compare_to_benchmark(get_channel("tgbeta", posts=20, client=client))
    assert cmp.available and cmp.band == "20k-100k"
    assert cmp.position in ("above", "below")


def test_under_1000_subscribers_has_no_benchmark(make_client, ok):
    client, _ = make_client({BASE_URL + "golang_news": ok("golang_news")})
    cmp = compare_to_benchmark(get_channel("golang_news", posts=20, client=client))
    assert not cmp.available and "1,000" in cmp.reason


def test_preview_disabled_propagates(make_client):
    client, _ = make_client({BASE_URL + "closedchan": Response(302, "", "https://t.me/closedchan")})
    with pytest.raises(PreviewDisabledError):
        get_channel("closedchan", client=client)


def test_non_channel_page_is_reported(make_client):
    client, _ = make_client({BASE_URL + "weirdpage": Response(200, "<html><body>hello</body></html>")})
    with pytest.raises(TgStatsError, match="did not look like a channel preview"):
        get_channel("weirdpage", client=client)


def test_to_dict_is_json_serialisable(make_client, ok):
    client, _ = make_client({BASE_URL + "tgbeta": ok("tgbeta")})
    d = get_channel("tgbeta", posts=5, client=client).to_dict()
    json.dumps(d)
    assert d["posts_analyzed"] == 5 and d["benchmark"]["available"] is True
    assert len(d["top_posts"]) == 5


def test_posts_must_be_positive():
    with pytest.raises(ValueError):
        get_channel("durov", posts=0)
