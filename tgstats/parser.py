"""Parse the public Telegram web preview (``https://t.me/s/<channel>``).

Only the standard library is used. The parser reads a handful of stable CSS
class names from the preview page; if Telegram renames them the parser returns
fewer fields rather than raising, and the fixtures in ``tests/`` show what the
expected markup looks like.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from html.parser import HTMLParser
from typing import Dict, List, Optional

_VOID = frozenset(
    "area base br col embed hr img input link meta param source track wbr".split()
)

_MULTIPLIERS = {"K": 1_000, "M": 1_000_000, "B": 1_000_000_000}
_SPACES = "   "
_COUNT_RE = re.compile(r"^\s*([0-9][0-9.,   ]*?)\s*([KMBkmb]?)\s*$")


def parse_count(text: Optional[str]) -> Optional[int]:
    """Turn Telegram's abbreviated counters into integers.

    ``"1.2K"`` -> 1200, ``"3.4M"`` -> 3400000, ``"1 234"`` -> 1234.
    Returns ``None`` when the text is not a count. Abbreviated values are
    rounded by Telegram, so K, M and B results are approximate.
    """
    if text is None:
        return None
    m = _COUNT_RE.match(text)
    if not m:
        return None
    number, suffix = m.group(1), m.group(2).upper()
    for ch in _SPACES:
        number = number.replace(ch, "")
    if suffix:
        if number.count(",") == 1 and "." not in number:
            number = number.replace(",", ".")  # decimal comma
        else:
            number = number.replace(",", "")
        try:
            return int(round(float(number) * _MULTIPLIERS[suffix]))
        except ValueError:
            return None
    digits = number.replace(",", "").replace(".", "")
    return int(digits) if digits.isdigit() else None


@dataclass
class ParsedPost:
    id: int
    url: str
    date: Optional[str] = None  # ISO 8601, as served in time[datetime]
    views: Optional[int] = None
    text: str = ""
    forwarded: bool = False


@dataclass
class ParsedPage:
    username: Optional[str] = None
    title: Optional[str] = None
    description: Optional[str] = None
    verified: bool = False
    counters: Dict[str, int] = field(default_factory=dict)  # counter_type -> int
    posts: List[ParsedPost] = field(default_factory=list)

    @property
    def subscribers(self) -> Optional[int]:
        for key in ("subscribers", "subscriber"):
            if key in self.counters:
                return self.counters[key]
        return None


class _PreviewParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.page = ParsedPage()
        # Each stack entry is (tag, markers opened by that element).
        self._stack: List[tuple] = []
        self._buf: Dict[str, List[str]] = {}
        self._msg: Optional[dict] = None
        self._counter: Optional[dict] = None

    def _active(self, name: str) -> bool:
        return any(name in marks for _, marks in self._stack)

    def _open(self, marks: List[str], name: str) -> None:
        marks.append(name)
        self._buf[name] = []

    def _close(self, name: str) -> str:
        return "".join(self._buf.pop(name, [])).strip()

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        classes = set((a.get("class") or "").split())
        if tag == "br":
            for name in ("text", "desc"):
                if name in self._buf:
                    self._buf[name].append("\n")
            return
        if tag in _VOID:
            return
        marks: List[str] = []

        if self._msg is None:
            if "tgme_channel_info_header_title" in classes:
                self._open(marks, "title")
            elif "tgme_channel_info_header_username" in classes:
                self._open(marks, "username")
            elif "verified-icon" in classes:
                self.page.verified = True
            elif "tgme_channel_info_description" in classes:
                self._open(marks, "desc")
            elif "tgme_channel_info_counter" in classes:
                marks.append("counter")
                self._counter = {}
            elif self._counter is not None and "counter_value" in classes:
                self._open(marks, "counter_value")
            elif self._counter is not None and "counter_type" in classes:
                self._open(marks, "counter_type")

        if "tgme_widget_message" in classes and a.get("data-post"):
            self._msg = {
                "ref": a["data-post"],
                "date": None,
                "views": None,
                "text": None,
                "forwarded": False,
            }
            marks.append("msg")
        elif self._msg is not None:
            if "tgme_widget_message_reply" in classes:
                marks.append("reply")
            elif "tgme_widget_message_forwarded_from" in classes:
                self._msg["forwarded"] = True
            elif "tgme_widget_message_views" in classes:
                self._open(marks, "views")
            elif (
                "tgme_widget_message_text" in classes
                and self._msg["text"] is None
                and not self._active("reply")
            ):
                self._open(marks, "text")
            if tag == "time" and a.get("datetime") and self._msg["date"] is None:
                self._msg["date"] = a["datetime"]
        self._stack.append((tag, marks))

    def handle_startendtag(self, tag, attrs):
        # "<br/>" has no end tag; other self-closing tags open nothing we track.
        if tag == "br":
            self.handle_starttag(tag, attrs)

    def handle_endtag(self, tag):
        if tag in _VOID:
            return
        idx = None
        for i in range(len(self._stack) - 1, -1, -1):
            if self._stack[i][0] == tag:
                idx = i
                break
        if idx is None:
            return
        closed = self._stack[idx:]
        del self._stack[idx:]
        for _, marks in reversed(closed):
            for name in marks:
                self._finish(name)

    def _finish(self, name: str) -> None:
        if name == "title":
            self.page.title = self._close("title") or None
        elif name == "username":
            self.page.username = self._close("username").lstrip("@") or None
        elif name == "desc":
            self.page.description = self._close("desc") or None
        elif name == "counter_value" and self._counter is not None:
            self._counter["value"] = self._close("counter_value")
        elif name == "counter_type" and self._counter is not None:
            self._counter["type"] = self._close("counter_type").lower()
        elif name == "counter":
            c = self._counter or {}
            value = parse_count(c.get("value"))
            if value is not None and c.get("type"):
                self.page.counters[c["type"]] = value
            self._counter = None
        elif name == "views" and self._msg is not None:
            self._msg["views"] = parse_count(self._close("views"))
        elif name == "text" and self._msg is not None:
            raw = self._close("text")
            self._msg["text"] = re.sub(r"[ \t]+", " ", raw)
        elif name == "msg" and self._msg is not None:
            self._emit_message()

    def _emit_message(self) -> None:
        m = self._msg or {}
        ref = m.get("ref", "")
        num = ref.rpartition("/")[2]
        if num.isdigit():
            self.page.posts.append(
                ParsedPost(
                    id=int(num),
                    url="https://t.me/%s" % ref,
                    date=m.get("date"),
                    views=m.get("views"),
                    text=m.get("text") or "",
                    forwarded=bool(m.get("forwarded")),
                )
            )
        self._msg = None

    def handle_data(self, data):
        for parts in self._buf.values():
            parts.append(data)


def parse_page(html: str) -> ParsedPage:
    """Parse one preview page into channel info and the posts on it."""
    parser = _PreviewParser()
    parser.feed(html)
    parser.close()
    return parser.page
