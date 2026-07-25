# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 BMO Soluciones, S.A.

"""Tests for documents CRUD and ACL."""

import pytest

from wanshitong.acl import puede_editar, puede_leer
from wanshitong.auth import proteger_passwd
from wanshitong.model import (
    Categoria,
    Documento,
    Etiqueta,
    Grupo,
    PermisoDocumento,
    Usuario,
    VersionDocumento,
    db,
)


@pytest.fixture(scope="module")
def usuarios(app):
    """Create test users."""
    with app.app_context():
        admin = db.session.execute(db.select(Usuario).filter_by(usuario="app-admin")).scalar_one_or_none()
        if admin is None:
            admin = db.session.execute(db.select(Usuario).filter_by(tipo="admin")).scalars().first()
        assert admin is not None

        editor = Usuario()
        editor.usuario = "editor1"
        editor.acceso = proteger_passwd("password123")
        editor.nombre = "Editor"
        editor.apellido = "Uno"
        editor.tipo = "editor"
        editor.activo = True
        db.session.add(editor)

        lector = Usuario()
        lector.usuario = "lector1"
        lector.acceso = proteger_passwd("password123")
        lector.nombre = "Lector"
        lector.apellido = "Uno"
        lector.tipo = "consulta"
        lector.activo = True
        db.session.add(lector)

        db.session.commit()
        return {
            "admin": admin.id,
            "editor": editor.id,
            "lector": lector.id,
        }


def _get_usuario(app, user_id):
    with app.app_context():
        return db.session.get(Usuario, user_id)


# ─── Model tests ─────────────────────────────────────────────────────────────


class TestModelos:
    def test_crear_categoria(self, app):
        with app.app_context():
            cat = Categoria()
            cat.nombre = "Ingeniería"
            db.session.add(cat)
            db.session.commit()
            assert cat.id is not None

    def test_categoria_jerarquica(self, app):
        with app.app_context():
            padre = Categoria()
            padre.nombre = "Finanzas"
            db.session.add(padre)
            db.session.flush()

            hijo = Categoria()
            hijo.nombre = "Contabilidad"
            hijo.parent_id = padre.id
            db.session.add(hijo)
            db.session.commit()

            assert hijo.parent_id == padre.id
            assert hijo.parent.nombre == "Finanzas"

    def test_crear_grupo(self, app):
        with app.app_context():
            grupo = Grupo()
            grupo.nombre = "Devs"
            grupo.descripcion = "Equipo de desarrollo"
            db.session.add(grupo)
            db.session.commit()
            assert grupo.id is not None

    def test_usuario_en_grupo(self, app, usuarios):
        with app.app_context():
            editor = db.session.get(Usuario, usuarios["editor"])
            grupo = db.session.execute(db.select(Grupo).filter_by(nombre="Devs")).scalar_one()
            grupo.usuarios.append(editor)
            db.session.commit()
            assert editor in grupo.usuarios

    def test_crear_documento(self, app, usuarios):
        with app.app_context():
            editor = db.session.get(Usuario, usuarios["editor"])
            doc = Documento()
            doc.titulo = "Documento de prueba"
            doc.contenido = "# Hola\n\nEsto es una prueba."
            doc.autor_id = editor.id
            doc.estado = "draft"
            doc.visibilidad = "privado"
            doc.numero_version = 1
            db.session.add(doc)
            db.session.commit()
            assert doc.id is not None
            assert doc.estado == "draft"

    def test_etiquetas_documento(self, app, usuarios):
        with app.app_context():
            editor = db.session.get(Usuario, usuarios["editor"])
            doc = Documento()
            doc.titulo = "Doc con etiquetas"
            doc.contenido = "contenido"
            doc.autor_id = editor.id
            doc.estado = "public"
            doc.visibilidad = "publico"
            doc.numero_version = 1

            etiqueta = Etiqueta()
            etiqueta.nombre = "python"
            db.session.add(etiqueta)
            db.session.flush()

            doc.etiquetas.append(etiqueta)
            db.session.add(doc)
            db.session.commit()
            assert len(doc.etiquetas) == 1
            assert doc.etiquetas[0].nombre == "python"


# ─── ACL tests ───────────────────────────────────────────────────────────────


