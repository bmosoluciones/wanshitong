# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 BMO Soluciones, S.A.

from flask_wtf import FlaskForm
from flask_wtf.file import FileField
from wtforms import (
    StringField,
    PasswordField,
    SubmitField,
    TextAreaField,
    SelectField,
    SelectMultipleField,
    BooleanField,
)
from wtforms.validators import DataRequired, Length, Optional, Email
from wanshitong.i18n import _


class LoginForm(FlaskForm):
    email = StringField("email", validators=[DataRequired()])
    password = PasswordField("password", validators=[DataRequired(), Length(min=6)])
    submit = SubmitField(_("Iniciar sesión"))


class DocumentoForm(FlaskForm):
    titulo = StringField(_("Título"), validators=[DataRequired(), Length(max=200)])
    contenido = TextAreaField(_("Contenido"), validators=[DataRequired()])
    categoria_id = SelectField(_("Categoría"), validators=[Optional()], coerce=str)
    visibilidad = SelectField(
        _("Visibilidad"),
        choices=[("privado", _("Privado")), ("publico", _("Público"))],
        default="privado",
    )
    estado = SelectField(
        _("Estado"),
        choices=[
            ("draft", _("Borrador")),
            ("public", _("Publicado")),
            ("archived", _("Archivado")),
        ],
        default="draft",
    )
    etiquetas = StringField(
        _("Etiquetas (separadas por comas)"), validators=[Optional()]
    )
    descripcion_cambio = StringField(
        _("Descripción del cambio"), validators=[Optional(), Length(max=200)]
    )
    submit = SubmitField(_("Guardar"))


class UsuarioForm(FlaskForm):
    usuario = StringField(_("Usuario"), validators=[DataRequired(), Length(max=150)])
    nombre = StringField(_("Nombre"), validators=[Optional(), Length(max=100)])
    apellido = StringField(_("Apellido"), validators=[Optional(), Length(max=100)])
    correo_electronico = StringField(
        _("Correo electrónico"), validators=[Optional(), Email(), Length(max=150)]
    )
    tipo = SelectField(
        _("Rol"),
        choices=[
            ("admin", _("Administrador")),
            ("editor", _("Editor")),
            ("consulta", _("Consulta")),
        ],
        default="editor",
    )
    activo = BooleanField(_("Activo"), default=True)
    password = PasswordField(_("Contraseña"), validators=[Optional(), Length(min=6)])
    submit = SubmitField(_("Guardar"))


class GrupoForm(FlaskForm):
    nombre = StringField(_("Nombre"), validators=[DataRequired(), Length(max=100)])
    descripcion = TextAreaField(_("Descripción"), validators=[Optional()])
    usuario_ids = SelectMultipleField(
        _("Miembros"), validators=[Optional()], coerce=str
    )
    categoria_ids = SelectMultipleField(
        _("Categorías accesibles"), validators=[Optional()], coerce=str
    )
    submit = SubmitField(_("Guardar"))


class CategoriaForm(FlaskForm):
    nombre = StringField(_("Nombre"), validators=[DataRequired(), Length(max=100)])
    slug = StringField(_("Slug"), validators=[Optional(), Length(max=120)])
    icono = StringField(_("Ícono"), validators=[Optional(), Length(max=32)])
    color = StringField(_("Color"), validators=[Optional(), Length(max=20)])
    parent_id = SelectField(_("Categoría padre"), validators=[Optional()], coerce=str)
    grupo_ids = SelectMultipleField(
        _("Grupos con acceso"), validators=[Optional()], coerce=str
    )
    submit = SubmitField(_("Guardar"))


class EtiquetaForm(FlaskForm):
    nombre = StringField(_("Nombre"), validators=[DataRequired(), Length(max=50)])
    slug = StringField(_("Slug"), validators=[Optional(), Length(max=80)])
    icono = StringField(_("Ícono"), validators=[Optional(), Length(max=32)])
    color = StringField(_("Color"), validators=[Optional(), Length(max=20)])
    parent_id = SelectField(_("Etiqueta padre"), validators=[Optional()], coerce=str)
    submit = SubmitField(_("Guardar"))


class AppSettingsForm(FlaskForm):
    site_title = StringField(
        _("Título del sitio"), validators=[DataRequired(), Length(max=150)]
    )
    site_logo = FileField(_("Logo del sitio"))
    default_language = SelectField(
        _("Idioma por defecto"),
        choices=[("en", "English"), ("es", "Español")],
        default="en",
    )
    uploads_enabled = BooleanField(_("Permitir carga de archivos"), default=True)
    max_upload_size_mb = StringField(
        _("Tamaño máximo de archivos (MB)"),
        validators=[DataRequired(), Length(max=10)],
        default="10",
    )
    submit = SubmitField(_("Guardar configuración"))


class ProfileForm(FlaskForm):
    nombre = StringField(_("Nombre"), validators=[Optional(), Length(max=100)])
    apellido = StringField(_("Apellido"), validators=[Optional(), Length(max=100)])
    correo_electronico = StringField(
        _("Correo electrónico"), validators=[Optional(), Email(), Length(max=150)]
    )
    password = PasswordField(
        _("Nueva contraseña"), validators=[Optional(), Length(min=6)]
    )
    avatar = FileField(_("Imagen de perfil"))
    submit = SubmitField(_("Guardar perfil"))


class BusquedaForm(FlaskForm):
    q = StringField(_("Buscar"), validators=[Optional()])
    categoria_id = SelectField(_("Categoría"), validators=[Optional()], coerce=str)
    estado = SelectField(
        _("Estado"),
        choices=[
            ("", _("Todos")),
            ("draft", _("Borrador")),
            ("public", _("Publicado")),
            ("archived", _("Archivado")),
        ],
        default="",
    )
    etiqueta = StringField(_("Etiqueta"), validators=[Optional()])
    submit = SubmitField(_("Buscar"))


class PermisoForm(FlaskForm):
    usuario_id = SelectField(_("Usuario"), validators=[Optional()], coerce=str)
    grupo_id = SelectField(_("Grupo"), validators=[Optional()], coerce=str)
    tipo_permiso = SelectField(
        _("Permiso"),
        choices=[("lectura", _("Lectura")), ("edicion", _("Edición"))],
        default="lectura",
    )
    submit = SubmitField(_("Agregar permiso"))
