# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 BMO Soluciones, S.A.

from __future__ import annotations

from uuid import uuid4

from sqlalchemy.exc import IntegrityError

from wanshitong.auth import proteger_passwd
from wanshitong.model import Categoria, Documento, Grupo, Usuario, db


def _login(client, username: str, password: str) -> None:
    response = client.post(
        "/login",
        data={"email": username, "password": password},
        follow_redirects=False,
    )
    assert response.status_code in {302, 303}


def test_editor_can_manage_tags_but_not_categories(app):
    editor_username = f"editor-tags-{uuid4().hex[:8]}"
    with app.app_context():
        editor = Usuario()
        editor.usuario = editor_username
        editor.acceso = proteger_passwd("password123")
        editor.tipo = "editor"
        editor.activo = True
        db.session.add(editor)
        db.session.commit()

    client = app.test_client()
    _login(client, editor_username, "password123")

    assert client.get("/a/t").status_code == 200
    assert client.get("/a/c").status_code == 403


def test_slug_uniqueness_scoped_to_root_nodes(app):
    suffix = uuid4().hex[:8]
    with app.app_context():
        root_a = Categoria()
        root_a.nombre = f"Finance Root {suffix}"
        root_a.slug = f"public-{suffix}"
        db.session.add(root_a)

        root_b = Categoria()
        root_b.nombre = f"RRHH Root {suffix}"
        root_b.slug = f"rrhh-{suffix}"
        db.session.add(root_b)
        db.session.flush()

        child_same_slug = Categoria()
        child_same_slug.nombre = f"Child Public {suffix}"
        child_same_slug.slug = f"public-{suffix}"
        child_same_slug.parent_id = root_b.id
        db.session.add(child_same_slug)
        db.session.commit()

        duplicate_root = Categoria()
        duplicate_root.nombre = f"Duplicate Root {suffix}"
        duplicate_root.slug = f"public-{suffix}"
        duplicate_root.parent_id = None
        db.session.add(duplicate_root)

        failed = False
        try:
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            failed = True

        assert failed is True


def test_document_view_shows_category_links_and_filtered_list(app):
    suffix = uuid4().hex[:8]
    with app.app_context():
        editor = Usuario()
        editor.usuario = f"editor-doc-{suffix}"
        editor.acceso = proteger_passwd("password123")
        editor.tipo = "editor"
        editor.activo = True
        db.session.add(editor)

        group = Grupo()
        group.nombre = f"group-doc-{suffix}"
        db.session.add(group)
        db.session.flush()

        editor.grupos.append(group)

        categoria = Categoria()
        categoria.nombre = f"Public {suffix}"
        categoria.slug = f"public-doc-{suffix}"
        categoria.grupos.append(group)
        db.session.add(categoria)
        db.session.flush()

        doc = Documento()
        doc.titulo = f"Documento {suffix}"
        doc.slug = f"documento-{suffix}"
        doc.contenido = "contenido"
        doc.autor_id = editor.id
        doc.categoria_id = categoria.id
        doc.estado = "public"
        doc.visibilidad = "publico"
        doc.numero_version = 1
        db.session.add(doc)
        db.session.commit()

        doc_id = doc.id
        categoria_id = categoria.id

    client = app.test_client()
    _login(client, f"editor-doc-{suffix}", "password123")

    response_ver = client.get(f"/d/{doc_id}")
    assert response_ver.status_code == 200
    assert f"/d/?categoria_id={categoria_id}" in response_ver.get_data(as_text=True)

    response_lista = client.get(f"/d/?categoria_id={categoria_id}")
    assert response_lista.status_code == 200
    assert f"Documento {suffix}" in response_lista.get_data(as_text=True)
