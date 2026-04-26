# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 BMO Soluciones, S.A.


from wanshitong import ensure_database_initialized
from wanshitong.auth import proteger_passwd
from wanshitong.model import Usuario, db


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
