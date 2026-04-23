import pytest

from wanshitong import create_app, ensure_database_initialized
from wanshitong.model import Usuario, db


def test_create_app_instance(app):
    assert app is not None
    assert app.config["SQLALCHEMY_DATABASE_URI"].startswith("sqlite")


def test_ensure_database_creates_admin(app):
    # Ensure database initialized creates admin user
    with app.app_context():
        ensure_database_initialized(app)
        admin = db.session.execute(db.select(Usuario).filter_by(tipo="admin")).scalar_one_or_none()
        assert admin is not None
        assert admin.tipo == "admin"


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
