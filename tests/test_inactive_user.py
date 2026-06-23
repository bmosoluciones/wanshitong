# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2025 BMO Soluciones, S.A.

from uuid import uuid4
from wanshitong.model import Usuario, Grupo, Documento, PermisoDocumento, db
from wanshitong.auth import proteger_passwd

def create_user(app, username, password="password123", tipo="editor", activo=True):
    with app.app_context():
        user = Usuario()
        user.usuario = username
        user.acceso = proteger_passwd(password)
        user.tipo = tipo
        user.activo = activo
        db.session.add(user)
        db.session.commit()
        return user.id

def create_group(app, name):
    with app.app_context():
        group = Grupo(nombre=name)
        db.session.add(group)
        db.session.commit()
        return group.id

def add_user_to_group(app, user_id, group_id):
    with app.app_context():
        user = db.session.get(Usuario, user_id)
        group = db.session.get(Grupo, group_id)
        user.grupos.append(group)
        db.session.commit()

def create_document(app, titulo, autor_id, group_permissions=None):
    with app.app_context():
        doc = Documento(
            titulo=titulo,
            contenido=f"Contenido de {titulo}",
            autor_id=autor_id,
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

def test_inactive_user_cannot_login(app):
    create_user(app, "inactive_user", activo=False)
    client = app.test_client()
    response = client.post("/login", data={"email": "inactive_user", "password": "password123"}, follow_redirects=True)
    assert "Usuario o contraseña incorrectos." in response.get_data(as_text=True)

def test_inactive_user_session_invalidated(app):
    user_id = create_user(app, "active_then_inactive", activo=True)
    client = app.test_client()
    client.post("/login", data={"email": "active_then_inactive", "password": "password123"}, follow_redirects=True)

    response = client.get("/")
    assert response.status_code == 200

    with app.app_context():
        user = db.session.get(Usuario, user_id)
        user.activo = False
        db.session.commit()

    response = client.get("/")
    assert response.status_code == 302
    assert "/login" in response.location

def test_group_isolation_enforced(app):
    """User in Group A cannot see Doc in Group B."""
    user_a_id = create_user(app, "user_a")
    group_a_id = create_group(app, "Group A")
    add_user_to_group(app, user_a_id, group_a_id)

    user_b_id = create_user(app, "user_b")
    group_b_id = create_group(app, "Group B")
    add_user_to_group(app, user_b_id, group_b_id)

    doc_b_id = create_document(app, "Doc B", user_b_id, group_permissions={group_b_id: "lectura"})

    client = app.test_client()
    client.post("/login", data={"email": "user_a", "password": "password123"}, follow_redirects=True)

    # Direct URL access to Doc B should be 403
    response = client.get(f"/d/{doc_b_id}")
    assert response.status_code == 403

    # List view should not contain Doc B
    response = client.get("/d/")
    assert "Doc B" not in response.get_data(as_text=True)

def test_inactive_user_cannot_access_even_with_group(app):
    """An inactive user cannot access anything, even if they are in an allowed group."""
    user_id = create_user(app, "inactive_with_group", activo=False)
    group_id = create_group(app, "Some Group")
    add_user_to_group(app, user_id, group_id)

    doc_id = create_document(app, "Some Doc", user_id, group_permissions={group_id: "lectura"})

    client = app.test_client()
    # Mock a session if possible, or just try to login
    client.post("/login", data={"email": "inactive_with_group", "password": "password123"}, follow_redirects=True)

    response = client.get(f"/d/{doc_id}")
    assert response.status_code == 302 # Redirected to login because session was not established or invalidated
