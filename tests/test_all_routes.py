# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 BMO Soluciones, S.A.

from __future__ import annotations

import io
from datetime import datetime, timezone

from flask import url_for

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
from wanshitong.utils import avatar_dir, document_image_dir, site_asset_dir

ID_ADMIN = "01KPYS82MH1FE4YFF3KEWYE4A1"
ID_EDITOR = "01KPYS82MH1FE4YFF3KEWYE4A2"
ID_USER_DELETE = "01KPYS82MH1FE4YFF3KEWYE4A3"
ID_GRUPO = "01KPYS82MH1FE4YFF3KEWYE4B1"
ID_GRUPO_DELETE = "01KPYS82MH1FE4YFF3KEWYE4B2"
ID_CATEGORIA = "01KPYS82MH1FE4YFF3KEWYE4C1"
ID_CATEGORIA_DELETE = "01KPYS82MH1FE4YFF3KEWYE4C2"
ID_ETIQUETA = "01KPYS82MH1FE4YFF3KEWYE4D1"
ID_ETIQUETA_DELETE = "01KPYS82MH1FE4YFF3KEWYE4D2"
ID_DOCUMENTO = "01KPYS82MH1FE4YFF3KEWYE4E1"
ID_DOCUMENTO_DELETE = "01KPYS82MH1FE4YFF3KEWYE4E2"
ID_PERMISO = "01KPYS82MH1FE4YFF3KEWYE4F1"
ID_VERSION = "01KPYS82MH1FE4YFF3KEWYE4G1"

SKIP_ENDPOINTS = {"auth.logout"}
OK_OR_REDIRECT = {200, 301, 302, 303, 307, 308}
RUN_TOKEN = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S%f")


def _upsert_usuario(user_id: str, usuario: str, tipo: str, password: str) -> Usuario:
    registro = db.session.get(Usuario, user_id)
    if registro is None:
        registro = Usuario()
        registro.id = user_id
        db.session.add(registro)

    registro.usuario = usuario
    registro.acceso = proteger_passwd(password)
    registro.tipo = tipo
    registro.activo = True
    registro.nombre = usuario
    registro.apellido = "test"
    return registro


def _seed_static_data(app) -> None:
    with app.app_context():
        admin = _upsert_usuario(ID_ADMIN, "admin-static", "admin", "admin-static")
        editor = _upsert_usuario(ID_EDITOR, "editor-static", "editor", "editor-static")
        _upsert_usuario(ID_USER_DELETE, "delete-static", "editor", "delete-static")

        grupo = db.session.get(Grupo, ID_GRUPO)
        if grupo is None:
            grupo = Grupo()
            grupo.id = ID_GRUPO
            db.session.add(grupo)
        grupo.nombre = "grupo-static"

        grupo_delete = db.session.get(Grupo, ID_GRUPO_DELETE)
        if grupo_delete is None:
            grupo_delete = Grupo()
            grupo_delete.id = ID_GRUPO_DELETE
            db.session.add(grupo_delete)
        grupo_delete.nombre = "grupo-delete-static"

        categoria = db.session.get(Categoria, ID_CATEGORIA)
        if categoria is None:
            categoria = Categoria()
            categoria.id = ID_CATEGORIA
            db.session.add(categoria)
        categoria.nombre = "categoria-static"
        categoria.slug = "categoria-static"
        categoria.icono = "folder"
        categoria.color = "#0ea5e9"

        categoria_delete = db.session.get(Categoria, ID_CATEGORIA_DELETE)
        if categoria_delete is None:
            categoria_delete = Categoria()
            categoria_delete.id = ID_CATEGORIA_DELETE
            db.session.add(categoria_delete)
        categoria_delete.nombre = "categoria-delete-static"
        categoria_delete.slug = "categoria-delete-static"
        categoria_delete.icono = "folder"
        categoria_delete.color = "#22c55e"

        etiqueta = db.session.get(Etiqueta, ID_ETIQUETA)
        if etiqueta is None:
            etiqueta = Etiqueta()
            etiqueta.id = ID_ETIQUETA
            db.session.add(etiqueta)
        etiqueta.nombre = "etiqueta-static"
        etiqueta.slug = "etiqueta-static"
        etiqueta.icono = "tag"
        etiqueta.color = "#f97316"

        etiqueta_delete = db.session.get(Etiqueta, ID_ETIQUETA_DELETE)
        if etiqueta_delete is None:
            etiqueta_delete = Etiqueta()
            etiqueta_delete.id = ID_ETIQUETA_DELETE
            db.session.add(etiqueta_delete)
        etiqueta_delete.nombre = "etiqueta-delete-static"
        etiqueta_delete.slug = "etiqueta-delete-static"
        etiqueta_delete.icono = "tag"
        etiqueta_delete.color = "#a855f7"

        documento = db.session.get(Documento, ID_DOCUMENTO)
        if documento is None:
            documento = Documento()
            documento.id = ID_DOCUMENTO
            db.session.add(documento)
        documento.titulo = "documento-static"
        documento.slug = "documento-static"
        documento.contenido = "# Documento static"
        documento.autor_id = editor.id
        documento.categoria_id = categoria.id
        documento.estado = "public"
        documento.visibilidad = "publico"
        documento.numero_version = 1
        if etiqueta not in documento.etiquetas:
            documento.etiquetas.append(etiqueta)

        documento_delete = db.session.get(Documento, ID_DOCUMENTO_DELETE)
        if documento_delete is None:
            documento_delete = Documento()
            documento_delete.id = ID_DOCUMENTO_DELETE
            db.session.add(documento_delete)
        documento_delete.titulo = "documento-delete-static"
        documento_delete.slug = "documento-delete-static"
        documento_delete.contenido = "contenido delete"
        documento_delete.autor_id = editor.id
        documento_delete.categoria_id = categoria.id
        documento_delete.estado = "draft"
        documento_delete.visibilidad = "privado"
        documento_delete.numero_version = 1

        version = db.session.get(VersionDocumento, ID_VERSION)
        if version is None:
            version = VersionDocumento()
            version.id = ID_VERSION
            db.session.add(version)
        version.documento_id = documento.id
        version.titulo = "documento-static-v1"
        version.contenido = "version 1"
        version.numero_version = 1
        version.modificado_por_id = admin.id
        version.descripcion_cambio = "seed"

        permiso = db.session.get(PermisoDocumento, ID_PERMISO)
        if permiso is None:
            permiso = PermisoDocumento()
            permiso.id = ID_PERMISO
            db.session.add(permiso)
        permiso.documento_id = documento.id
        permiso.grupo_id = grupo.id
        permiso.usuario_id = None
        permiso.tipo_permiso = "lectura"

        db.session.commit()

        # Media files for routes with <path:filename>
        avatar_path = avatar_dir() / f"{ID_EDITOR}.png"
        avatar_path.write_bytes(b"avatar")
        editor.avatar_extension = "png"

        site_logo = site_asset_dir() / "test-site-logo.png"
        site_logo.write_bytes(b"site")

        doc_image = document_image_dir(ID_DOCUMENTO) / "test-doc-image.png"
        doc_image.write_bytes(b"doc")
        db.session.commit()


