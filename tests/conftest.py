import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(__file__))

from tgstats.client import Client, Response  # noqa: E402

FIXTURES = os.path.join(os.path.dirname(__file__), "fixtures")


def fixture_html(name):
    with open(os.path.join(FIXTURES, name + ".html"), encoding="utf-8") as fh:
        return fh.read()


class FakeNet:
    """Offline transport: maps URL to a Response (or a list of Responses, used in order)."""

    def __init__(self, routes):
        self.routes = routes
        self.calls = []

    def __call__(self, url, user_agent, timeout):
        self.calls.append((url, user_agent, timeout))
        route = self.routes[url]
        if isinstance(route, list):
            return route.pop(0)
        return route


class Clock:
    """Fake clock: sleeping advances time, so tests never wait."""

    def __init__(self):
        self.now = 1000.0
        self.sleeps = []

    def time(self):
        return self.now

    def sleep(self, seconds):
        self.sleeps.append(seconds)
        self.now += seconds


@pytest.fixture
def clock():
    return Clock()


@pytest.fixture
def make_client(clock):
    def build(routes, **kw):
        net = FakeNet(routes)
        client = Client(transport=net, sleep=clock.sleep, clock=clock.time, **kw)
        return client, net

    return build


@pytest.fixture
def ok():
    return lambda name: Response(200, fixture_html(name))
