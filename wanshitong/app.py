# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 BMO Soluciones, S.A.

"""App module."""

from __future__ import annotations

from flask import Blueprint, render_template
from flask_login import current_user, login_required
from sqlalchemy import func

from wanshitong.acl import puede_leer
from wanshitong.model import Categoria, Documento, Etiqueta, Usuario, database

app = Blueprint("app", __name__)


@app.route("/")
@login_required
def index():
    stmt = database.select(Documento).where(Documento.estado != "archived")
    stmt = stmt.order_by(Documento.timestamp.desc())
    documentos = [
        doc
        for doc in database.session.execute(stmt).scalars().all()
        if puede_leer(doc, current_user)
    ]

    recientes = documentos[:10]
    document_count = len(documentos)
    published_count = sum(1 for doc in documentos if doc.estado == "public")
    category_ids = {doc.categoria_id for doc in documentos if doc.categoria_id}
    category_count = len(category_ids)
    tag_ids = {tag.id for doc in documentos for tag in doc.etiquetas if tag.id}
    tag_count = len(tag_ids)

    return render_template(
        "index.html",
        recientes=recientes,
        summary={
            "documents": document_count,
            "active": document_count,
            "published": published_count,
            "categories": category_count,
            "tags": tag_count,
        },
    )
