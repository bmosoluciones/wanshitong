# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 BMO Soluciones, S.A.

"""Data model for the app package."""

from __future__ import annotations

from datetime import date, datetime, timezone

from flask_login import UserMixin
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase
from ulid import ULID


class Base(DeclarativeBase):
    pass


db = SQLAlchemy(model_class=Base)
database = db


def generador_de_codigos_unicos() -> str:
    codigo_aleatorio = ULID()
    id_unico = str(codigo_aleatorio)
    return id_unico


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class BaseTabla:
    id = database.Column(
        database.String(26),
        primary_key=True,
        nullable=False,
        index=True,
        default=generador_de_codigos_unicos,
    )
    timestamp = database.Column(database.DateTime, default=utc_now, nullable=False)
    creado = database.Column(database.Date, default=date.today, nullable=False)
    creado_por = database.Column(database.String(150), nullable=True)
    modificado = database.Column(database.DateTime, onupdate=utc_now, nullable=True)
    modificado_por = database.Column(database.String(150), nullable=True)


# Association table: Usuario <-> Grupo
usuario_grupo = database.Table(
    "usuario_grupo",
    database.Column(
        "usuario_id",
        database.String(26),
        database.ForeignKey("usuario.id"),
        primary_key=True,
    ),
    database.Column(
        "grupo_id",
        database.String(26),
        database.ForeignKey("grupo.id"),
        primary_key=True,
    ),
)

# Association table: Documento <-> Etiqueta
documento_etiqueta = database.Table(
    "documento_etiqueta",
    database.Column(
        "documento_id",
        database.String(26),
        database.ForeignKey("documento.id"),
        primary_key=True,
    ),
    database.Column(
        "etiqueta_id",
        database.String(26),
        database.ForeignKey("etiqueta.id"),
        primary_key=True,
    ),
)

# Association table: Categoria <-> Grupo
categoria_grupo = database.Table(
    "categoria_grupo",
    database.Column(
        "categoria_id",
        database.String(26),
        database.ForeignKey("categoria.id"),
        primary_key=True,
    ),
    database.Column(
        "grupo_id",
        database.String(26),
        database.ForeignKey("grupo.id"),
        primary_key=True,
    ),
)


class Usuario(UserMixin, database.Model, BaseTabla):
    __tablename__ = "usuario"
    __table_args__ = (
        database.UniqueConstraint("usuario", name="id_usuario_unico"),
        database.UniqueConstraint("correo_electronico", name="correo_usuario_unico"),
    )

    usuario = database.Column(database.String(150), nullable=False, index=True, unique=True)
    acceso = database.Column(database.LargeBinary(), nullable=False)
    nombre = database.Column(database.String(100))
    apellido = database.Column(database.String(100))
    correo_electronico = database.Column(database.String(150))
    correo_electronico_verificado = database.Column(database.Boolean(), default=False)
    tipo = database.Column(database.String(20))  # admin / editor / consulta
    activo = database.Column(database.Boolean(), default=True)
    ultimo_acceso = database.Column(database.DateTime, nullable=True)
    theme_preference = database.Column(database.String(10), default="light")
    avatar_extension = database.Column(database.String(10), nullable=True)

    grupos = database.relationship("Grupo", secondary=usuario_grupo, back_populates="usuarios")
    documentos = database.relationship("Documento", back_populates="autor", foreign_keys="Documento.autor_id")


class Grupo(database.Model, BaseTabla):
    __tablename__ = "grupo"

    nombre = database.Column(database.String(100), nullable=False, unique=True)
    descripcion = database.Column(database.Text, nullable=True)

    usuarios = database.relationship("Usuario", secondary=usuario_grupo, back_populates="grupos")
    categorias = database.relationship("Categoria", secondary=categoria_grupo, back_populates="grupos")


class Categoria(database.Model, BaseTabla):
    __tablename__ = "categoria"

    nombre = database.Column(database.String(100), nullable=False)
    slug = database.Column(database.String(120), nullable=True, unique=True, index=True)
    icono = database.Column(database.String(32), nullable=True)
    color = database.Column(database.String(20), nullable=True)
    parent_id = database.Column(database.String(26), database.ForeignKey("categoria.id"), nullable=True)

    subcategorias = database.relationship("Categoria", backref=database.backref("parent", remote_side="Categoria.id"))
    documentos = database.relationship("Documento", back_populates="categoria")
    grupos = database.relationship("Grupo", secondary=categoria_grupo, back_populates="categorias")


