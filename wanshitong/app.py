# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 BMO Soluciones, S.A.

"""App module."""

from __future__ import annotations

from typing import cast

from flask import Blueprint, render_template
from flask_login import current_user, login_required
from sqlalchemy import func

from wanshitong.acl import puede_leer
from wanshitong.model import Categoria, Documento, Etiqueta, Usuario, database

app = Blueprint("app", __name__)


@app.route("/")
@login_required
def index():
    usuario_actual = cast(Usuario, current_user)

    stmt = database.select(Documento).where(Documento.estado != "archived")
    stmt = stmt.order_by(Documento.timestamp.desc())
    documentos = [doc for doc in database.session.execute(stmt).scalars().all() if puede_leer(doc, usuario_actual)]

    recientes = documentos[:10]
    is_admin = usuario_actual.tipo == "admin"

    document_count = len(documentos)
    active_count = sum(1 for doc in documentos if doc.estado != "archived")
    category_ids = {doc.categoria_id for doc in documentos if doc.categoria_id}
    visible_category_count = len(category_ids)
    tag_ids = {tag.id for doc in documentos for tag in doc.etiquetas if tag.id}
    visible_tag_count = len(tag_ids)

    category_count = visible_category_count
    tag_count = visible_tag_count
    user_count = None
    if is_admin:
        category_count = database.session.scalar(database.select(func.count()).select_from(Categoria)) or 0
        tag_count = database.session.scalar(database.select(func.count()).select_from(Etiqueta)) or 0
        user_count = database.session.scalar(database.select(func.count()).select_from(Usuario)) or 0

    return render_template(
        "index.html",
        recientes=recientes,
        is_admin=is_admin,
        summary={
            "documents": document_count,
            "active": active_count,
            "categories_visible": visible_category_count,
            "tags_visible": visible_tag_count,
            "categories": category_count,
            "tags": tag_count,
            "users": user_count,
        },
    )
