# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 BMO Soluciones, S.A.

"""Documents blueprint."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from flask import (
    Blueprint,
    abort,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    url_for,
)
from flask_login import current_user, login_required
from werkzeug.utils import secure_filename

from wanshitong.acl import puede_acceder_categoria, puede_editar, puede_leer
from wanshitong.forms import BusquedaForm, DocumentoForm, PermisoForm
from wanshitong.i18n import _
from wanshitong.md_utils import render_markdown
from wanshitong.model import (
    Categoria,
    Documento,
    Etiqueta,
    Grupo,
    PermisoDocumento,
    Usuario,
    VersionDocumento,
    database,
)
from wanshitong.utils import (
    ALLOWED_IMAGE_EXTENSIONS,
    document_image_dir,
    max_upload_size_bytes,
    slugify,
    uploads_enabled,
)

documentos = Blueprint("documentos", __name__)


@documentos.route("/preview", methods=["POST"])
@login_required
def preview_api():
    """Render Markdown to HTML for live preview."""
    data = request.get_json(force=True, silent=True) or {}
    md_text = data.get("markdown", "")
    html = render_markdown(md_text)
    return jsonify({"html": html})


def _get_categoria_choices():
    categorias = database.session.execute(database.select(Categoria)).scalars().all()
    choices = [("", _("Sin categoría"))]
    choices += [
        (c.id, c.nombre)
        for c in categorias
        if current_user.tipo == "admin" or puede_acceder_categoria(c, current_user)
    ]
    return choices


def _get_or_create_etiqueta(nombre: str) -> Etiqueta:
    nombre = nombre.strip().lower()
    etiqueta = database.session.execute(
        database.select(Etiqueta).filter_by(nombre=nombre)
    ).scalar_one_or_none()
    if etiqueta is None:
        etiqueta = Etiqueta()
        etiqueta.nombre = nombre
        etiqueta.slug = slugify(nombre, "tag")
        database.session.add(etiqueta)
    return etiqueta


@documentos.route("/")
@login_required
def lista():
    form = BusquedaForm(request.args, meta={"csrf": False})
    form.categoria_id.choices = _get_categoria_choices()

    q = request.args.get("q", "").strip()
    categoria_id = request.args.get("categoria_id", "").strip()
    estado_filtro = request.args.get("estado", "").strip()
    etiqueta_filtro = request.args.get("etiqueta", "").strip()

    stmt = database.select(Documento)

    if q:
        from sqlalchemy import or_

        stmt = stmt.where(
            or_(
                Documento.titulo.ilike(f"%{q}%"),
                Documento.contenido.ilike(f"%{q}%"),
            )
        )

    if categoria_id:
        stmt = stmt.where(Documento.categoria_id == categoria_id)

    if estado_filtro:
        stmt = stmt.where(Documento.estado == estado_filtro)

    if etiqueta_filtro:
        stmt = stmt.where(
            Documento.etiquetas.any(Etiqueta.nombre.ilike(f"%{etiqueta_filtro}%"))
        )

    # Don't show archived by default unless explicitly requested
    if not estado_filtro:
        stmt = stmt.where(Documento.estado != "archived")

    stmt = stmt.order_by(Documento.timestamp.desc())
    docs = [
        doc
        for doc in database.session.execute(stmt).scalars().all()
        if puede_leer(doc, current_user)
    ]

    return render_template("documentos/lista.html", documentos=docs, form=form)


@documentos.route("/new", methods=["GET", "POST"])
@login_required
def nuevo():
    if current_user.tipo == "consulta":
        abort(403)

    form = DocumentoForm()
    form.categoria_id.choices = _get_categoria_choices()

    if form.validate_on_submit():
        doc = Documento()
        doc.titulo = form.titulo.data
        doc.contenido = form.contenido.data
        doc.autor_id = current_user.id
        doc.categoria_id = form.categoria_id.data or None
        doc.visibilidad = form.visibilidad.data
        doc.estado = form.estado.data
        doc.slug = _build_document_slug(form.titulo.data)
        doc.creado_por = current_user.usuario
        doc.numero_version = 1

        database.session.add(doc)
        database.session.flush()  # Get ID

        # Save initial version
        _guardar_version(
            doc, current_user, str(form.descripcion_cambio.data or _("Versión inicial"))
        )

        # Process tags
        _actualizar_etiquetas(doc, form.etiquetas.data or "")

        database.session.commit()
        flash(str(_("Documento creado exitosamente.")), "success")
        return redirect(url_for("documentos.ver", doc_id=doc.id))

    return render_template("documentos/editar.html", form=form, doc=None)


@documentos.route("/<doc_id>")
@login_required
def ver(doc_id):
    doc = database.session.get(Documento, doc_id)
    if doc is None:
        abort(404)
    if not puede_leer(doc, current_user):
        abort(403)

    html_contenido = render_markdown(doc.contenido)
    puede_edit = puede_editar(doc, current_user)
    category_path = _category_path(doc.categoria)
    return render_template(
        "documentos/ver.html",
        doc=doc,
        html_contenido=html_contenido,
        puede_editar=puede_edit,
        category_path=category_path,
    )


@documentos.route("/<doc_id>/edit", methods=["GET", "POST"])
@login_required
def editar(doc_id):
    doc = database.session.get(Documento, doc_id)
    if doc is None:
        abort(404)
    if not puede_editar(doc, current_user):
        abort(403)

    form = DocumentoForm(obj=doc)
    form.categoria_id.choices = _get_categoria_choices()

    if request.method == "GET":
        form.etiquetas.data = ", ".join(e.nombre for e in doc.etiquetas)

    if form.validate_on_submit():
        # Save current version before changing
        _guardar_version(doc, current_user, form.descripcion_cambio.data or "")

        doc.titulo = form.titulo.data
        doc.contenido = form.contenido.data
        doc.slug = _build_document_slug(form.titulo.data, doc.id)
        doc.categoria_id = form.categoria_id.data or None
        doc.visibilidad = form.visibilidad.data
        doc.modificado_por = current_user.usuario

        estado_anterior = doc.estado
        doc.estado = form.estado.data
        if doc.estado != estado_anterior:
            doc.estado_cambiado_en = datetime.now(timezone.utc)
            doc.estado_cambiado_por_id = current_user.id

        doc.numero_version += 1

        # Process tags
        _actualizar_etiquetas(doc, form.etiquetas.data or "")

        database.session.commit()
        flash(str(_("Documento actualizado exitosamente.")), "success")
        return redirect(url_for("documentos.ver", doc_id=doc.id))

    return render_template("documentos/editar.html", form=form, doc=doc)


@documentos.route("/<doc_id>/delete", methods=["POST"])
@login_required
def eliminar(doc_id):
    doc = database.session.get(Documento, doc_id)
    if doc is None:
        abort(404)
    if not puede_editar(doc, current_user):
        abort(403)

    database.session.delete(doc)
    database.session.commit()
    flash(str(_("Documento eliminado.")), "info")
    return redirect(url_for("documentos.lista"))


@documentos.route("/<doc_id>/history")
@login_required
def historial(doc_id):
    doc = database.session.get(Documento, doc_id)
    if doc is None:
        abort(404)
    if not puede_leer(doc, current_user):
        abort(403)

    versiones = (
        database.session.execute(
            database.select(VersionDocumento)
            .where(VersionDocumento.documento_id == doc_id)
            .order_by(VersionDocumento.numero_version.desc())
        )
        .scalars()
        .all()
    )

    return render_template("documentos/historial.html", doc=doc, versiones=versiones)


@documentos.route("/<doc_id>/v/<ver_id>")
@login_required
def ver_version(doc_id, ver_id):
    doc = database.session.get(Documento, doc_id)
    if doc is None:
        abort(404)
    if not puede_leer(doc, current_user):
        abort(403)

    version = database.session.get(VersionDocumento, ver_id)
    if version is None or version.documento_id != doc_id:
        abort(404)

    html_contenido = render_markdown(version.contenido)
    return render_template(
        "documentos/ver_version.html",
        doc=doc,
        version=version,
        html_contenido=html_contenido,
    )


@documentos.route("/<doc_id>/restore/<ver_id>", methods=["POST"])
@login_required
def restaurar_version(doc_id, ver_id):
    doc = database.session.get(Documento, doc_id)
    if doc is None:
        abort(404)
    if not puede_editar(doc, current_user):
        abort(403)

    version = database.session.get(VersionDocumento, ver_id)
    if version is None or version.documento_id != doc_id:
        abort(404)

    # Save current state as a version
    _guardar_version(
        doc,
        current_user,
        str(_("Antes de restaurar versión ")) + str(version.numero_version),
    )

    doc.titulo = version.titulo
    doc.contenido = version.contenido
    doc.numero_version += 1
    doc.modificado_por = current_user.usuario

    database.session.commit()
    flash(str(_("Versión restaurada exitosamente.")), "success")
    return redirect(url_for("documentos.ver", doc_id=doc.id))


@documentos.route("/<doc_id>/share", methods=["GET", "POST"])
@login_required
def permisos(doc_id):
    doc = database.session.get(Documento, doc_id)
    if doc is None:
        abort(404)
    if not puede_editar(doc, current_user):
        abort(403)

    form = PermisoForm()

    grupos = database.session.execute(database.select(Grupo)).scalars().all()
    form.usuario_id.choices = [("", _("Ninguno"))]
    form.grupo_id.choices = [("", _("Ninguno"))] + [(g.id, g.nombre) for g in grupos]

    if form.validate_on_submit():
        usuario_id = form.usuario_id.data or None
        grupo_id = form.grupo_id.data or None

        if not grupo_id:
            flash(str(_("Debe seleccionar un grupo.")), "warning")
        else:
            permiso = PermisoDocumento()
            permiso.documento_id = doc_id
            permiso.usuario_id = None
            permiso.grupo_id = grupo_id
            permiso.tipo_permiso = form.tipo_permiso.data
            permiso.creado_por = current_user.usuario
            database.session.add(permiso)
            database.session.commit()
            flash(str(_("Permiso agregado.")), "success")
            return redirect(url_for("documentos.permisos", doc_id=doc_id))

    permisos_actuales = (
        database.session.execute(
            database.select(PermisoDocumento).where(
                PermisoDocumento.documento_id == doc_id
            )
        )
        .scalars()
        .all()
    )

    return render_template(
        "documentos/permisos.html", doc=doc, form=form, permisos=permisos_actuales
    )


@documentos.route("/<doc_id>/share/<perm_id>/delete", methods=["POST"])
@login_required
def eliminar_permiso(doc_id, perm_id):
    doc = database.session.get(Documento, doc_id)
    if doc is None:
        abort(404)
    if not puede_editar(doc, current_user):
        abort(403)

    permiso = database.session.get(PermisoDocumento, perm_id)
    if permiso is None or permiso.documento_id != doc_id:
        abort(404)

    database.session.delete(permiso)
    database.session.commit()
    flash(str(_("Permiso eliminado.")), "info")
    return redirect(url_for("documentos.permisos", doc_id=doc_id))


@documentos.route("/<doc_id>/image", methods=["POST"])
@login_required
def upload_image(doc_id):
    doc = database.session.get(Documento, doc_id)
    if doc is None:
        abort(404)
    if not puede_editar(doc, current_user):
        abort(403)
    if not uploads_enabled():
        return jsonify({"error": "uploads-disabled"}), 403

    uploaded = request.files.get("file")
    if uploaded is None or not uploaded.filename:
        return jsonify({"error": "missing-file"}), 400

    extension = _validated_image_extension(uploaded.filename)
    if extension is None:
        return jsonify({"error": "invalid-image"}), 400

    uploaded.stream.seek(0, 2)
    size = uploaded.stream.tell()
    uploaded.stream.seek(0)
    if size > max_upload_size_bytes():
        return jsonify({"error": "file-too-large"}), 400

    filename = _next_document_image_name(doc.id, extension)
    target = document_image_dir(doc.id) / filename
    uploaded.save(target)

    return jsonify(
        {
            "url": url_for("media_document", doc_id=doc.id, filename=filename),
            "filename": filename,
        }
    )


def _guardar_version(doc: Documento, usuario: Usuario, descripcion: str = "") -> None:
    version = VersionDocumento()
    version.documento_id = doc.id
    version.titulo = doc.titulo
    version.contenido = doc.contenido
    version.numero_version = doc.numero_version
    version.modificado_por_id = usuario.id
    version.descripcion_cambio = str(descripcion) if descripcion is not None else None
    version.creado_por = usuario.usuario
    database.session.add(version)


def _actualizar_etiquetas(doc: Documento, etiquetas_str: str) -> None:
    nombres = [n.strip().lower() for n in etiquetas_str.split(",") if n.strip()]
    doc.etiquetas.clear()
    for nombre in nombres:
        if nombre:
            etiqueta = _get_or_create_etiqueta(nombre)
            doc.etiquetas.append(etiqueta)


def _build_document_slug(title: str, doc_id: str | None = None) -> str:
    suffix = doc_id[:6].lower() if doc_id else datetime.now().strftime("%H%M%S")
    return f"{slugify(title, 'doc')}-{suffix}"


def _validated_image_extension(filename: str) -> str | None:
    extension = Path(secure_filename(filename)).suffix.lower().lstrip(".")
    if extension in ALLOWED_IMAGE_EXTENSIONS:
        return extension
    return None


def _next_document_image_name(doc_id: str, extension: str) -> str:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S%f")
    return f"{doc_id}-{timestamp}.{extension}"


def _category_path(categoria: Categoria | None) -> list[Categoria]:
    if categoria is None:
        return []

    path: list[Categoria] = []
    current = categoria
    while current is not None:
        path.append(current)
        current = current.parent
    path.reverse()
    return path