class TestACL:
    def _crear_doc(self, app, autor_id, estado="draft", visibilidad="privado"):
        with app.app_context():
            doc = Documento()
            doc.titulo = f"Doc {estado} {visibilidad}"
            doc.contenido = "contenido"
            doc.autor_id = autor_id
            doc.estado = estado
            doc.visibilidad = visibilidad
            doc.numero_version = 1
            db.session.add(doc)
            db.session.commit()
            return doc.id

    def test_admin_puede_leer_todo(self, app, usuarios):
        doc_id = self._crear_doc(app, usuarios["editor"], "draft", "privado")
        with app.app_context():
            admin = db.session.get(Usuario, usuarios["admin"])
            doc = db.session.get(Documento, doc_id)
            assert puede_leer(doc, admin) is True

    def test_admin_puede_editar_todo(self, app, usuarios):
        doc_id = self._crear_doc(app, usuarios["editor"], "draft", "privado")
        with app.app_context():
            admin = db.session.get(Usuario, usuarios["admin"])
            doc = db.session.get(Documento, doc_id)
            assert puede_editar(doc, admin) is True

    def test_autor_no_puede_leer_propio_sin_grupo(self, app, usuarios):
        doc_id = self._crear_doc(app, usuarios["editor"], "draft", "privado")
        with app.app_context():
            editor = db.session.get(Usuario, usuarios["editor"])
            doc = db.session.get(Documento, doc_id)
            # Now requires group/category access
            assert puede_leer(doc, editor) is False

    def test_autor_no_puede_editar_propio_sin_grupo(self, app, usuarios):
        doc_id = self._crear_doc(app, usuarios["editor"], "draft", "privado")
        with app.app_context():
            editor = db.session.get(Usuario, usuarios["editor"])
            doc = db.session.get(Documento, doc_id)
            # Now requires group/category access
            assert puede_editar(doc, editor) is False

    def test_publico_no_visible_sin_acceso_explicito(self, app, usuarios):
        doc_id = self._crear_doc(app, usuarios["editor"], "public", "publico")
        with app.app_context():
            lector = db.session.get(Usuario, usuarios["lector"])
            doc = db.session.get(Documento, doc_id)
            # visibilidad=publico no longer grants access
            assert puede_leer(doc, lector) is False

    def test_privado_no_visible_para_lector_sin_permiso(self, app, usuarios):
        doc_id = self._crear_doc(app, usuarios["editor"], "draft", "privado")
        with app.app_context():
            lector = db.session.get(Usuario, usuarios["lector"])
            doc = db.session.get(Documento, doc_id)
            assert puede_leer(doc, lector) is False

    def test_consulta_no_puede_editar(self, app, usuarios):
        doc_id = self._crear_doc(app, usuarios["editor"], "public", "publico")
        with app.app_context():
            lector = db.session.get(Usuario, usuarios["lector"])
            doc = db.session.get(Documento, doc_id)
            assert puede_editar(doc, lector) is False

    def test_permiso_explicito_grupo(self, app, usuarios):
        doc_id = self._crear_doc(app, usuarios["editor"], "draft", "privado")
        with app.app_context():
            lector = db.session.get(Usuario, usuarios["lector"])
            grupo = Grupo()
            grupo.nombre = "Lectores"
            db.session.add(grupo)
            db.session.flush()
            grupo.usuarios.append(lector)

            permiso = PermisoDocumento()
            permiso.documento_id = doc_id
            permiso.grupo_id = grupo.id
            permiso.tipo_permiso = "lectura"
            db.session.add(permiso)
            db.session.commit()

            doc = db.session.get(Documento, doc_id)
            # Reload lector to get fresh groups
            lector_fresh = db.session.get(Usuario, usuarios["lector"])
            assert puede_leer(doc, lector_fresh) is True


# ─── Markdown rendering tests ────────────────────────────────────────────────


class TestMarkdown:
    def test_render_markdown_basic(self):
        from wanshitong.md_utils import render_markdown

        html = render_markdown("# Título\n\nPárrafo de prueba.")
        assert "<h1>" in html
        assert "Título" in html
        assert "Párrafo" in html

    def test_render_markdown_sanitizes_script(self):
        from wanshitong.md_utils import render_markdown

        html = render_markdown("<script>alert('xss')</script>")
        # bleach removes the script tag (the main XSS vector)
        assert "<script>" not in html
        assert "</script>" not in html

    def test_render_markdown_tables(self):
        from wanshitong.md_utils import render_markdown

        md = "| A | B |\n|---|---|\n| 1 | 2 |"
        html = render_markdown(md)
        assert "<table>" in html

    def test_render_markdown_code(self):
        from wanshitong.md_utils import render_markdown

        html = render_markdown("```python\nprint('hello')\n```")
        assert "<code" in html


# ─── Version history tests ───────────────────────────────────────────────────


