# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 BMO Soluciones, S.A.

from __future__ import annotations

import re
from collections.abc import Iterable

BOOTSTRAP_ICON_NAMES = [
    "airplane",
    "alarm",
    "archive",
    "backpack",
    "backspace",
    "bag",
    "bag-check",
    "bag-heart",
    "bank",
    "bar-chart-line",
    "book",
    "bookmark",
    "bookmarks",
    "braces",
    "bug",
    "building",
    "cake",
    "calendar",
    "camera",
    "car-front",
    "cart",
    "chat",
    "clipboard",
    "cloud",
    "database",
    "diagram-3",
    "envelope",
    "exclamation-octagon",
    "file-earmark-text",
    "folder",
    "floppy",
    "gear",
    "geo-alt",
    "globe-americas",
    "hand-thumbs-down",
    "hand-thumbs-up",
    "heart",
    "headphones",
    "house",
    "image",
    "journal-bookmark",
    "lightbulb",
    "list-ol",
    "list-ul",
    "list-check",
    "mortarboard",
    "paperclip",
    "pencil",
    "person",
    "pin",
    "pin-angle",
    "radioactive",
    "send",
    "share",
    "stickies",
    "tag",
    "tags",
    "terminal",
    "trash",
    "trophy",
    "vector-pen",
    "unlock",
    "lock",
    "luggage",
    "megaphone",
    "cash-coin",
    "coin",
    "piggy-bank",
]

EMOJI_TO_BOOTSTRAP_ICON = {
    "📁": "folder",
    "🏛️": "building",
    "📊": "bar-chart-line",
    "🧩": "diagram-3",
    "🔐": "lock",
    "🧠": "lightbulb",
    "⚙️": "gear",
    "🛠️": "gear",
    "💼": "bag",
    "📚": "book",
    "🏷️": "tag",
    "📌": "pin",
    "🔥": "exclamation-octagon",
    "🧪": "bug",
    "🧱": "braces",
    "🚀": "send",
    "✅": "list-check",
    "📝": "pencil",
    "📎": "paperclip",
    "🔖": "bookmark",
    "🔓": "unlock",
    "✈️": "airplane",
    "🏠": "house",
    "📧": "envelope",
    "💰": "cash-coin",
    "💖": "heart",
}

ICON_SEARCH_TERMS = {
    "house": ["home", "inicio", "hogar", "casa"],
    "lock": ["candado", "seguridad", "security", "bloqueo"],
    "unlock": ["desbloquear", "abrir", "unlock"],
    "envelope": ["mail", "correo", "email", "mensaje"],
    "folder": ["carpeta", "categoria", "categoría", "category"],
    "tag": ["etiqueta", "tag", "label"],
    "tags": ["etiquetas", "tags", "labels"],
    "file-earmark-text": ["documento", "document", "archivo", "file", "texto"],
    "person": ["persona", "usuario", "user"],
    "calendar": ["calendario", "calendar", "fecha", "date"],
    "gear": ["configuracion", "configuración", "settings", "ajustes"],
    "cloud": ["nube", "cloud"],
    "database": ["base de datos", "database", "db"],
    "book": ["libro", "book", "manual"],
    "bookmark": ["marcador", "bookmark"],
}


def icon_to_css_class(icon_name: str | None, fallback: str = "folder") -> str:
    normalized = normalize_icon_name(icon_name, fallback=fallback)
    return f"bi bi-{normalized}"


def normalize_icon_name(icon_name: str | None, fallback: str = "folder") -> str:
    cleaned = (icon_name or "").strip().lower()
    if not cleaned:
        return fallback

    if cleaned in EMOJI_TO_BOOTSTRAP_ICON:
        return EMOJI_TO_BOOTSTRAP_ICON[cleaned]

    cleaned = cleaned.replace("bi bi-", "").replace("bi-", "")
    cleaned = re.sub(r"\s+", "-", cleaned)
    cleaned = re.sub(r"[^a-z0-9\-]", "", cleaned)

    if cleaned in BOOTSTRAP_ICON_NAMES:
        return cleaned
    return fallback


def is_likely_emoji(value: str | None) -> bool:
    text = (value or "").strip()
    if not text:
        return False
    if text in EMOJI_TO_BOOTSTRAP_ICON:
        return True
    return any(ord(char) > 127 for char in text)


def icon_picker_catalog() -> list[dict[str, str]]:
    entries: list[dict[str, str]] = []
    for icon in BOOTSTRAP_ICON_NAMES:
        base_keywords = icon.replace("-", " ")
        extra = " ".join(ICON_SEARCH_TERMS.get(icon, []))
        keywords = f"{icon} {base_keywords} {extra}".strip()
        entries.append({"value": icon, "keywords": keywords})
    return entries


def migration_pairs_for_emoji(values: Iterable[str | None]) -> list[tuple[str, str]]:
    pairs: list[tuple[str, str]] = []
    for icon in values:
        if not icon:
            continue
        value = icon.strip()
        mapped = EMOJI_TO_BOOTSTRAP_ICON.get(value)
        if mapped:
            pairs.append((value, mapped))
    return pairs
