# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 BMO Soluciones, S.A.

"""Admin blueprint for user, group, and category management."""

from __future__ import annotations

from functools import wraps
from pathlib import Path
from platform import platform as os_platform
from sys import version as py_version
from typing import cast

from flask import Blueprint, abort, flash, jsonify, redirect, render_template, request, session, url_for
from flask_login import current_user, login_required
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from werkzeug.utils import secure_filename

from wanshitong.auth import proteger_passwd
from wanshitong.forms import AppSettingsForm, CategoriaForm, EtiquetaForm, GrupoForm, UsuarioForm
from wanshitong.i18n import _
from wanshitong.icon_catalog import normalize_icon_name
from wanshitong.model import AppConfig, Categoria, Etiqueta, Grupo, Usuario, database
from wanshitong.utils import ALLOWED_IMAGE_EXTENSIONS, ensure_default_settings, set_setting, site_asset_dir, slugify

admin = Blueprint("admin", __name__)


def solo_admin(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if current_user.tipo != "admin":
            abort(403)
        return f(*args, **kwargs)

    return decorated


def solo_admin_o_editor(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if current_user.tipo not in {"admin", "editor"}:
            abort(403)
        return f(*args, **kwargs)

    return decorated


def _commit_or_rollback() -> None:
    try:
        database.session.commit()
    except Exception:
        database.session.rollback()
        raise


def _ensure_settings() -> None:
    ensure_default_settings(current_user.usuario if current_user.is_authenticated else None)


def _get_setting_value(key: str, fallback: str) -> str:
    setting = database.session.execute(database.select(AppConfig).where(AppConfig.clave == key)).scalar_one_or_none()
    if setting is None or setting.valor is None:
        return fallback
    return setting.valor


# ─── Usuarios ────────────────────────────────────────────────────────────────


@admin.route("/u")
@login_required
@solo_admin
def usuarios():
    lista = database.session.execute(database.select(Usuario).order_by(Usuario.usuario)).scalars().all()
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
                return render_template(
                    "admin/configuracion.html",
                    form=form,
                    current_site_logo=_get_setting_value("site_logo_filename", ""),
                    current_site_favicon=_get_setting_value("site_favicon_filename", ""),
                )
            filename = _store_site_logo(logo_file, extension)
            set_setting("site_logo_filename", filename, current_user.usuario)

        favicon_file = request.files.get(form.site_favicon.name)
        if favicon_file and favicon_file.filename:
            extension = _validated_favicon_extension(favicon_file.filename)
            if extension is None:
                flash(str(_("Formato de favicon no soportado. Use .ico o .png.")), "error")
                return render_template(
                    "admin/configuracion.html",
                    form=form,
                    current_site_logo=_get_setting_value("site_logo_filename", ""),
                    current_site_favicon=_get_setting_value("site_favicon_filename", ""),
                )
            filename = _store_site_favicon(favicon_file, extension)
            set_setting("site_favicon_filename", filename, current_user.usuario)

        session["lang"] = updates["default_language"]
        session.modified = True
        _commit_or_rollback()
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
        current_site_favicon=_get_setting_value("site_favicon_filename", ""),
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


def _validated_favicon_extension(filename: str) -> str | None:
    extension = Path(secure_filename(filename)).suffix.lower().lstrip(".")
    if extension in {"ico", "png"}:
        return extension
    return None


def _store_site_favicon(uploaded_file, extension: str) -> str:
    directory = site_asset_dir()
    for existing in directory.glob("favicon.*"):
        existing.unlink()
    filename = f"favicon.{extension}"
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
        _commit_or_rollback()
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
        _commit_or_rollback()
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
    _commit_or_rollback()
    flash(str(_("Usuario eliminado.")), "info")
    return redirect(url_for("admin.usuarios"))


# ─── Grupos ──────────────────────────────────────────────────────────────────


@admin.route("/g")
@login_required
@solo_admin
def grupos():
    lista = database.session.execute(database.select(Grupo).order_by(Grupo.nombre)).scalars().all()
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
        _commit_or_rollback()
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
        _commit_or_rollback()
        flash(str(_("Grupo actualizado exitosamente.")), "success")
        return redirect(url_for("admin.grupos"))
    return render_template(
        "admin/grupo_form.html",
        form=form,
        grupo=grupo,
        categoria_paths={categoria.id: _categoria_path_label(categoria) for categoria in grupo.categorias},
    )


@admin.route("/g/<grupo_id>/delete", methods=["POST"])
@login_required
@solo_admin
def eliminar_grupo(grupo_id):
    grupo = database.session.get(Grupo, grupo_id)
    if grupo is None:
        abort(404)
    database.session.delete(grupo)
    _commit_or_rollback()
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
        _commit_or_rollback()
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
        _commit_or_rollback()
        flash(str(_("Usuario removido del grupo.")), "info")
    return redirect(url_for("admin.editar_grupo", grupo_id=grupo_id))


# ─── Categorías ──────────────────────────────────────────────────────────────


@admin.route("/c")
@login_required
@solo_admin
def categorias():
    lista = database.session.execute(database.select(Categoria).order_by(Categoria.nombre)).scalars().all()
    categorias_rows = _categoria_hierarchy_rows(lista)
    return render_template("admin/categorias.html", categorias_rows=categorias_rows)


@admin.route("/c/new", methods=["GET", "POST"])
@login_required
@solo_admin
def nueva_categoria():
    form = CategoriaForm()
    todas = database.session.execute(database.select(Categoria).order_by(Categoria.nombre)).scalars().all()
    form.parent_id.choices = _categoria_parent_choices(todas)
    form.grupo_ids.choices = _grupo_choices()
    if form.validate_on_submit():
        cat = Categoria()
        cat.nombre = form.nombre.data
        cat.slug = slugify((form.slug.data or "").strip() or form.nombre.data, "category")
        raw_icon = (form.icono.data or "").strip()
        cat.icono = normalize_icon_name(raw_icon, fallback="folder") if raw_icon else None
        cat.color = (form.color.data or "").strip() or None
        cat.parent_id = form.parent_id.data or None
        if cat.parent_id is None and _root_slug_exists_categoria(cat.slug):
            flash(
                str(_("El slug ya existe en una categoría de primer nivel. Use uno diferente.")),
                "error",
            )
            return render_template("admin/categoria_form.html", form=form, categoria=None)
        cat.grupos = _get_selected_grupos(form.grupo_ids.data)
        cat.creado_por = current_user.usuario
        database.session.add(cat)
        try:
            _commit_or_rollback()
        except IntegrityError:
            flash(str(_("No se pudo crear la categoría por un conflicto de unicidad.")), "error")
            return render_template("admin/categoria_form.html", form=form, categoria=None)
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
        database.session.execute(database.select(Categoria).where(Categoria.id != cat_id).order_by(Categoria.nombre))
        .scalars()
        .all()
    )
    form.parent_id.choices = _categoria_parent_choices(todas)
    form.grupo_ids.choices = _grupo_choices()
    if not form.is_submitted():
        form.grupo_ids.data = [grupo.id for grupo in cat.grupos]
    if form.validate_on_submit():
        new_parent_id = form.parent_id.data or None
        new_slug = slugify((form.slug.data or "").strip() or form.nombre.data, "category")
        if new_parent_id is None and _root_slug_exists_categoria(new_slug, exclude_id=cat.id):
            flash(
                str(_("Este slug ya está en uso en primer nivel. Antes de mover la categoría a raíz, cambie el slug.")),
                "error",
            )
            return render_template("admin/categoria_form.html", form=form, categoria=cat)

        cat.nombre = form.nombre.data
        cat.slug = new_slug
        raw_icon = (form.icono.data or "").strip()
        cat.icono = normalize_icon_name(raw_icon, fallback="folder") if raw_icon else None
        cat.color = (form.color.data or "").strip() or None
        cat.parent_id = new_parent_id
        cat.grupos = _get_selected_grupos(form.grupo_ids.data)
        cat.modificado_por = current_user.usuario
        try:
            _commit_or_rollback()
        except IntegrityError:
            flash(str(_("No se pudo actualizar la categoría por un conflicto de unicidad.")), "error")
            return render_template("admin/categoria_form.html", form=form, categoria=cat)
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
    _commit_or_rollback()
    flash(str(_("Categoría eliminada.")), "info")
    return redirect(url_for("admin.categorias"))


@admin.route("/t")
@login_required
@solo_admin_o_editor
def etiquetas():
    lista = database.session.execute(database.select(Etiqueta).order_by(Etiqueta.nombre)).scalars().all()
    etiquetas_rows = _etiqueta_hierarchy_rows(lista)
    return render_template("admin/etiquetas.html", etiquetas_rows=etiquetas_rows)


@admin.route("/t/new", methods=["GET", "POST"])
@login_required
@solo_admin_o_editor
def nueva_etiqueta():
    form = EtiquetaForm()
    todas = database.session.execute(database.select(Etiqueta).order_by(Etiqueta.nombre)).scalars().all()
    form.parent_id.choices = _etiqueta_parent_choices(todas)
    if form.validate_on_submit():
        tag = Etiqueta()
        tag.nombre = form.nombre.data.strip().lower()
        tag.slug = slugify((form.slug.data or "").strip() or form.nombre.data, "tag")
        raw_icon = (form.icono.data or "").strip()
        tag.icono = normalize_icon_name(raw_icon, fallback="tag") if raw_icon else None
        tag.color = (form.color.data or "").strip() or None
        tag.parent_id = form.parent_id.data or None
        if tag.parent_id is None and _root_slug_exists_etiqueta(tag.slug):
            flash(
                str(_("El slug ya existe en una etiqueta de primer nivel. Use uno diferente.")),
                "error",
            )
            return render_template("admin/etiqueta_form.html", form=form, etiqueta=None)
        tag.creado_por = current_user.usuario
        database.session.add(tag)
        try:
            _commit_or_rollback()
        except IntegrityError:
            flash(str(_("No se pudo crear la etiqueta por un conflicto de unicidad.")), "error")
            return render_template("admin/etiqueta_form.html", form=form, etiqueta=None)
        flash(str(_("Etiqueta creada exitosamente.")), "success")
        return redirect(url_for("admin.etiquetas"))
    return render_template("admin/etiqueta_form.html", form=form, etiqueta=None)


@admin.route("/t/<tag_id>/edit", methods=["GET", "POST"])
@login_required
@solo_admin_o_editor
def editar_etiqueta(tag_id):
    tag = database.session.get(Etiqueta, tag_id)
    if tag is None:
        abort(404)

    form = EtiquetaForm(obj=tag)
    todas = (
        database.session.execute(database.select(Etiqueta).where(Etiqueta.id != tag_id).order_by(Etiqueta.nombre))
        .scalars()
        .all()
    )
    form.parent_id.choices = _etiqueta_parent_choices(todas)
    if form.validate_on_submit():
        new_parent_id = form.parent_id.data or None
        new_slug = slugify((form.slug.data or "").strip() or form.nombre.data, "tag")
        if new_parent_id is None and _root_slug_exists_etiqueta(new_slug, exclude_id=tag.id):
            flash(
                str(_("Este slug ya está en uso en primer nivel. Antes de mover la etiqueta a raíz, cambie el slug.")),
                "error",
            )
            return render_template("admin/etiqueta_form.html", form=form, etiqueta=tag)

        tag.nombre = form.nombre.data.strip().lower()
        tag.slug = new_slug
        raw_icon = (form.icono.data or "").strip()
        tag.icono = normalize_icon_name(raw_icon, fallback="tag") if raw_icon else None
        tag.color = (form.color.data or "").strip() or None
        tag.parent_id = new_parent_id
        tag.modificado_por = current_user.usuario
        try:
            _commit_or_rollback()
        except IntegrityError:
            flash(str(_("No se pudo actualizar la etiqueta por un conflicto de unicidad.")), "error")
            return render_template("admin/etiqueta_form.html", form=form, etiqueta=tag)
        flash(str(_("Etiqueta actualizada exitosamente.")), "success")
        return redirect(url_for("admin.etiquetas"))
    return render_template("admin/etiqueta_form.html", form=form, etiqueta=tag)


@admin.route("/t/<tag_id>/delete", methods=["POST"])
@login_required
@solo_admin_o_editor
def eliminar_etiqueta(tag_id):
    tag = database.session.get(Etiqueta, tag_id)
    if tag is None:
        abort(404)
    database.session.delete(tag)
    _commit_or_rollback()
    flash(str(_("Etiqueta eliminada.")), "info")
    return redirect(url_for("admin.etiquetas"))


def _grupo_choices() -> list[tuple[str, str]]:
    grupos = database.session.execute(database.select(Grupo).order_by(Grupo.nombre)).scalars().all()
    return [(grupo.id, grupo.nombre) for grupo in grupos]


def _populate_group_form_choices(form: GrupoForm) -> None:
    usuarios = database.session.execute(database.select(Usuario).order_by(Usuario.usuario)).scalars().all()
    categorias = database.session.execute(database.select(Categoria).order_by(Categoria.nombre)).scalars().all()
    form.usuario_ids.choices = [(usuario.id, usuario.usuario) for usuario in usuarios if usuario.activo]
    form.categoria_ids.choices = [
        (categoria.id, _categoria_path_label(categoria)) for categoria, _, _ in _categoria_hierarchy_rows(categorias)
    ]


def _hierarchy_rows(items, name_attr: str = "nombre") -> list[tuple[object, int, str]]:
    by_parent: dict[str | None, list[object]] = {}
    by_id: dict[str, object] = {}
    for item in items:
        item_id = cast(str, getattr(item, "id"))
        item_parent_id = cast(str | None, getattr(item, "parent_id"))
        by_id[item_id] = item
        by_parent.setdefault(item_parent_id, []).append(item)

    def key_fn(obj: object) -> str:
        return cast(str, getattr(obj, name_attr)).lower()

    for siblings in by_parent.values():
        siblings.sort(key=key_fn)

    roots: list[object] = []
    for item in items:
        parent_id = cast(str | None, getattr(item, "parent_id"))
        if parent_id is None or parent_id not in by_id:
            roots.append(item)
    roots.sort(key=key_fn)

    rows: list[tuple[object, int, str]] = []
    visited: set[str] = set()

    def walk(node: object, depth: int, parent_path: str = "") -> None:
        node_id = cast(str, getattr(node, "id"))
        if node_id in visited:
            return
        visited.add(node_id)
        node_name = cast(str, getattr(node, name_attr))
        path = f"{parent_path} / {node_name}" if parent_path else node_name
        rows.append((node, depth, path))
        for child in by_parent.get(node_id, []):
            walk(child, depth + 1, path)

    for root in roots:
        walk(root, 0)

    for item in sorted(items, key=key_fn):
        item_id = cast(str, getattr(item, "id"))
        if item_id not in visited:
            walk(item, 0)

    return rows


def _indent_label(label: str, depth: int) -> str:
    if depth <= 0:
        return label
    return f"{'- ' * depth}{label}"


def _categoria_hierarchy_rows(
    categorias: list[Categoria],
) -> list[tuple[Categoria, int, str]]:
    return cast(list[tuple[Categoria, int, str]], _hierarchy_rows(categorias))


def _etiqueta_hierarchy_rows(
    etiquetas: list[Etiqueta],
) -> list[tuple[Etiqueta, int, str]]:
    return cast(list[tuple[Etiqueta, int, str]], _hierarchy_rows(etiquetas))


def _categoria_parent_choices(categorias: list[Categoria]) -> list[tuple[str, str]]:
    return [("", _("Ninguna"))] + [
        (categoria.id, _indent_label(categoria.nombre, depth))
        for categoria, depth, _ in _categoria_hierarchy_rows(categorias)
    ]


def _etiqueta_parent_choices(etiquetas: list[Etiqueta]) -> list[tuple[str, str]]:
    return [("", _("Ninguna"))] + [
        (etiqueta.id, _indent_label(etiqueta.nombre, depth))
        for etiqueta, depth, _ in _etiqueta_hierarchy_rows(etiquetas)
    ]


def _categoria_path_label(categoria: Categoria) -> str:
    path: list[str] = []
    current = categoria
    while current is not None:
        path.append(current.nombre)
        current = current.parent
    path.reverse()
    return " / ".join(path)


def _get_selected_usuarios(usuario_ids: list[str]) -> list[Usuario]:
    if not usuario_ids:
        return []
    return database.session.execute(database.select(Usuario).where(Usuario.id.in_(usuario_ids))).scalars().all()


def _get_selected_categorias(categoria_ids: list[str]) -> list[Categoria]:
    if not categoria_ids:
        return []
    return database.session.execute(database.select(Categoria).where(Categoria.id.in_(categoria_ids))).scalars().all()


def _get_selected_grupos(grupo_ids: list[str]) -> list[Grupo]:
    if not grupo_ids:
        return []
    return database.session.execute(database.select(Grupo).where(Grupo.id.in_(grupo_ids))).scalars().all()


def _root_slug_exists_categoria(slug: str, exclude_id: str | None = None) -> bool:
    stmt = database.select(Categoria).where(Categoria.slug == slug, Categoria.parent_id.is_(None))
    if exclude_id:
        stmt = stmt.where(Categoria.id != exclude_id)
    return database.session.execute(stmt).scalar_one_or_none() is not None


def _root_slug_exists_etiqueta(slug: str, exclude_id: str | None = None) -> bool:
    stmt = database.select(Etiqueta).where(Etiqueta.slug == slug, Etiqueta.parent_id.is_(None))
    if exclude_id:
        stmt = stmt.where(Etiqueta.id != exclude_id)
    return database.session.execute(stmt).scalar_one_or_none() is not None
