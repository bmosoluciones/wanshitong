# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 BMO Soluciones, S.A.

from uuid import uuid4
from wanshitong.model import Usuario, Grupo, Categoria, Documento, PermisoDocumento, db
from wanshitong.auth import proteger_passwd


def create_user(app, username, password="password123", tipo="editor"):
    with app.app_context():
        user = Usuario()
        user.usuario = username
        user.acceso = proteger_passwd(password)
        user.tipo = tipo
        user.activo = True
        db.session.add(user)
        db.session.commit()
        return user.id


def create_group(app, name):
    with app.app_context():
        group = Grupo(nombre=name)
        db.session.add(group)
        db.session.commit()
        return group.id


def create_category(app, name, group_ids=None):
    with app.app_context():
        cat = Categoria(nombre=name)
        if group_ids:
            groups = db.session.execute(db.select(Grupo).where(Grupo.id.in_(group_ids))).scalars().all()
            cat.grupos.extend(groups)
        db.session.add(cat)
        db.session.commit()
        return cat.id


def create_document(app, titulo, autor_id, categoria_id=None, group_permissions=None):
    with app.app_context():
        doc = Documento(
            titulo=titulo,
            contenido=f"Contenido de {titulo}",
            autor_id=autor_id,
            categoria_id=categoria_id,
            estado="public",
            visibilidad="privado",
            slug=f"{titulo.lower().replace(' ', '-')}-{uuid4().hex[:6]}",
        )
        db.session.add(doc)
        db.session.flush()
        if group_permissions:
            for group_id, tipo in group_permissions.items():
                perm = PermisoDocumento(documento_id=doc.id, grupo_id=group_id, tipo_permiso=tipo)
                db.session.add(perm)
        db.session.commit()
        return doc.id


def login(client, username, password="password123"):
    return client.post("/login", data={"email": username, "password": password}, follow_redirects=True)


def test_anonymous_access_denied(app):
    client = app.test_client()
    routes = [
        "/",
        "/d/",
        "/d/some-id",
        "/d/some-id/edit",
        "/d/new",
        "/a/u",
    ]
    for route in routes:
        response = client.get(route)
        assert response.status_code == 302
        assert "/login" in response.location


def test_authenticated_user_no_groups_cannot_see_restricted_docs(app):
    suffix = uuid4().hex[:6]
    user_id = create_user(app, f"user-{suffix}")
    group_id = create_group(app, f"group-{suffix}")
    doc_id = create_document(app, f"Secret Doc {suffix}", user_id, group_permissions={group_id: "lectura"})

    client = app.test_client()
    login(client, f"user-{suffix}")

    # Direct access
    assert client.get(f"/d/{doc_id}").status_code == 403

    # List view
    response = client.get("/d/")
    assert f"Secret Doc {suffix}" not in response.get_data(as_text=True)


def test_author_access_strictly_by_groups(app):
    """Even if I am the author, I cannot see it if I am not in the allowed group."""
    suffix = uuid4().hex[:6]
    user_id = create_user(app, f"author-{suffix}")
    other_group_id = create_group(app, f"other-group-{suffix}")
    doc_id = create_document(app, f"Author Restricted {suffix}", user_id, group_permissions={other_group_id: "lectura"})

    client = app.test_client()
    login(client, f"author-{suffix}")

    assert client.get(f"/d/{doc_id}").status_code == 403


def test_group_access_works(app):
    suffix = uuid4().hex[:6]
    group_id = create_group(app, f"allowed-group-{suffix}")
    user_id = create_user(app, f"member-{suffix}")

    with app.app_context():
        user = db.session.get(Usuario, user_id)
        group = db.session.get(Grupo, group_id)
        user.grupos.append(group)
        db.session.commit()

    doc_id = create_document(app, f"Group Doc {suffix}", user_id, group_permissions={group_id: "lectura"})

    client = app.test_client()
    login(client, f"member-{suffix}")

    assert client.get(f"/d/{doc_id}").status_code == 200
    assert f"Group Doc {suffix}" in client.get("/d/").get_data(as_text=True)


def test_search_results_filtering(app):
    suffix = uuid4().hex[:6]
    group_id = create_group(app, f"search-group-{suffix}")
    user_id = create_user(app, f"searcher-{suffix}")

    with app.app_context():
        user = db.session.get(Usuario, user_id)
        group = db.session.get(Grupo, group_id)
        user.grupos.append(group)
        db.session.commit()

    # Doc 1: accessible via group
    create_document(app, f"Visible Search {suffix}", user_id, group_permissions={group_id: "lectura"})
    # Doc 2: not accessible
    create_document(app, f"Hidden Search {suffix}", user_id)

    client = app.test_client()
    login(client, f"searcher-{suffix}")

    # Search for common term 'Search'
    response = client.get("/d/?q=Search")
    data = response.get_data(as_text=True)
    assert f"Visible Search {suffix}" in data
    assert f"Hidden Search {suffix}" not in data


def test_sidebar_navigation_filtering(app):
    suffix = uuid4().hex[:6]
    group_id = create_group(app, f"nav-group-{suffix}")
    user_id = create_user(app, f"navigator-{suffix}")

    with app.app_context():
        user = db.session.get(Usuario, user_id)
        group = db.session.get(Grupo, group_id)
        user.grupos.append(group)
        db.session.commit()

    cat1_id = create_category(app, f"Visible Cat {suffix}", group_ids=[group_id])
    cat2_id = create_category(app, f"Hidden Cat {suffix}")

    create_document(app, f"Doc in Visible Cat {suffix}", user_id, categoria_id=cat1_id)
    create_document(app, f"Doc in Hidden Cat {suffix}", user_id, categoria_id=cat2_id)

    client = app.test_client()
    login(client, f"navigator-{suffix}")

    response = client.get("/")
    data = response.get_data(as_text=True)
    assert f"Visible Cat {suffix}" in data
    assert f"Hidden Cat {suffix}" not in data
    assert f"Doc in Visible Cat {suffix}" in data
    assert f"Doc in Hidden Cat {suffix}" not in data


def test_media_access_protection(app):
    suffix = uuid4().hex[:6]
    user_id = create_user(app, f"media-user-{suffix}")
    doc_id = create_document(app, f"Media Doc {suffix}", user_id)

    client = app.test_client()

    # Anonymous
    response = client.get(f"/media/documents/{doc_id}/test.png")
    assert response.status_code == 302

    # Authenticated but no access
    login(client, f"media-user-{suffix}")
    response = client.get(f"/media/documents/{doc_id}/test.png")
    assert response.status_code == 403


def test_no_individual_user_permissions_allowed(app):
    """Verify that PermisoDocumento does not have usuario_id anymore."""
    with app.app_context():
        from wanshitong.model import PermisoDocumento

        assert not hasattr(PermisoDocumento, "usuario_id")
        assert not hasattr(PermisoDocumento, "usuario")
