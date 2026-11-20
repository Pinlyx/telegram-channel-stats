import pytest

from conftest import fixture_html
from tgstats import parse_count, parse_page


@pytest.mark.parametrize(
    "text,expected",
    [
        ("1.2K", 1200),
        ("3.4M", 3400000),
        ("285K", 285000),
        ("9.94M", 9940000),
        ("27.9K", 27900),
        ("119", 119),
        ("1 234", 1234),
        ("1,234", 1234),
        ("2.5B", 2500000000),
        ("1,5K", 1500),
        ("  42 ", 42),
        ("", None),
        ("abc", None),
        (None, None),
    ],
)
def test_parse_count(text, expected):
    assert parse_count(text) == expected


def test_channel_info_from_fixture():
    page = parse_page(fixture_html("durov_page1"))
    assert page.username == "durov"
    assert page.title == "Pavel Durov"
    assert page.description == "Founder of Telegram."
    assert page.verified is True
    assert page.subscribers == 9940000
    assert page.counters["photos"] == 106


def test_posts_from_fixture():
    page = parse_page(fixture_html("durov_page1"))
    assert len(page.posts) == 20
    first = page.posts[0]
    assert first.id == 545
    assert first.url == "https://t.me/durov/545"
    assert first.date == "2026-08-30T09:10:19+00:00"
    assert first.views == 3800000
    assert first.text.startswith("A high-school student just made $20,000")
    assert all(p.views is not None and p.date for p in page.posts)


def test_forwarded_flag_and_small_channel():
    page = parse_page(fixture_html("golang_news"))
    assert page.subscribers == 119
    assert any(p.forwarded for p in page.posts)
    assert not page.verified


def test_garbage_html_does_not_raise():
    page = parse_page("<div><p>not a channel</div></span><br/>")
    assert page.posts == [] and page.subscribers is None