def _login_admin(client) -> None:
    response = client.post(
        "/login",
        data={"email": "admin-static", "password": "admin-static"},
        follow_redirects=True,
    )
    assert response.status_code == 200


def _params_for_rule(rule) -> dict[str, str]:
    endpoint = rule.endpoint
    params: dict[str, str] = {}
    for arg in rule.arguments:
        if arg == "cat_id":
            params[arg] = ID_CATEGORIA_DELETE if endpoint == "admin.eliminar_categoria" else ID_CATEGORIA
        elif arg == "tag_id":
            params[arg] = ID_ETIQUETA_DELETE if endpoint == "admin.eliminar_etiqueta" else ID_ETIQUETA
        elif arg == "grupo_id":
            if endpoint == "admin.eliminar_grupo":
                params[arg] = ID_GRUPO_DELETE
            else:
                params[arg] = ID_GRUPO
        elif arg == "user_id":
            params[arg] = ID_USER_DELETE if endpoint == "admin.eliminar_usuario" else ID_EDITOR
        elif arg == "doc_id":
            if endpoint == "documentos.eliminar":
                params[arg] = ID_DOCUMENTO_DELETE
            else:
                params[arg] = ID_DOCUMENTO
        elif arg == "perm_id":
            params[arg] = ID_PERMISO
        elif arg == "ver_id":
            params[arg] = ID_VERSION
        elif arg == "filename":
            if endpoint == "media_avatar":
                params[arg] = f"{ID_EDITOR}.png"
            elif endpoint == "media_document":
                params[arg] = "test-doc-image.png"
            elif endpoint == "media_site_logo":
                params[arg] = "test-site-logo.png"
            else:
                params[arg] = "WanShiTongLogo.png"
    return params


