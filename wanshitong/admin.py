# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 BMO Soluciones, S.A.

"""Admin blueprint for user, group, and category management."""

from __future__ import annotations

from functools import wraps
from pathlib import Path
from platform import platform as os_platform
from sys import version as py_version
from typing import cast

from flask import (
    Blueprint,
    abort,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from flask_login import current_user, login_required
from sqlalchemy import text
from werkzeug.utils import secure_filename

from wanshitong.auth import proteger_passwd
from wanshitong.forms import (
    AppSettingsForm,
    CategoriaForm,
    EtiquetaForm,
    GrupoForm,
    UsuarioForm,
)
from wanshitong.i18n import _
from wanshitong.model import AppConfig, Categoria, Etiqueta, Grupo, Usuario, database
from wanshitong.utils import (
    ALLOWED_IMAGE_EXTENSIONS,
    ensure_default_settings,
    set_setting,
    site_asset_dir,
    slugify,
)

admin = Blueprint("admin", __name__)


def solo_admin(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if current_user.tipo != "admin":
            abort(403)
        return f(*args, **kwargs)

    return decorated


def _ensure_settings() -> None:
    ensure_default_settings(
        current_user.usuario if current_user.is_authenticated else None
    )


def _get_setting_value(key: str, fallback: str) -> str:
    setting = database.session.execute(
        database.select(AppConfig).where(AppConfig.clave == key)
    ).scalar_one_or_none()
    if setting is None or setting.valor is None:
        return fallback
    return setting.valor


# ─── Usuarios ────────────────────────────────────────────────────────────────


@admin.route("/u")
@login_required
@solo_admin
def usuarios():
    lista = (
        database.session.execute(database.select(Usuario).order_by(Usuario.usuario))
        .scalars()
        .all()
    )
    return render_template("admin/usuarios.html", usuarios=lista)


@admin.route("/s", methods=["GET", "POST"])
@login_required
@solo_admin
def configuracion():
    _ensure_settings()

    form = AppSettingsForm()
    if form.validate_on_submit():
        updates = {
            "site_title": form.site_title.data.strip(),
            "default_language": form.default_language.data,
            "uploads_enabled": "1" if form.uploads_enabled.data else "0",
            "max_upload_size_mb": form.max_upload_size_mb.data.strip(),
        }
        for key, value in updates.items():
            set_setting(key, value, current_user.usuario)

        logo_file = request.files.get(form.site_logo.name)
        if logo_file and logo_file.filename:
            extension = _validated_image_extension(logo_file.filename)
            if extension is None:
                flash(str(_("Formato de logo no soportado.")), "error")
                return render_template("admin/configuracion.html", form=form)
            filename = _store_site_logo(logo_file, extension)
            set_setting("site_logo_filename", filename, current_user.usuario)

        session["lang"] = updates["default_language"]
        session.modified = True
        database.session.commit()
        flash(str(_("Configuración actualizada exitosamente.")), "success")
        return redirect(url_for("admin.configuracion"))

    if form.site_title.data is None:
        form.site_title.data = _get_setting_value("site_title", "WanShiTong")
        form.default_language.data = _get_setting_value("default_language", "en")
        form.uploads_enabled.data = _get_setting_value("uploads_enabled", "1") == "1"
        form.max_upload_size_mb.data = _get_setting_value("max_upload_size_mb", "10")

    return render_template(
        "admin/configuracion.html",
        form=form,
        current_site_logo=_get_setting_value("site_logo_filename", ""),
    )


def _validated_image_extension(filename: str) -> str | None:
    extension = Path(secure_filename(filename)).suffix.lower().lstrip(".")
    if extension in ALLOWED_IMAGE_EXTENSIONS:
        return extension
    return None


def _store_site_logo(uploaded_file, extension: str) -> str:
    directory = site_asset_dir()
    for existing in directory.glob("logo.*"):
        existing.unlink()
    filename = f"logo.{extension}"
    uploaded_file.save(directory / filename)
    return filename


@admin.route("/system")
@login_required
@solo_admin
def system_info():
    engine_name = _database_engine_name()
    sqlite_path = _sqlite_database_path()
    db_status = "ok"
    try:
        database.session.execute(text("SELECT 1"))
    except Exception:
        database.session.rollback()
        db_status = "error"

    payload = {
        "system": os_platform(),
        "python_version": py_version.split()[0],
        "database": {
            "engine": engine_name,
            "status": db_status,
        },
    }
    if sqlite_path:
        payload["database"]["sqlite_path"] = sqlite_path
    return jsonify(payload), 200


def _database_engine_name() -> str:
    dialect = (database.engine.url.get_backend_name() or "").lower()
    if dialect.startswith("postgres"):
        return "PostgreSQL"
    if dialect.startswith("mysql"):
        return "MySQL"
    if dialect.startswith("sqlite"):
        return "SQLite"
    return dialect or "Unknown"


def _sqlite_database_path() -> str | None:
    url = database.engine.url
    if (url.get_backend_name() or "").lower() != "sqlite":
        return None
    database_path = url.database
    if database_path in (None, "", ":memory:"):
        return database_path or ":memory:"
    return str(Path(cast(str, database_path)).resolve())


@admin.route("/u/new", methods=["GET", "POST"])
@login_required
@solo_admin
def nuevo_usuario():
    form = UsuarioForm()
    if form.validate_on_submit():
        usuario = Usuario()
        usuario.usuario = form.usuario.data
        usuario.nombre = form.nombre.data
        usuario.apellido = form.apellido.data
        usuario.correo_electronico = form.correo_electronico.data or None
        usuario.tipo = form.tipo.data
        usuario.activo = form.activo.data
        password = form.password.data
        if not password:
            flash(str(_("La contraseña es requerida al crear un usuario.")), "warning")
            return render_template("admin/usuario_form.html", form=form, usuario=None)
        usuario.acceso = proteger_passwd(password)
        usuario.creado_por = current_user.usuario
        database.session.add(usuario)
        database.session.commit()
        flash(str(_("Usuario creado exitosamente.")), "success")
        return redirect(url_for("admin.usuarios"))
    return render_template("admin/usuario_form.html", form=form, usuario=None)


@admin.route("/u/<user_id>/edit", methods=["GET", "POST"])
@login_required
@solo_admin
def editar_usuario(user_id):
    usuario = database.session.get(Usuario, user_id)
    if usuario is None:
        abort(404)

    form = UsuarioForm(obj=usuario)
    if form.validate_on_submit():
        usuario.usuario = form.usuario.data
        usuario.nombre = form.nombre.data
        usuario.apellido = form.apellido.data
        usuario.correo_electronico = form.correo_electronico.data or None
        usuario.tipo = form.tipo.data
        usuario.activo = form.activo.data
        usuario.modificado_por = current_user.usuario
        if form.password.data:
            usuario.acceso = proteger_passwd(form.password.data)
        database.session.commit()
        flash(str(_("Usuario actualizado exitosamente.")), "success")
        return redirect(url_for("admin.usuarios"))

    form.password.data = ""
    return render_template("admin/usuario_form.html", form=form, usuario=usuario)


@admin.route("/u/<user_id>/delete", methods=["POST"])
@login_required
@solo_admin
def eliminar_usuario(user_id):
    usuario = database.session.get(Usuario, user_id)
    if usuario is None:
        abort(404)
    if usuario.id == current_user.id:
        flash(str(_("No puede eliminar su propio usuario.")), "warning")
        return redirect(url_for("admin.usuarios"))
    database.session.delete(usuario)
    database.session.commit()
    flash(str(_("Usuario eliminado.")), "info")
    return redirect(url_for("admin.usuarios"))


# ─── Grupos ──────────────────────────────────────────────────────────────────


@admin.route("/g")
@login_required
@solo_admin
def grupos():
    lista = (
        database.session.execute(database.select(Grupo).order_by(Grupo.nombre))
        .scalars()
        .all()
    )
    return render_template("admin/grupos.html", grupos=lista)


@admin.route("/g/new", methods=["GET", "POST"])
@login_required
@solo_admin
def nuevo_grupo():
    form = GrupoForm()
    _populate_group_form_choices(form)
    if form.validate_on_submit():
        grupo = Grupo()
        grupo.nombre = form.nombre.data
        grupo.descripcion = form.descripcion.data
        grupo.creado_por = current_user.usuario
        grupo.usuarios = _get_selected_usuarios(form.usuario_ids.data)
        grupo.categorias = _get_selected_categorias(form.categoria_ids.data)
        database.session.add(grupo)
        database.session.commit()
        flash(str(_("Grupo creado exitosamente.")), "success")
        return redirect(url_for("admin.grupos"))
    return render_template("admin/grupo_form.html", form=form, grupo=None)


@admin.route("/g/<grupo_id>/edit", methods=["GET", "POST"])
@login_required
@solo_admin
def editar_grupo(grupo_id):
    grupo = database.session.get(Grupo, grupo_id)
    if grupo is None:
        abort(404)

    form = GrupoForm(obj=grupo)
    _populate_group_form_choices(form)
    if not form.is_submitted():
        form.usuario_ids.data = [usuario.id for usuario in grupo.usuarios]
        form.categoria_ids.data = [categoria.id for categoria in grupo.categorias]
    if form.validate_on_submit():
        grupo.nombre = form.nombre.data
        grupo.descripcion = form.descripcion.data
        grupo.usuarios = _get_selected_usuarios(form.usuario_ids.data)
        grupo.categorias = _get_selected_categorias(form.categoria_ids.data)
        grupo.modificado_por = current_user.usuario
        database.session.commit()
        flash(str(_("Grupo actualizado exitosamente.")), "success")
        return redirect(url_for("admin.grupos"))
    return render_template("admin/grupo_form.html", form=form, grupo=grupo)


@admin.route("/g/<grupo_id>/delete", methods=["POST"])
@login_required
@solo_admin
def eliminar_grupo(grupo_id):
    grupo = database.session.get(Grupo, grupo_id)
    if grupo is None:
        abort(404)
    database.session.delete(grupo)
    database.session.commit()
    flash(str(_("Grupo eliminado.")), "info")
    return redirect(url_for("admin.grupos"))


@admin.route("/g/<grupo_id>/m/<user_id>/add", methods=["POST"])
@login_required
@solo_admin
def agregar_miembro(grupo_id, user_id):
    grupo = database.session.get(Grupo, grupo_id)
    usuario = database.session.get(Usuario, user_id)
    if grupo is None or usuario is None:
        abort(404)
    if usuario not in grupo.usuarios:
        grupo.usuarios.append(usuario)
        database.session.commit()
        flash(str(_("Usuario agregado al grupo.")), "success")
    return redirect(url_for("admin.editar_grupo", grupo_id=grupo_id))


@admin.route("/g/<grupo_id>/m/<user_id>/delete", methods=["POST"])
@login_required
@solo_admin
def eliminar_miembro(grupo_id, user_id):
    grupo = database.session.get(Grupo, grupo_id)
    usuario = database.session.get(Usuario, user_id)
    if grupo is None or usuario is None:
        abort(404)
    if usuario in grupo.usuarios:
        grupo.usuarios.remove(usuario)
        database.session.commit()
        flash(str(_("Usuario removido del grupo.")), "info")
    return redirect(url_for("admin.editar_grupo", grupo_id=grupo_id))


# ─── Categorías ──────────────────────────────────────────────────────────────


@admin.route("/c")
@login_required
@solo_admin
def categorias():
    lista = (
        database.session.execute(database.select(Categoria).order_by(Categoria.nombre))
        .scalars()
        .all()
    )
    return render_template("admin/categorias.html", categorias=lista)


@admin.route("/c/new", methods=["GET", "POST"])
@login_required
@solo_admin
def nueva_categoria():
    form = CategoriaForm()
    todas = (
        database.session.execute(database.select(Categoria).order_by(Categoria.nombre))
        .scalars()
        .all()
    )
    form.parent_id.choices = [("", _("Ninguna"))] + [(c.id, c.nombre) for c in todas]
    form.grupo_ids.choices = _grupo_choices()
    if form.validate_on_submit():
        cat = Categoria()
        cat.nombre = form.nombre.data
        cat.slug = slugify(
            (form.slug.data or "").strip() or form.nombre.data, "category"
        )
        cat.icono = (form.icono.data or "").strip() or None
        cat.color = (form.color.data or "").strip() or None
        cat.parent_id = form.parent_id.data or None
        cat.grupos = _get_selected_grupos(form.grupo_ids.data)
        cat.creado_por = current_user.usuario
        database.session.add(cat)
        database.session.commit()
        flash(str(_("Categoría creada exitosamente.")), "success")
        return redirect(url_for("admin.categorias"))
    return render_template("admin/categoria_form.html", form=form, categoria=None)


@admin.route("/c/<cat_id>/edit", methods=["GET", "POST"])
@login_required
@solo_admin
def editar_categoria(cat_id):
    cat = database.session.get(Categoria, cat_id)
    if cat is None:
        abort(404)

    form = CategoriaForm(obj=cat)
    todas = (
        database.session.execute(
            database.select(Categoria)
            .where(Categoria.id != cat_id)
            .order_by(Categoria.nombre)
        )
        .scalars()
        .all()
    )
    form.parent_id.choices = [("", _("Ninguna"))] + [(c.id, c.nombre) for c in todas]
    form.grupo_ids.choices = _grupo_choices()
    if not form.is_submitted():
        form.grupo_ids.data = [grupo.id for grupo in cat.grupos]
    if form.validate_on_submit():
        cat.nombre = form.nombre.data
        cat.slug = slugify(
            (form.slug.data or "").strip() or form.nombre.data, "category"
        )
        cat.icono = (form.icono.data or "").strip() or None
        cat.color = (form.color.data or "").strip() or None
        cat.parent_id = form.parent_id.data or None
        cat.grupos = _get_selected_grupos(form.grupo_ids.data)
        cat.modificado_por = current_user.usuario
        database.session.commit()
        flash(str(_("Categoría actualizada exitosamente.")), "success")
        return redirect(url_for("admin.categorias"))
    return render_template("admin/categoria_form.html", form=form, categoria=cat)


@admin.route("/c/<cat_id>/delete", methods=["POST"])
@login_required
@solo_admin
def eliminar_categoria(cat_id):
    cat = database.session.get(Categoria, cat_id)
    if cat is None:
        abort(404)
    database.session.delete(cat)
    database.session.commit()
    flash(str(_("Categoría eliminada.")), "info")
    return redirect(url_for("admin.categorias"))


@admin.route("/t")
@login_required
@solo_admin
def etiquetas():
    lista = (
        database.session.execute(database.select(Etiqueta).order_by(Etiqueta.nombre))
        .scalars()
        .all()
    )
    return render_template("admin/etiquetas.html", etiquetas=lista)


@admin.route("/t/new", methods=["GET", "POST"])
@login_required
@solo_admin
def nueva_etiqueta():
    form = EtiquetaForm()
    todas = (
        database.session.execute(database.select(Etiqueta).order_by(Etiqueta.nombre))
        .scalars()
        .all()
    )
    form.parent_id.choices = [("", _("Ninguna"))] + [(t.id, t.nombre) for t in todas]
    if form.validate_on_submit():
        tag = Etiqueta()
        tag.nombre = form.nombre.data.strip().lower()
        tag.slug = slugify((form.slug.data or "").strip() or form.nombre.data, "tag")
        tag.icono = (form.icono.data or "").strip() or None
        tag.color = (form.color.data or "").strip() or None
        tag.parent_id = form.parent_id.data or None
        tag.creado_por = current_user.usuario
        database.session.add(tag)
        database.session.commit()
        flash(str(_("Etiqueta creada exitosamente.")), "success")
        return redirect(url_for("admin.etiquetas"))
    return render_template("admin/etiqueta_form.html", form=form, etiqueta=None)


@admin.route("/t/<tag_id>/edit", methods=["GET", "POST"])
@login_required
@solo_admin
def editar_etiqueta(tag_id):
    tag = database.session.get(Etiqueta, tag_id)
    if tag is None:
        abort(404)

    form = EtiquetaForm(obj=tag)
    todas = (
        database.session.execute(
            database.select(Etiqueta)
            .where(Etiqueta.id != tag_id)
            .order_by(Etiqueta.nombre)
        )
        .scalars()
        .all()
    )
    form.parent_id.choices = [("", _("Ninguna"))] + [(t.id, t.nombre) for t in todas]
    if form.validate_on_submit():
        tag.nombre = form.nombre.data.strip().lower()
        tag.slug = slugify((form.slug.data or "").strip() or form.nombre.data, "tag")
        tag.icono = (form.icono.data or "").strip() or None
        tag.color = (form.color.data or "").strip() or None
        tag.parent_id = form.parent_id.data or None
        tag.modificado_por = current_user.usuario
        database.session.commit()
        flash(str(_("Etiqueta actualizada exitosamente.")), "success")
        return redirect(url_for("admin.etiquetas"))
    return render_template("admin/etiqueta_form.html", form=form, etiqueta=tag)


@admin.route("/t/<tag_id>/delete", methods=["POST"])
@login_required
@solo_admin
def eliminar_etiqueta(tag_id):
    tag = database.session.get(Etiqueta, tag_id)
    if tag is None:
        abort(404)
    database.session.delete(tag)
    database.session.commit()
    flash(str(_("Etiqueta eliminada.")), "info")
    return redirect(url_for("admin.etiquetas"))


def _grupo_choices() -> list[tuple[str, str]]:
    grupos = (
        database.session.execute(database.select(Grupo).order_by(Grupo.nombre))
        .scalars()
        .all()
    )
    return [(grupo.id, grupo.nombre) for grupo in grupos]


def _populate_group_form_choices(form: GrupoForm) -> None:
    usuarios = (
        database.session.execute(database.select(Usuario).order_by(Usuario.usuario))
        .scalars()
        .all()
    )
    categorias = (
        database.session.execute(database.select(Categoria).order_by(Categoria.nombre))
        .scalars()
        .all()
    )
    form.usuario_ids.choices = [
        (usuario.id, usuario.usuario) for usuario in usuarios if usuario.activo
    ]
    form.categoria_ids.choices = [
        (categoria.id, categoria.nombre) for categoria in categorias
    ]


def _get_selected_usuarios(usuario_ids: list[str]) -> list[Usuario]:
    if not usuario_ids:
        return []
    return (
        database.session.execute(
            database.select(Usuario).where(Usuario.id.in_(usuario_ids))
        )
        .scalars()
        .all()
    )


def _get_selected_categorias(categoria_ids: list[str]) -> list[Categoria]:
    if not categoria_ids:
        return []
    return (
        database.session.execute(
            database.select(Categoria).where(Categoria.id.in_(categoria_ids))
        )
        .scalars()
        .all()
    )


def _get_selected_grupos(grupo_ids: list[str]) -> list[Grupo]:
    if not grupo_ids:
        return []
    return (
        database.session.execute(database.select(Grupo).where(Grupo.id.in_(grupo_ids)))
        .scalars()
        .all()
    )