class TestVersionado:
    def test_guardar_version(self, app, usuarios):
        with app.app_context():
            editor = db.session.get(Usuario, usuarios["editor"])
            doc = Documento()
            doc.titulo = "Doc Versionado"
            doc.contenido = "Versión 1"
            doc.autor_id = editor.id
            doc.estado = "draft"
            doc.visibilidad = "privado"
            doc.numero_version = 1
            db.session.add(doc)
            db.session.flush()

            # Save initial version
            version1 = VersionDocumento()
            version1.documento_id = doc.id
            version1.titulo = doc.titulo
            version1.contenido = doc.contenido
            version1.numero_version = doc.numero_version
            version1.modificado_por_id = editor.id
            version1.descripcion_cambio = "Versión inicial"
            db.session.add(version1)

            # Update document
            doc.contenido = "Versión 2"
            doc.numero_version = 2

            version2 = VersionDocumento()
            version2.documento_id = doc.id
            version2.titulo = doc.titulo
            version2.contenido = "Versión 2"
            version2.numero_version = 2
            version2.modificado_por_id = editor.id
            version2.descripcion_cambio = "Segunda versión"
            db.session.add(version2)
            db.session.commit()

            versiones = (
                db.session.execute(db.select(VersionDocumento).where(VersionDocumento.documento_id == doc.id))
                .scalars()
                .all()
            )
            assert len(versiones) == 2


# ─── PDF Download tests ──────────────────────────────────────────────────────


class TestDescargarPDF:
    def test_pdf_unauthenticated(self, app):
        client = app.test_client()
        response = client.get("/d/some-doc-id/pdf")
        # should redirect to login
        assert response.status_code == 302
        assert "/login" in response.headers.get("Location", "")

    def test_pdf_unauthorized(self, app, usuarios):
        # Create a private draft document belonging to editor
        with app.app_context():
            editor = db.session.get(Usuario, usuarios["editor"])
            doc = Documento()
            doc.titulo = "Private Note"
            doc.contenido = "Very secret information"
            doc.autor_id = editor.id
            doc.estado = "draft"
            doc.visibilidad = "privado"
            doc.numero_version = 1
            db.session.add(doc)
            db.session.commit()
            doc_id = doc.id

        # Login as lector (has no permission to read editor's private doc without explicit access)
        client = app.test_client()
        client.post("/login", data={"email": "lector1", "password": "password123"})

        response = client.get(f"/d/{doc_id}/pdf")
        # should be 403 Forbidden
        assert response.status_code == 403

    def test_pdf_authorized(self, app, usuarios):
        # Create a document accessible to editor
        with app.app_context():
            admin = db.session.get(Usuario, usuarios["admin"])
            doc = Documento()
            doc.titulo = "Public Note for Export"
            doc.contenido = "This is a beautiful markdown note with a **bold** word."
            doc.autor_id = admin.id
            doc.estado = "public"
            doc.visibilidad = "publico"
            doc.numero_version = 1
            db.session.add(doc)
            db.session.commit()
            doc_id = doc.id

        # Login as admin
        client = app.test_client()
        with app.app_context():
            admin_user = db.session.get(Usuario, usuarios["admin"]).usuario

        client.post("/login", data={"email": admin_user, "password": "app-admin"})

        response = client.get(f"/d/{doc_id}/pdf")
        assert response.status_code == 200
        assert response.mimetype == "application/pdf"
        assert response.headers.get("Content-Disposition", "").startswith("attachment; filename=")


class TestImageUploadGuards:
    def test_image_upload_guards_on_new_and_edit_forms(self, app, usuarios):
        # 1. Create a document first to use for the edit page test
        with app.app_context():
            editor = db.session.get(Usuario, usuarios["editor"])
            admin = db.session.get(Usuario, usuarios["admin"])
            doc = Documento()
            doc.titulo = "Test Doc for Image Upload Guard"
            doc.contenido = "Existing content"
            doc.autor_id = editor.id
            doc.estado = "draft"
            doc.visibilidad = "privado"
            doc.numero_version = 1
            db.session.add(doc)
            db.session.commit()
            doc_id = doc.id
            admin_user = admin.usuario

        client = app.test_client()
        # Login as admin
        client.post("/login", data={"email": admin_user, "password": "app-admin"})

        # 2. Test /d/new (creation form)
        response_new = client.get("/d/new")
        assert response_new.status_code == 200
        html_new = response_new.get_data(as_text=True)
        # Should render 'if (!false) {' to guard against upload when document doesn't exist yet
        assert "if (!false) {" in html_new

        # 3. Test /d/<doc_id>/edit (editing form)
        response_edit = client.get(f"/d/{doc_id}/edit")
        assert response_edit.status_code == 200
        html_edit = response_edit.get_data(as_text=True)
        # Should render 'if (!true) {' because document exists and upload is allowed
        assert "if (!true) {" in html_edit

        # 4. Test backend upload endpoint with "new" as doc_id returns 404
        response_upload_new = client.post("/d/new/image", data={"file": (None, "")})
        assert response_upload_new.status_code == 404
