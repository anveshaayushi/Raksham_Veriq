"""Chat text is untrusted. Everything shown from it goes through these helpers."""

from __future__ import annotations

import html
import re

_MD_SPECIAL = re.compile(r"([\\`*_{}\[\]()#+\-.!|>~<$&:])")


_URL = re.compile(r"\b(h)(ttps?)(://)", re.I)
_WWW = re.compile(r"\bwww\.", re.I)


def defang(text: str) -> str:
    """Make URLs non-clickable (hxxp://, www[.]) so chat links can't be auto-linked by a Markdown renderer."""
    return _WWW.sub("www[.]", _URL.sub(lambda m: "hxxp" + m.group(2)[3:] + m.group(3), str(text)))


def md_escape(text: str) -> str:
    """Escape Markdown so chat text renders literally in st.markdown (no links, images, HTML or formatting).
    URLs are defanged too, because Streamlit auto-links bare URLs even when ':' is escaped."""
    return _MD_SPECIAL.sub(r"\\\1", defang(text)).replace("\n", "  \n")


def code(text: str) -> str:
    """Inline code span for ids and labels: backticks removed, no Markdown escaping needed inside."""
    return "`" + str(text).replace("`", "'").replace("\n", " ") + "`"


def html_escape(text: str) -> str:
    return html.escape(str(text), quote=True)


_PHONE = re.compile(r"(?<!\d)(?:\+?91[- ]?)?[6-9]\d{9}(?!\d)")
_DIGITS = re.compile(r"(?<!\d)\d{9,18}(?!\d)")


def redact(text: str) -> str:
    """Account-like digit runs and Indian mobile numbers -> last four digits only."""
    text = _PHONE.sub(lambda m: "XXXXXX" + m.group(0)[-4:], str(text))
    return _DIGITS.sub(lambda m: "XX" + m.group(0)[-4:], text)