def _post_kwargs(endpoint: str) -> dict:
    if endpoint == "auth.login":
        return {"data": {"email": "admin-static", "password": "admin-static"}}
    if endpoint == "auth.set_theme":
        return {"json": {"theme": "dark"}}
    if endpoint == "auth.profile":
        return {"data": {"nombre": "Admin", "apellido": "Static", "correo_electronico": "admin@example.com"}}
    if endpoint == "admin.nuevo_usuario":
        return {
            "data": {
                "usuario": f"nuevo-static-{RUN_TOKEN}",
                "nombre": "Nuevo",
                "apellido": "Usuario",
                "correo_electronico": f"nuevo-static-{RUN_TOKEN}@example.com",
                "tipo": "editor",
                "activo": "y",
                "password": "password123",
            }
        }
    if endpoint == "admin.editar_usuario":
        return {
            "data": {
                "usuario": "editor-static",
                "nombre": "Editor",
                "apellido": "Static",
                "correo_electronico": "editor-static@example.com",
                "tipo": "editor",
                "activo": "y",
                "password": "",
            }
        }
    if endpoint in {
        "admin.eliminar_usuario",
        "admin.eliminar_categoria",
        "admin.eliminar_etiqueta",
        "admin.eliminar_grupo",
    }:
        return {"data": {}}
    if endpoint == "admin.nuevo_grupo" or endpoint == "admin.editar_grupo":
        return {
            "data": {
                "nombre": f"grupo-form-static-{RUN_TOKEN}" if endpoint == "admin.nuevo_grupo" else "grupo-static",
                "descripcion": "desc",
                "usuario_ids": [ID_EDITOR],
                "categoria_ids": [ID_CATEGORIA],
            }
        }
    if endpoint == "admin.configuracion":
        return {
            "data": {
                "site_title": "WanShiTong",
                "default_language": "es",
                "uploads_enabled": "y",
                "max_upload_size_mb": "10",
            }
        }
    if endpoint == "admin.nueva_categoria" or endpoint == "admin.editar_categoria":
        return {
            "data": {
                "nombre": (
                    f"categoria-form-static-{RUN_TOKEN}" if endpoint == "admin.nueva_categoria" else "categoria-static"
                ),
                "slug": (
                    f"categoria-form-static-{RUN_TOKEN}" if endpoint == "admin.nueva_categoria" else "categoria-static"
                ),
                "icono": "folder",
                "color": "#0ea5e9",
                "parent_id": "",
                "grupo_ids": [ID_GRUPO],
            }
        }
    if endpoint == "admin.nueva_etiqueta" or endpoint == "admin.editar_etiqueta":
        return {
            "data": {
                "nombre": (
                    f"etiqueta-form-static-{RUN_TOKEN}" if endpoint == "admin.nueva_etiqueta" else "etiqueta-static"
                ),
                "slug": (
                    f"etiqueta-form-static-{RUN_TOKEN}" if endpoint == "admin.nueva_etiqueta" else "etiqueta-static"
                ),
                "icono": "tag",
                "color": "#f97316",
                "parent_id": "",
            }
        }
    if endpoint == "admin.agregar_miembro" or endpoint == "admin.eliminar_miembro":
        return {"data": {}}
    if endpoint == "documentos.nuevo" or endpoint == "documentos.editar":
        return {
            "data": {
                "titulo": f"doc-form-static-{RUN_TOKEN}" if endpoint == "documentos.nuevo" else "documento-static",
                "contenido": "contenido",
                "categoria_id": ID_CATEGORIA,
                "visibilidad": "publico",
                "estado": "public",
                "etiquetas": "etiqueta-static",
                "descripcion_cambio": "cambio",
            }
        }
    if endpoint == "documentos.preview_api":
        return {"json": {"markdown": "# preview"}}
    if endpoint == "documentos.permisos":
        return {"data": {"usuario_id": "", "grupo_id": ID_GRUPO, "tipo_permiso": "lectura"}}
    if endpoint in {"documentos.eliminar", "documentos.restaurar_version", "documentos.eliminar_permiso"}:
        return {"data": {}}
    if endpoint == "documentos.upload_image":
        return {
            "data": {"file": (io.BytesIO(b"file-content"), "route-test.png")},
            "content_type": "multipart/form-data",
        }
    return {"data": {}}


def test_all_routes_without_internal_server_error(app):
    _seed_static_data(app)
    client = app.test_client()
    _login_admin(client)

    with app.test_request_context():
        rules = sorted(app.url_map.iter_rules(), key=lambda rule: (rule.rule, rule.endpoint))

    for rule in rules:
        if rule.endpoint in SKIP_ENDPOINTS:
            continue

        params = _params_for_rule(rule)

        methods: list[str] = []
        if "GET" in rule.methods:
            methods.append("GET")
        if "POST" in rule.methods:
            methods.append("POST")

        for method in methods:
            with app.test_request_context():
                path = url_for(rule.endpoint, **params)

            if method == "GET":
                response = client.get(path, follow_redirects=False)
            else:
                kwargs = _post_kwargs(rule.endpoint)
                response = client.post(path, follow_redirects=False, **kwargs)

            assert (
                response.status_code != 500
            ), f"Ruta {rule.rule} ({rule.endpoint}) metodo {method} devolvio Internal Server Error"

            location = response.headers.get("Location", "")
            if response.status_code in {301, 302, 303, 307, 308} and location.startswith("/"):
                redirected = client.get(location, follow_redirects=False)
                assert (
                    redirected.status_code != 500
                ), f"Ruta {rule.rule} ({rule.endpoint}) metodo {method} redirige a {location} y devolvio 500"

            assert (
                response.status_code in OK_OR_REDIRECT
            ), f"Ruta {rule.rule} ({rule.endpoint}) metodo {method} devolvio {response.status_code}"
