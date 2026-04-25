# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 BMO Soluciones, S.A.

"""Auth module."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
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
from flask_login import current_user, login_required, login_user, logout_user
from werkzeug.utils import secure_filename

from wanshitong.forms import LoginForm, ProfileForm
from wanshitong.i18n import _
from wanshitong.log import log
from wanshitong.model import Usuario, database
from wanshitong.utils import (
    ALLOWED_IMAGE_EXTENSIONS,
    avatar_dir,
    avatar_filename,
    max_upload_size_bytes,
)

auth = Blueprint("auth", __name__)


@auth.route("/login", methods=["GET", "POST"])
def login():
    form = LoginForm()

    if form.validate_on_submit():
        usuario_id = form.email.data or ""
        clave = form.password.data or ""

        if validar_acceso(usuario_id, clave):
            registro = database.session.execute(
                database.select(Usuario).filter_by(usuario=usuario_id)
            ).scalar_one_or_none()
            if not registro:
                registro = database.session.execute(
                    database.select(Usuario).filter_by(correo_electronico=usuario_id)
                ).scalar_one_or_none()

            if registro is not None:
                login_user(registro)
                return redirect(url_for("app.index"))

        flash(str(_("Usuario o contraseña incorrectos.")), "error")

    return render_template("auth/login.html", form=form)


@auth.route("/logout")
@login_required
def logout():
    logout_user()
    flash(str(_("Sesión cerrada correctamente.")), "info")
    return redirect(url_for("auth.login"))


@auth.route("/me", methods=["GET", "POST"])
@login_required
def profile():
    usuario = database.session.get(Usuario, current_user.id)
    if usuario is None:
        abort(404)
    form = ProfileForm(obj=usuario)

    if request.method == "GET":
        form.nombre.data = usuario.nombre
        form.apellido.data = usuario.apellido
        form.correo_electronico.data = usuario.correo_electronico

    if form.validate_on_submit():
        usuario.nombre = form.nombre.data
        usuario.apellido = form.apellido.data
        usuario.correo_electronico = form.correo_electronico.data or None
        usuario.modificado_por = usuario.usuario

        if form.password.data:
            usuario.acceso = proteger_passwd(form.password.data)

        avatar = request.files.get(form.avatar.name)
        if avatar and avatar.filename:
            extension = _validated_image_extension(avatar.filename)
            if extension is None:
                flash(str(_("Formato de imagen no soportado.")), "error")
                return render_template("auth/profile.html", form=form, usuario=usuario)
            avatar.stream.seek(0, 2)
            size = avatar.stream.tell()
            avatar.stream.seek(0)
            if size > max_upload_size_bytes():
                flash(str(_("La imagen excede el tamaño máximo permitido.")), "error")
                return render_template("auth/profile.html", form=form, usuario=usuario)
            _store_avatar(usuario, avatar, extension)

        database.session.commit()
        flash(str(_("Perfil actualizado exitosamente.")), "success")
        return redirect(url_for("auth.profile"))

    return render_template("auth/profile.html", form=form, usuario=usuario)


@auth.route("/me/theme", methods=["POST"])
@login_required
def set_theme():
    theme = (request.get_json(silent=True) or {}).get("theme", "light")
    if theme not in {"light", "dark"}:
        return jsonify({"error": "invalid-theme"}), 400
    usuario = database.session.get(Usuario, current_user.id)
    if usuario is None:
        return jsonify({"error": "not-found"}), 404
    usuario.theme_preference = theme
    usuario.modificado_por = usuario.usuario
    database.session.commit()
    return jsonify({"theme": theme})


ph = PasswordHasher()


def proteger_passwd(clave: str, /) -> bytes:
    _hash = ph.hash(clave.encode()).encode("utf-8")
    return _hash


def validar_acceso(usuario_id: str, acceso: str, /) -> bool:
    log.trace(f"Verifying access for {usuario_id}")
    registro = database.session.execute(database.select(Usuario).filter_by(usuario=usuario_id)).scalar_one_or_none()

    if not registro:
        registro = database.session.execute(
            database.select(Usuario).filter_by(correo_electronico=usuario_id)
        ).scalar_one_or_none()

    if registro is not None:
        try:
            ph.verify(registro.acceso, acceso.encode())
            clave_validada = True
        except VerifyMismatchError:
            clave_validada = False
    else:
        log.trace(f"User record not found for {usuario_id}")
        clave_validada = False

    log.trace(f"Access validation result is {clave_validada}")
    if clave_validada:
        registro.ultimo_acceso = datetime.now()
        database.session.commit()

    return clave_validada


def _validated_image_extension(filename: str) -> str | None:
    extension = Path(secure_filename(filename)).suffix.lower().lstrip(".")
    if extension in ALLOWED_IMAGE_EXTENSIONS:
        return extension
    return None


def _store_avatar(usuario: Usuario, uploaded_file, extension: str) -> None:
    directory = avatar_dir()
    for allowed in ALLOWED_IMAGE_EXTENSIONS:
        existing = directory / avatar_filename(usuario.id, allowed)
        if existing.exists():
            existing.unlink()
    target = directory / avatar_filename(usuario.id, extension)
    uploaded_file.save(target)
    usuario.avatar_extension = extension
