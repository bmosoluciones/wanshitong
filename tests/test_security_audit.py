# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 BMO Soluciones, S.A.

from datetime import datetime, timedelta, timezone
from uuid import uuid4
from wanshitong.model import Usuario, Grupo, Categoria, Documento, PermisoDocumento, db
from wanshitong.auth import proteger_passwd
from wanshitong.utils import set_setting


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


def test_robots_txt_route(app):
    client = app.test_client()
    response = client.get("/robots.txt")
    assert response.status_code == 200
    assert "text/plain" in response.content_type
    assert "User-agent: *" in response.get_data(as_text=True)
    assert "Disallow: /" in response.get_data(as_text=True)


def test_security_contact_and_operator_attribution(app):
    with app.app_context():
        set_setting("operator_name", "Example Knowledge Team")
        set_setting("security_contact", "mailto:security@example.com")
        set_setting("public_origin", "https://docs.example.com")
        db.session.commit()
    client = app.test_client()

    login_response = client.get("/login")
    assert b"Example Knowledge Team" in login_response.data
    assert b'mailto:security@example.com' in login_response.data

    response = client.get("/.well-known/security.txt")
    assert response.status_code == 200
    assert response.mimetype == "text/plain"
    body = response.get_data(as_text=True)
    assert "Contact: mailto:security@example.com" in body
    assert "Canonical: https://docs.example.com/.well-known/security.txt" in body
    expires_line = next(line for line in body.splitlines() if line.startswith("Expires: "))
    expires = datetime.fromisoformat(expires_line.removeprefix("Expires: ").replace("Z", "+00:00"))
    now = datetime.now(timezone.utc)
    assert now + timedelta(days=179) < expires <= now + timedelta(days=180)


def test_security_txt_is_not_published_with_invalid_contact(app):
    with app.app_context():
        set_setting("security_contact", "security@example.com")
        db.session.commit()
    response = app.test_client().get("/.well-known/security.txt")
    assert response.status_code == 404


def test_admin_can_edit_deployment_identity(app):
    client = app.test_client()
    login(client, "app-admin", "app-admin")
    response = client.post(
        "/a/s",
        data={
            "site_title": "WanShiTong",
            "default_language": "es",
            "uploads_enabled": "y",
            "max_upload_size_mb": "10",
            "operator_name": "Example Operations, S.A.",
            "security_contact": "mailto:abuse@example.com",
            "public_origin": "https://knowledge.example.com",
        },
        follow_redirects=True,
    )
    assert response.status_code == 200

    login_page = client.get("/login").get_data(as_text=True)
    assert "Example Operations, S.A." in login_page
    assert "mailto:abuse@example.com" in login_page
    security_txt = client.get("/.well-known/security.txt").get_data(as_text=True)
    assert "Canonical: https://knowledge.example.com/.well-known/security.txt" in security_txt


def test_security_headers_and_noindex(app):
    client = app.test_client()
    response = client.get("/login")
    assert response.status_code == 200
    assert response.headers.get("X-Frame-Options") == "DENY"
    assert response.headers.get("X-Content-Type-Options") == "nosniff"
    assert response.headers.get("X-Robots-Tag") == "noindex, nofollow, noarchive"
    assert response.headers.get("Referrer-Policy") == "strict-origin-when-cross-origin"

    html = response.get_data(as_text=True)
    assert '<meta name="robots" content="noindex, nofollow, noarchive"' in html


def test_open_redirect_prevention(app):
    suffix = uuid4().hex[:6]
    username = f"redirect-user-{suffix}"
    create_user(app, username, "password123")

    client = app.test_client()

    malicious_targets = [
        "https://evil.com",
        "http://evil.com",
        "//evil.com",
        "\\\\evil.com",
        "javascript:alert(1)",
    ]

    for target in malicious_targets:
        response = client.post(
            f"/login?next={target}",
            data={"email": username, "password": "password123"},
            follow_redirects=False,
        )
        assert response.status_code == 302
        assert response.location != target
        assert not response.location.startswith("http://evil.com")
        assert not response.location.startswith("https://evil.com")
        assert not response.location.startswith("//evil.com")