class Etiqueta(database.Model, BaseTabla):
    __tablename__ = "etiqueta"

    nombre = database.Column(database.String(50), nullable=False, unique=True)
    slug = database.Column(database.String(80), nullable=True, unique=True, index=True)
    icono = database.Column(database.String(32), nullable=True)
    color = database.Column(database.String(20), nullable=True)
    parent_id = database.Column(database.String(26), database.ForeignKey("etiqueta.id"), nullable=True)

    subetiquetas = database.relationship("Etiqueta", backref=database.backref("parent", remote_side="Etiqueta.id"))


class Documento(database.Model, BaseTabla):
    __tablename__ = "documento"

    titulo = database.Column(database.String(200), nullable=False)
    slug = database.Column(database.String(240), nullable=True, unique=True, index=True)
    contenido = database.Column(database.Text, nullable=False, default="")
    autor_id = database.Column(database.String(26), database.ForeignKey("usuario.id"), nullable=False)
    categoria_id = database.Column(database.String(26), database.ForeignKey("categoria.id"), nullable=True)
    estado = database.Column(database.String(20), default="draft", nullable=False)  # draft / public / archived
    visibilidad = database.Column(database.String(20), default="privado", nullable=False)  # publico / privado
    numero_version = database.Column(database.Integer, default=1, nullable=False)
    estado_cambiado_en = database.Column(database.DateTime, nullable=True)
    estado_cambiado_por_id = database.Column(database.String(26), database.ForeignKey("usuario.id"), nullable=True)

    autor = database.relationship("Usuario", back_populates="documentos", foreign_keys=[autor_id])
    estado_cambiado_por = database.relationship("Usuario", foreign_keys=[estado_cambiado_por_id])
    categoria = database.relationship("Categoria", back_populates="documentos")
    etiquetas = database.relationship("Etiqueta", secondary=documento_etiqueta, backref="documentos")
    permisos = database.relationship("PermisoDocumento", back_populates="documento", cascade="all, delete-orphan")
    versiones = database.relationship(
        "VersionDocumento",
        back_populates="documento",
        cascade="all, delete-orphan",
        order_by="VersionDocumento.numero_version.desc()",
    )


class PermisoDocumento(database.Model, BaseTabla):
    __tablename__ = "permiso_documento"

    documento_id = database.Column(database.String(26), database.ForeignKey("documento.id"), nullable=False)
    usuario_id = database.Column(database.String(26), database.ForeignKey("usuario.id"), nullable=True)
    grupo_id = database.Column(database.String(26), database.ForeignKey("grupo.id"), nullable=True)
    tipo_permiso = database.Column(database.String(20), nullable=False)  # lectura / edicion

    documento = database.relationship("Documento", back_populates="permisos")
    usuario = database.relationship("Usuario")
    grupo = database.relationship("Grupo")


class VersionDocumento(database.Model, BaseTabla):
    __tablename__ = "version_documento"

    documento_id = database.Column(database.String(26), database.ForeignKey("documento.id"), nullable=False)
    titulo = database.Column(database.String(200), nullable=False)
    contenido = database.Column(database.Text, nullable=False)
    numero_version = database.Column(database.Integer, nullable=False)
    modificado_por_id = database.Column(database.String(26), database.ForeignKey("usuario.id"), nullable=True)
    descripcion_cambio = database.Column(database.String(200), nullable=True)

    documento = database.relationship("Documento", back_populates="versiones")
    modificado_por = database.relationship("Usuario")


class AppConfig(database.Model, BaseTabla):
    __tablename__ = "app_config"
    __table_args__ = (database.UniqueConstraint("clave", name="app_config_clave_unica"),)

    clave = database.Column(database.String(100), nullable=False, unique=True, index=True)
    valor = database.Column(database.Text, nullable=True)
    tipo = database.Column(database.String(20), nullable=False, default="string")
    descripcion = database.Column(database.String(255), nullable=True)
