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


def test_category_cycle_prevention(app):
    admin_username = f"admin-cycle-{uuid4().hex[:8]}"
    with app.app_context():
        admin = Usuario()
        admin.usuario = admin_username
        admin.acceso = proteger_passwd("password123")
        admin.tipo = "admin"
        admin.activo = True
        db.session.add(admin)

        cat_a = Categoria()
        cat_a.nombre = f"Category A {uuid4().hex[:4]}"
        cat_a.slug = f"cat-a-{uuid4().hex[:4]}"
        db.session.add(cat_a)
        db.session.flush()

        cat_b = Categoria()
        cat_b.nombre = f"Category B {uuid4().hex[:4]}"
        cat_b.slug = f"cat-b-{uuid4().hex[:4]}"
        cat_b.parent_id = cat_a.id
        db.session.add(cat_b)
        db.session.commit()

        cat_a_id = cat_a.id
        cat_b_id = cat_b.id

    client = app.test_client()
    _login(client, admin_username, "password123")

    response = client.post(
        f"/a/c/{cat_a_id}/edit",
        data={
            "nombre": "Category A Modified",
            "slug": "cat-a-mod",
            "parent_id": cat_b_id,
        },
        follow_redirects=True,
    )
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    if "crearía un ciclo de dependencias" not in html:
        print("HTML WAS:")
        print(html)
    assert "crearía un ciclo de dependencias" in html

    with app.app_context():
        refreshed_a = db.session.get(Categoria, cat_a_id)
        assert refreshed_a.parent_id is None


def test_tag_cycle_prevention(app):
    from wanshitong.model import Etiqueta

    admin_username = f"admin-cycle-{uuid4().hex[:8]}"
    with app.app_context():
        admin = Usuario()
        admin.usuario = admin_username
        admin.acceso = proteger_passwd("password123")
        admin.tipo = "admin"
        admin.activo = True
        db.session.add(admin)

        tag_a = Etiqueta()
        tag_a.nombre = f"Tag A {uuid4().hex[:4]}".lower()
        tag_a.slug = f"tag-a-{uuid4().hex[:4]}"
        db.session.add(tag_a)
        db.session.flush()

        tag_b = Etiqueta()
        tag_b.nombre = f"Tag B {uuid4().hex[:4]}".lower()
        tag_b.slug = f"tag-b-{uuid4().hex[:4]}"
        tag_b.parent_id = tag_a.id
        db.session.add(tag_b)
        db.session.commit()

        tag_a_id = tag_a.id
        tag_b_id = tag_b.id

    client = app.test_client()
    _login(client, admin_username, "password123")

    response = client.post(
        f"/a/t/{tag_a_id}/edit",
        data={
            "nombre": "tag a modified",
            "slug": "tag-a-mod",
            "parent_id": tag_b_id,
        },
        follow_redirects=True,
    )
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert "crearía un ciclo de dependencias" in html

    with app.app_context():
        refreshed_a = db.session.get(Etiqueta, tag_a_id)
        assert refreshed_a.parent_id is None
