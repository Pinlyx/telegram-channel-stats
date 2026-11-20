import pytest

from tgstats.client import (
    BASE_URL,
    USER_AGENT,
    FetchError,
    InvalidUsernameError,
    PreviewDisabledError,
    RateLimitedError,
    Response,
    normalize_username,
)


@pytest.mark.parametrize(
    "raw",
    [
        "durov",
        "@durov",
        "t.me/durov",
        "https://t.me/durov",
        "https://t.me/s/durov",
        "https://t.me/s/durov?before=5",
        "durov/",
    ],
)
def test_normalize_username(raw):
    assert normalize_username(raw) == "durov"


@pytest.mark.parametrize("raw", ["", "a", "bad name", "9abcde", "https://example.com/x y"])
def test_invalid_usernames(raw):
    with pytest.raises(InvalidUsernameError):
        normalize_username(raw)


def test_preview_disabled_redirect(make_client):
    client, net = make_client({BASE_URL + "nopreview": Response(302, "", "https://t.me/nopreview")})
    with pytest.raises(PreviewDisabledError) as exc:
        client.get_page("nopreview")
    assert "preview disabled" in str(exc.value)
    assert len(net.calls) == 1


def test_sends_explicit_user_agent_and_timeout(make_client):
    client, net = make_client({BASE_URL + "durov": Response(200, "<html></html>")}, timeout=7)
    client.get_page("durov")
    assert net.calls[0][1] == USER_AGENT
    assert net.calls[0][2] == 7


def test_before_parameter(make_client):
    client, net = make_client({BASE_URL + "durov?before=545": Response(200, "x")})
    assert client.get_page("durov", before=545) == "x"


def test_min_one_second_between_requests(make_client, clock):
    client, _ = make_client(
        {BASE_URL + "durov": Response(200, "a"), BASE_URL + "durov?before=9": Response(200, "b")}
    )
    client.get_page("durov")
    client.get_page("durov", before=9)
    assert clock.sleeps and clock.sleeps[0] >= 1.0 - 1e-9


def test_interval_cannot_be_lowered_below_one_second(make_client):
    client, _ = make_client({}, min_interval=0.01)
    assert client.min_interval == 1.0


def test_backs_off_on_429_then_succeeds(make_client, clock):
    client, net = make_client(
        {BASE_URL + "durov": [Response(429, "", None, 7.0), Response(429), Response(200, "ok")]}
    )
    assert client.get_page("durov") == "ok"
    assert len(net.calls) == 3
    assert 7.0 in clock.sleeps  # honoured Retry-After
    assert any(s >= 10.0 for s in clock.sleeps)  # exponential fallback grew


def test_gives_up_after_repeated_429(make_client):
    client, net = make_client({BASE_URL + "durov": Response(429)}, max_retries=2)
    with pytest.raises(RateLimitedError):
        client.get_page("durov")
    assert len(net.calls) == 3


def test_unexpected_status(make_client):
    client, _ = make_client({BASE_URL + "durov": Response(500)})
    with pytest.raises(FetchError):
        client.get_page("durov")
