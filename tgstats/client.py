"""Polite HTTP client for the public Telegram web preview."""

from __future__ import annotations

import re
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Callable, Optional

USER_AGENT = "telegram-channel-stats/0.1 (+https://github.com/Pinlyx/telegram-channel-stats)"
BASE_URL = "https://t.me/s/"
MIN_INTERVAL = 1.0  # seconds between requests; lower values are clamped up

_USERNAME_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_]{3,31}$")


class TgStatsError(Exception):
    """Base class for every error raised by this package."""


class InvalidUsernameError(TgStatsError):
    """The argument is not a usable public channel username."""


class PreviewDisabledError(TgStatsError):
    """t.me/s/<name> redirected to t.me/<name>: no public web preview."""


class RateLimitedError(TgStatsError):
    """Telegram kept answering 429 after the allowed retries."""


class FetchError(TgStatsError):
    """Network failure or an unexpected HTTP status."""


def normalize_username(value: str) -> str:
    """Accept ``durov``, ``@durov``, ``t.me/durov``, ``https://t.me/s/durov``."""
    v = (value or "").strip()
    v = re.sub(r"^(?:https?://)?(?:www\.)?t\.me/", "", v, flags=re.I)
    v = re.sub(r"^s/", "", v)
    v = v.split("?")[0].split("#")[0].strip("/").split("/")[0]
    v = v.lstrip("@")
    if not _USERNAME_RE.match(v):
        raise InvalidUsernameError("not a valid public channel username: %r" % value)
    return v


@dataclass
class Response:
    status: int
    body: str = ""
    location: Optional[str] = None
    retry_after: Optional[float] = None


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):  # noqa: D401
        return None


def _urllib_transport(url: str, user_agent: str, timeout: float) -> Response:
    opener = urllib.request.build_opener(_NoRedirect)
    req = urllib.request.Request(
        url, headers={"User-Agent": user_agent, "Accept": "text/html"}
    )
    try:
        with opener.open(req, timeout=timeout) as resp:
            body = resp.read().decode("utf-8", errors="replace")
            return Response(resp.status, body)
    except urllib.error.HTTPError as err:
        retry_after = None
        raw = err.headers.get("Retry-After") if err.headers else None
        if raw and raw.strip().isdigit():
            retry_after = float(raw.strip())
        return Response(err.code, "", err.headers.get("Location") if err.headers else None, retry_after)
    except (urllib.error.URLError, OSError, TimeoutError) as err:
        raise FetchError("network error for %s: %s" % (url, err)) from err


class Client:
    """Fetches preview pages, one request at a time, at most one per second.

    ``transport`` and ``sleep``/``clock`` can be replaced, which is how the
    tests run without a network.
    """

    def __init__(
        self,
        min_interval: float = MIN_INTERVAL,
        timeout: float = 20.0,
        user_agent: str = USER_AGENT,
        max_retries: int = 3,
        transport: Optional[Callable[[str, str, float], Response]] = None,
        sleep: Callable[[float], None] = time.sleep,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self.min_interval = max(float(min_interval), MIN_INTERVAL)
        self.timeout = timeout
        self.user_agent = user_agent
        self.max_retries = max_retries
        self._transport = transport or _urllib_transport
        self._sleep = sleep
        self._clock = clock
        self._last: Optional[float] = None

    def _wait_turn(self) -> None:
        if self._last is not None:
            gap = self.min_interval - (self._clock() - self._last)
            if gap > 0:
                self._sleep(gap)
        self._last = self._clock()

    def get_page(self, username: str, before: Optional[int] = None) -> str:
        """Return the HTML of one preview page (newest posts, or older than ``before``)."""
        name = normalize_username(username)
        url = BASE_URL + name
        if before is not None:
            url += "?before=%d" % before
        for attempt in range(self.max_retries + 1):
            self._wait_turn()
            resp = self._transport(url, self.user_agent, self.timeout)
            if resp.status == 200:
                return resp.body
            if resp.status in (301, 302, 303, 307, 308):
                raise PreviewDisabledError(
                    "@%s has no public web preview (preview disabled, or the channel "
                    "does not exist or is private); t.me/s/%s redirected to %s"
                    % (name, name, resp.location or "t.me/" + name)
                )
            if resp.status == 429:
                if attempt >= self.max_retries:
                    break
                backoff = resp.retry_after if resp.retry_after else 5.0 * (2 ** attempt)
                self._sleep(min(backoff, 120.0))
                self._last = self._clock()
                continue
            raise FetchError("unexpected HTTP %d for %s" % (resp.status, url))
        raise RateLimitedError("Telegram answered 429 too many times for %s; try again later" % url)
