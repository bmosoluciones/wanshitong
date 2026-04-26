# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 BMO Soluciones, S.A.

from __future__ import annotations

import re
from pathlib import Path

from flask import current_app, url_for

from wanshitong.model import AppConfig, Usuario, database

DEFAULT_SETTINGS = {
    "site_title": {"value": "WanShiTong", "type": "string"},
    "site_logo_filename": {"value": "", "type": "string"},
    "site_favicon_filename": {"value": "", "type": "string"},
    "default_language": {"value": "es", "type": "string"},
    "uploads_enabled": {"value": "1", "type": "bool"},
    "max_upload_size_mb": {"value": "10", "type": "int"},
}

ALLOWED_IMAGE_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp"}


def slugify(value: str | None, fallback: str = "item") -> str:
    text = (value or "").strip().lower()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    text = re.sub(r"-{2,}", "-", text).strip("-")
    return text or fallback


def ensure_default_settings(created_by: str | None = None) -> None:
    for key, definition in DEFAULT_SETTINGS.items():
        setting = database.session.execute(
            database.select(AppConfig).where(AppConfig.clave == key)
        ).scalar_one_or_none()
        if setting is not None:
            continue
        setting = AppConfig()
        setting.clave = key
        setting.valor = definition["value"]
        setting.tipo = definition["type"]
        setting.creado_por = created_by
        database.session.add(setting)
    try:
        database.session.flush()
    except Exception:
        database.session.rollback()
        raise


def get_setting(key: str, fallback: str) -> str:
    try:
        setting = database.session.execute(
            database.select(AppConfig).where(AppConfig.clave == key)
        ).scalar_one_or_none()
    except Exception:
        return fallback
    if setting is None or setting.valor in (None, ""):
        return fallback
    return setting.valor


def set_setting(key: str, value: str, modified_by: str | None = None) -> None:
    setting = database.session.execute(database.select(AppConfig).where(AppConfig.clave == key)).scalar_one_or_none()
    if setting is None:
        setting = AppConfig()
        setting.clave = key
        setting.valor = value
        setting.tipo = DEFAULT_SETTINGS.get(key, {"type": "string"})["type"]
        setting.creado_por = modified_by
        database.session.add(setting)
    else:
        setting.valor = value
        setting.modificado_por = modified_by


def uploads_enabled() -> bool:
    return get_setting("uploads_enabled", "1") == "1"


def max_upload_size_bytes() -> int:
    size_mb = int(get_setting("max_upload_size_mb", "10") or "10")
    return size_mb * 1024 * 1024


def uploads_root() -> Path:
    root = Path(current_app.config["UPLOADS_ROOT"])
    root.mkdir(parents=True, exist_ok=True)
    return root


def avatar_dir() -> Path:
    path = uploads_root() / "avatars"
    path.mkdir(parents=True, exist_ok=True)
    return path


def document_image_dir(doc_id: str) -> Path:
    path = uploads_root() / "documents" / doc_id
    path.mkdir(parents=True, exist_ok=True)
    return path


def site_asset_dir() -> Path:
    path = uploads_root() / "site"
    path.mkdir(parents=True, exist_ok=True)
    return path


def avatar_filename(user_id: str, extension: str) -> str:
    return f"{user_id}.{extension.lower()}"


def avatar_url(user: Usuario | None) -> str | None:
    if user is None or not user.avatar_extension:
        return None
    return url_for(
        "media_avatar",
        filename=avatar_filename(user.id, user.avatar_extension),
    )


def site_logo_url() -> str:
    logo_filename = get_setting("site_logo_filename", "")
    if logo_filename:
        return url_for("media_site_logo", filename=logo_filename)
    return url_for("static", filename="WanShiTongLogo.png")


def site_favicon_url() -> str:
    favicon_filename = get_setting("site_favicon_filename", "")
    if favicon_filename:
        return url_for("media_site_logo", filename=favicon_filename)
    return url_for("static", filename="favicon.ico")


def site_favicon_mime_type() -> str:
    favicon_filename = get_setting("site_favicon_filename", "")
    suffix = Path(favicon_filename).suffix.lower()
    if suffix == ".png":
        return "image/png"
    return "image/x-icon"
