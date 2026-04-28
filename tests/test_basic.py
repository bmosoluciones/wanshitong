# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 BMO Soluciones, S.A.


import re

from wanshitong import ensure_database_initialized
from wanshitong.auth import proteger_passwd
from wanshitong.icon_catalog import BOOTSTRAP_ICON_NAMES, icon_picker_catalog
from wanshitong.model import Categoria, Documento, Etiqueta, Grupo, Usuario, db


def _extract_dashboard_value(html: str, title: str) -> int:
    pattern = re.compile(
        rf"dashboard-card-title\">\s*{re.escape(title)}\s*</(?:span|div)>.*?dashboard-card-value\">\s*(\d+)\s*<",
        re.DOTALL,
    )
    match = pattern.search(html)
    assert match is not None, f"Card not found: {title}"
    return int(match.group(1))


def test_create_app_instance(app):
    assert app is not None
    assert app.config["SQLALCHEMY_DATABASE_URI"].startswith("sqlite")


def test_ensure_database_creates_admin(app):
    # Ensure database initialized creates admin user
    with app.app_context():
        ensure_database_initialized(app)
        admins = db.session.execute(db.select(Usuario).filter_by(tipo="admin")).scalars().all()
        assert admins
        assert all(user.tipo == "admin" for user in admins)


def test_login_uses_default_site_logo(app):
    client = app.test_client()
    response = client.get("/login")

    assert response.status_code == 200
    assert b"WanShiTongLogo.png" in response.data


def test_sidebar_uses_spaces_tree_without_tag_section(app):
    client = app.test_client()
    login_response = client.post(
        "/login",
        data={"email": "app-admin", "password": "app-admin"},
        follow_redirects=True,
    )

    assert login_response.status_code == 200

    response = client.get("/")

    assert response.status_code == 200
    assert b"Espacios" in response.data
    assert b'sidebar-section-label">Etiquetas<' not in response.data


def test_health_endpoint_is_public_and_ok(app):
    client = app.test_client()

    response = client.get("/health")

    assert response.status_code == 200
    assert response.is_json
    assert response.get_json() == {"status": "ok"}


def test_icon_picker_catalog_contains_all_bootstrap_icons():
    icons = icon_picker_catalog()
    assert len(icons) == len(BOOTSTRAP_ICON_NAMES)
    assert {icon["value"] for icon in icons} == set(BOOTSTRAP_ICON_NAMES)
    for icon in icons:
        assert icon["keywords"].strip()


def test_ready_endpoint_checks_database_connection(app):
    client = app.test_client()

    response = client.get("/ready")
    payload = response.get_json()

    assert response.status_code == 200
    assert response.is_json
    assert payload["status"] == "ready"
    assert payload["database"] == "ok"


def test_system_endpoint_requires_admin_user(app):
    client = app.test_client()

    anon_response = client.get("/a/system")
    assert anon_response.status_code == 302

    with app.app_context():
        editor = Usuario()
        editor.usuario = "editor-system"
        editor.acceso = proteger_passwd("editor-pass")
        editor.tipo = "editor"
        editor.activo = True
        db.session.add(editor)
        db.session.commit()

    login_response = client.post(
        "/login",
        data={"email": "editor-system", "password": "editor-pass"},
        follow_redirects=True,
    )
    assert login_response.status_code == 200

    editor_response = client.get("/a/system")
    assert editor_response.status_code == 403


def test_system_endpoint_returns_runtime_data_for_admin(app):
    client = app.test_client()

    login_response = client.post(
        "/login",
        data={"email": "app-admin", "password": "app-admin"},
        follow_redirects=True,
    )
    assert login_response.status_code == 200

    response = client.get("/a/system")
    payload = response.get_json()

    assert response.status_code == 200
    assert response.is_json
    assert payload["system"]
    assert payload["python_version"]
    assert payload["database"]["engine"] in {"SQLite", "PostgreSQL", "MySQL"}
    assert payload["database"]["status"] in {"ok", "error"}


def test_dashboard_hides_global_counts_for_non_admin(app):
    client = app.test_client()

    with app.app_context():
        admin = db.session.execute(db.select(Usuario).filter_by(usuario="app-admin")).scalar_one()

        editor = Usuario()
        editor.usuario = "editor-dashboard"
        editor.acceso = proteger_passwd("editor-dashboard")
        editor.tipo = "editor"
        editor.activo = True

        grupo = Grupo()
        grupo.nombre = "grupo-dashboard"
        grupo.usuarios.append(editor)

        categoria_visible = Categoria()
        categoria_visible.nombre = "Categoria visible"
        categoria_visible.slug = "categoria-visible"
        categoria_visible.grupos.append(grupo)

        categoria_oculta = Categoria()
        categoria_oculta.nombre = "Categoria oculta"
        categoria_oculta.slug = "categoria-oculta"

        etiqueta_visible = Etiqueta()
        etiqueta_visible.nombre = "Etiqueta visible"
        etiqueta_visible.slug = "etiqueta-visible"

        etiqueta_oculta = Etiqueta()
        etiqueta_oculta.nombre = "Etiqueta oculta"
        etiqueta_oculta.slug = "etiqueta-oculta"

        db.session.add_all([editor, grupo, categoria_visible, categoria_oculta, etiqueta_visible, etiqueta_oculta])
        db.session.flush()

        doc_visible = Documento()
        doc_visible.titulo = "Doc visible"
        doc_visible.contenido = "visible"
        doc_visible.autor_id = editor.id
        doc_visible.categoria_id = categoria_visible.id
        doc_visible.estado = "public"
        doc_visible.visibilidad = "privado"
        doc_visible.etiquetas.append(etiqueta_visible)

        doc_oculto = Documento()
        doc_oculto.titulo = "Doc oculto"
        doc_oculto.contenido = "oculto"
        doc_oculto.autor_id = admin.id
        doc_oculto.categoria_id = categoria_oculta.id
        doc_oculto.estado = "public"
        doc_oculto.visibilidad = "privado"
        doc_oculto.etiquetas.append(etiqueta_oculta)

        db.session.add_all([doc_visible, doc_oculto])
        db.session.commit()

    login_response = client.post(
        "/login",
        data={"email": "editor-dashboard", "password": "editor-dashboard"},
        follow_redirects=True,
    )
    assert login_response.status_code == 200

    response = client.get("/")
    assert response.status_code == 200

    with app.app_context():
        total_categories = db.session.query(Categoria).count()
        total_tags = db.session.query(Etiqueta).count()

    html = response.get_data(as_text=True)
    assert "Usuarios" not in html
    assert "Total creadas" not in html
    visible_categories = _extract_dashboard_value(html, "Categorías visibles")
    visible_tags = _extract_dashboard_value(html, "Etiquetas visibles")

    assert visible_categories < total_categories
    assert visible_tags < total_tags


def test_dashboard_shows_global_counts_for_admin(app):
    client = app.test_client()

    with app.app_context():
        expected_categories = db.session.query(Categoria).count()
        expected_tags = db.session.query(Etiqueta).count()
        expected_users = db.session.query(Usuario).count()

    login_response = client.post(
        "/login",
        data={"email": "app-admin", "password": "app-admin"},
        follow_redirects=True,
    )
    assert login_response.status_code == 200

    response = client.get("/")
    assert response.status_code == 200

    html = response.get_data(as_text=True)
    assert "Usuarios" in html
    assert "Total creadas" in html
    assert _extract_dashboard_value(html, "Categorías") == expected_categories
    assert _extract_dashboard_value(html, "Etiquetas") == expected_tags
    assert _extract_dashboard_value(html, "Usuarios") == expected_users
