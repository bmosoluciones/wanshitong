# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 BMO Soluciones, S.A.

"""Markdown rendering utilities."""

from __future__ import annotations

import bleach
import markdown as _md

ALLOWED_TAGS = list(bleach.sanitizer.ALLOWED_TAGS) + [
    "p",
    "pre",
    "code",
    "h1",
    "h2",
    "h3",
    "h4",
    "h5",
    "h6",
    "blockquote",
    "ul",
    "ol",
    "li",
    "hr",
    "br",
    "strong",
    "em",
    "a",
    "img",
    "table",
    "thead",
    "tbody",
    "tr",
    "th",
    "td",
    "del",
    "ins",
    "sup",
    "sub",
]

ALLOWED_ATTRIBUTES = dict(bleach.sanitizer.ALLOWED_ATTRIBUTES)
ALLOWED_ATTRIBUTES["a"] = ["href", "title", "target"]
ALLOWED_ATTRIBUTES["img"] = ["src", "alt", "title", "width", "height"]
ALLOWED_ATTRIBUTES["code"] = ["class"]
ALLOWED_ATTRIBUTES["pre"] = ["class"]
ALLOWED_ATTRIBUTES["th"] = ["align"]
ALLOWED_ATTRIBUTES["td"] = ["align"]


def render_markdown(text: str) -> str:
    """Convert Markdown text to sanitized HTML."""
    extensions = ["fenced_code", "tables", "nl2br", "sane_lists"]
    html = _md.markdown(text or "", extensions=extensions)
    return bleach.clean(
        html, tags=ALLOWED_TAGS, attributes=ALLOWED_ATTRIBUTES, strip=True
    )
