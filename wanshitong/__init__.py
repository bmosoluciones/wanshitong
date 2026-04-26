# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 BMO Soluciones, S.A.
"""
App
===

Minimal app package for template projects.
"""

from __future__ import annotations

from os import environ
from pathlib import Path
from platform import platform as os_platform
from sys import version as py_version

from flask import (
    Flask,
    abort,
    flash,
    jsonify,
    redirect,
    request,
    send_from_directory,
    session,
    url_for,
)
from flask_alembic import Alembic
from flask_babel import Babel
from flask_login import LoginManager, current_user
from flask_wtf.csrf import CSRFProtect
from sqlalchemy import inspect, text
from sqlalchemy.pool import StaticPool

from flask_session import Session
from wanshitong.acl import puede_acceder_categoria, puede_leer
from wanshitong.admin import admin
from wanshitong.app import app as app_blueprint
from wanshitong.auth import auth
from wanshitong.config import DIRECTORIO_ARCHIVOS_BASE, DIRECTORIO_PLANTILLAS_BASE
from wanshitong.documentos import documentos
from wanshitong.i18n import _
from wanshitong.icon_catalog import icon_picker_catalog, icon_to_css_class
from wanshitong.log import log
from wanshitong.model import Categoria, Documento, Usuario, db
from wanshitong.utils import (
    avatar_url,
    ensure_default_settings,
    get_setting,
    site_favicon_mime_type,
    site_favicon_url,
    site_logo_url,
)
from wanshitong.version import __version__

session_manager = Session()
login_manager = LoginManager()
babel = Babel()
csrf = CSRFProtect()
alembic = Alembic(run_mkdir=False, metadatas=db.metadata)

SUPPORTED_LOCALES = ("es", "en")
DEFAULT_LOCALE = "es"
APP_LICENSE = "Apache-2.0"
SOURCE_CODE_URL = "https://github.com/bmosoluciones/wanshitong"

EXPECTED_SCHEMA = {
    "usuario": {"theme_preference", "avatar_extension", "ultimo_acceso"},
    "categoria": {"slug", "icono", "color"},
    "etiqueta": {"slug", "icono", "color", "parent_id"},
    "documento": {"slug"},
}
EXPECTED_TABLES = {"categoria_grupo", "app_config"}


def _get_locale() -> str:
    """Resolve the active locale for the current request.

    Priority:
    1. ``lang`` query parameter (e.g. ``?lang=en``)
    2. ``lang`` key stored in the Flask session
    3. App setting ``default_language``
    4. Best match from the browser's ``Accept-Language`` header
    5. App default locale
    """
    # 1. Explicit query parameter
    lang = request.args.get("lang")
    if lang in SUPPORTED_LOCALES:
        session["lang"] = lang
        return lang

    # 2. Previously stored in session
    if session.get("lang") in SUPPORTED_LOCALES:
        return session["lang"]

    # 3. App-level default language
    configured = get_setting("default_language", DEFAULT_LOCALE)
    if configured in SUPPORTED_LOCALES:
        return configured

    # 4. Browser header
    best = request.accept_languages.best_match(SUPPORTED_LOCALES)
    if best:
        return best

    return DEFAULT_LOCALE


@login_manager.user_loader
def cargar_sesion(identidad):
    if identidad is not None:
        return db.session.get(Usuario, identidad)
    return None


@login_manager.unauthorized_handler
def no_autorizado():
    flash(str(_("Favor iniciar sesión para acceder al sistema.")), "warning")
    return redirect(url_for("auth.login"))


def create_app(config) -> Flask:
    from wanshitong.config import configuration as default_conf

    app = Flask(
        __name__,
        static_folder=DIRECTORIO_ARCHIVOS_BASE,
        template_folder=DIRECTORIO_PLANTILLAS_BASE,
    )

    if config:
        app.config.from_mapping(config)
    else:
        app.config.from_object(default_conf)

    app.config.setdefault("APP_DEFAULT_LOCALE", DEFAULT_LOCALE)
    app.config.setdefault("APP_SITE_TITLE", "WanShiTong")
    app.config.setdefault("UPLOADS_ENABLED", True)
    app.config.setdefault("MAX_UPLOAD_SIZE_MB", 10)
    app.config.setdefault("AUTO_REBUILD_SCHEMA", not app.config.get("TESTING", False))
    app.config.setdefault("UPLOADS_ROOT", Path(app.root_path).parent / "data" / "uploads")

    db_uri = str(app.config.get("SQLALCHEMY_DATABASE_URI", ""))
    if app.config.get("TESTING") and db_uri.startswith("sqlite") and ":memory:" in db_uri:
        engine_options = dict(app.config.get("SQLALCHEMY_ENGINE_OPTIONS") or {})
        engine_options.setdefault("poolclass", StaticPool)
        connect_args = dict(engine_options.get("connect_args") or {})
        connect_args.setdefault("check_same_thread", False)
        engine_options["connect_args"] = connect_args
        app.config["SQLALCHEMY_ENGINE_OPTIONS"] = engine_options

    log.info("create_app: initializing app")
    db.init_app(app)
    alembic.init_app(app)

    try:
        log.info(f"create_app: SQLALCHEMY_DATABASE_URI = {app.config.get('SQLALCHEMY_DATABASE_URI')}")
    except Exception:
        log.warning("create_app: could not read SQLALCHEMY_DATABASE_URI from wanshitong.config")

    try:
        log.warning("create_app: calling ensure_database_initialized")
        ensure_database_initialized(app)
        log.info("create_app: ensure_database_initialized completed")
    except Exception as exc:
        log.warning(f"create_app: ensure_database_initialized raised: {exc}")
        try:
            log.exception("create_app: ensure_database_initialized exception")
        except Exception:
            pass

    if app.config.get("TESTING"):
        app.config["SESSION_TYPE"] = "filesystem"
        app.config["SESSION_PERMANENT"] = False
        app.config["SESSION_USE_SIGNER"] = True
    elif session_redis_url := environ.get("SESSION_REDIS_URL", None):
        from redis import Redis

        app.config["SESSION_TYPE"] = "redis"
        app.config["SESSION_REDIS"] = Redis.from_url(session_redis_url)
    else:
        app.config["SESSION_TYPE"] = "sqlalchemy"
        app.config["SESSION_SQLALCHEMY"] = db
        app.config["SESSION_SQLALCHEMY_TABLE"] = "sessions"
        app.config["SESSION_PERMANENT"] = False
        app.config["SESSION_USE_SIGNER"] = True

    app.config.setdefault("BABEL_DEFAULT_LOCALE", app.config["APP_DEFAULT_LOCALE"])
    app.config.setdefault("BABEL_SUPPORTED_LOCALES", list(SUPPORTED_LOCALES))
    app.config.setdefault("BABEL_TRANSLATION_DIRECTORIES", str(Path(app.root_path) / "translations"))

    babel.init_app(app, locale_selector=_get_locale)
    session_manager.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)

    # Expose get_locale in all templates
    from flask_babel import get_locale as _flask_get_locale

    @app.context_processor
    def inject_locale():
        nav_spaces = []
        if getattr(current_user, "is_authenticated", False):
            current_doc_id = (request.view_args or {}).get("doc_id")
            current_category_id = request.args.get("categoria_id")
            categorias = db.session.execute(db.select(Categoria).order_by(Categoria.nombre)).scalars().all()
            documentos = (
                db.session.execute(
                    db.select(Documento).where(Documento.estado != "archived").order_by(Documento.titulo)
                )
                .scalars()
                .all()
            )
            by_parent: dict[str | None, list[Categoria]] = {}
            docs_by_category: dict[str | None, list[Documento]] = {}
            for categoria in categorias:
                by_parent.setdefault(categoria.parent_id, []).append(categoria)

            for documento in documentos:
                if puede_leer(documento, current_user):
                    docs_by_category.setdefault(documento.categoria_id, []).append(documento)

            def build_doc_node(documento: Documento) -> dict:
                is_active = current_doc_id == documento.id
                return {
                    "kind": "document",
                    "id": documento.id,
                    "label": documento.titulo,
                    "url": url_for("documentos.ver", doc_id=documento.id),
                    "children": [],
                    "is_active": is_active,
                    "is_open": is_active,
                    "is_space": False,
                    "badge": None,
                    "color": None,
                }

            def build_space_tree(parent_id: str | None, depth: int = 0) -> list[dict]:
                result: list[dict] = []
                for categoria in sorted(by_parent.get(parent_id, []), key=lambda c: c.nombre):
                    child_nodes = build_space_tree(categoria.id, depth + 1)
                    document_nodes = [build_doc_node(documento) for documento in docs_by_category.get(categoria.id, [])]
                    if not puede_acceder_categoria(categoria, current_user):
                        if not child_nodes and not document_nodes:
                            continue
                    category_is_active = request.endpoint == "documentos.lista" and current_category_id == categoria.id
                    has_active_descendant = any(
                        child["is_active"] or child["is_open"] for child in child_nodes + document_nodes
                    )
                    result.append(
                        {
                            "kind": "category",
                            "id": categoria.id,
                            "label": categoria.nombre,
                            "url": url_for("documentos.lista", categoria_id=categoria.id),
                            "children": child_nodes + document_nodes,
                            "is_active": category_is_active,
                            "is_open": depth == 0 or category_is_active or has_active_descendant,
                            "is_space": depth == 0,
                            "icon_class": icon_to_css_class(categoria.icono, fallback="folder"),
                            "icon_color": categoria.color or "#6b7280",
                        }
                    )
                return result

            nav_spaces = build_space_tree(None)
            nav_spaces.extend(build_doc_node(documento) for documento in docs_by_category.get(None, []))
        return {
            "get_locale": _flask_get_locale,
            "site_title": get_setting("site_title", app.config["APP_SITE_TITLE"]),
            "site_logo_url": site_logo_url(),
            "site_favicon_url": site_favicon_url(),
            "site_favicon_mime_type": site_favicon_mime_type(),
            "app_name": "Wanshitong",
            "app_version": __version__,
            "app_license": APP_LICENSE,
            "app_source_url": SOURCE_CODE_URL,
            "current_theme": (
                current_user.theme_preference
                if getattr(current_user, "is_authenticated", False) and getattr(current_user, "theme_preference", None)
                else "light"
            ),
            "current_avatar_url": (
                avatar_url(current_user) if getattr(current_user, "is_authenticated", False) else None
            ),
            "nav_spaces": nav_spaces,
            "icon_picker_catalog": icon_picker_catalog(),
        }

    @app.route("/health")
    def health_check():
        return jsonify({"status": "ok"}), 200

    @app.route("/ready")
    def readiness_check():
        try:
            db.session.execute(text("SELECT 1"))
        except Exception:
            db.session.rollback()
            return (
                jsonify(
                    {
                        "status": "not-ready",
                        "database": "unreachable",
                        "python": py_version.split()[0],
                        "os": os_platform(),
                    }
                ),
                503,
            )

        return (
            jsonify(
                {
                    "status": "ready",
                    "database": "ok",
                    "python": py_version.split()[0],
                    "os": os_platform(),
                }
            ),
            200,
        )

    @app.before_request
    def require_login_by_default():
        if request.endpoint is None:
            return None
        if request.endpoint == "static":
            return None
        if request.endpoint in {"health_check", "readiness_check"}:
            return None
        if request.endpoint.startswith("auth.") and request.endpoint == "auth.login":
            return None
        if request.endpoint in {"media_avatar", "media_document", "media_site_logo"}:
            if getattr(current_user, "is_authenticated", False):
                return None
            if request.endpoint == "media_site_logo":
                return None
        if not getattr(current_user, "is_authenticated", False):
            return redirect(url_for("auth.login", next=request.path))
        return None

    @app.route("/media/avatars/<path:filename>")
    def media_avatar(filename: str):
        return send_from_directory(Path(app.config["UPLOADS_ROOT"]) / "avatars", filename)

    @app.route("/media/site/<path:filename>")
    def media_site_logo(filename: str):
        return send_from_directory(Path(app.config["UPLOADS_ROOT"]) / "site", filename)

    @app.route("/media/documents/<doc_id>/<path:filename>")
    def media_document(doc_id: str, filename: str):
        doc = db.session.get(Documento, doc_id)
        if doc is None:
            abort(404)
        if not getattr(current_user, "is_authenticated", False):
            return redirect(url_for("auth.login"))
        if not puede_leer(doc, current_user):
            abort(403)
        return send_from_directory(Path(app.config["UPLOADS_ROOT"]) / "documents" / doc_id, filename)

    app.register_blueprint(auth, url_prefix="")
    app.register_blueprint(app_blueprint, url_prefix="/")
    app.register_blueprint(documentos, url_prefix="/d")
    app.register_blueprint(admin, url_prefix="/a")

    return app


def ensure_database_initialized(app: Flask | None = None) -> None:
    from os import environ as _environ

    from wanshitong.auth import proteger_passwd as _proteger_passwd
    from wanshitong.model import Usuario
    from wanshitong.model import db as _db

    ctx = app
    if ctx is None:
        from flask import current_app

        ctx = current_app

    with ctx.app_context():
        try:
            try:
                log.warning(f"ensure_database_initialized: engine.url = {_db.engine.url}")
            except Exception:
                log.warning("ensure_database_initialized: could not read _db.engine.url")

            try:
                db_uri = ctx.config.get("SQLALCHEMY_DATABASE_URI")
                log.warning(f"ensure_database_initialized: Flask SQLALCHEMY_DATABASE_URI = {db_uri}")
            except Exception:
                log.warning("ensure_database_initialized: could not read SQLALCHEMY_DATABASE_URI from ctx.config")

            log.warning("ensure_database_initialized: calling create_all()")
            _db.create_all()
            log.info("ensure_database_initialized: create_all() completed")
            ensure_default_settings()
            _db.session.commit()
            log.warning("ensure_database_initialized: applying migrations with Flask-Alembic upgrade()")
            alembic.upgrade()
            log.info("ensure_database_initialized: migrations applied")
        except Exception as exc:
            log.warning(f"ensure_database_initialized: create_all() raised: {exc}")
            try:
                log.exception("ensure_database_initialized: create_all() exception")
            except Exception:
                pass

        registro_admin = _db.session.execute(_db.select(Usuario).filter_by(tipo="admin")).scalars().first()

        if registro_admin is None:
            admin_user = _environ.get("ADMIN_USER", "app-admin")
            admin_pass = _environ.get("ADMIN_PASSWORD", "app-admin")
            user_source = "env" if "ADMIN_USER" in _environ else "default"
            pass_source = "env" if "ADMIN_PASSWORD" in _environ else "default"
            log.warning(
                "ensure_database_initialized: no admin user found, creating initial admin "
                f"username='{admin_user}' (ADMIN_USER={user_source}, ADMIN_PASSWORD={pass_source})"
            )

            nuevo = Usuario()
            nuevo.usuario = admin_user
            nuevo.acceso = _proteger_passwd(admin_pass)
            nuevo.nombre = "Administrador"
            nuevo.apellido = ""
            nuevo.correo_electronico = None
            nuevo.tipo = "admin"
            nuevo.activo = True

            _db.session.add(nuevo)
            _db.session.commit()
            log.warning(f"ensure_database_initialized: initial admin user '{admin_user}' created")
        else:
            log.info(
                "ensure_database_initialized: admin user already exists; "
                f"seed skipped (usuario='{registro_admin.usuario}')"
            )


def _schema_reset_required(app: Flask) -> bool:
    if app.config.get("TESTING"):
        return False
    if not app.config.get("AUTO_REBUILD_SCHEMA", True):
        return False

    inspector = inspect(db.engine)
    table_names = set(inspector.get_table_names())

    if not table_names:
        return False

    if EXPECTED_TABLES - table_names:
        return True

    for table_name, expected_columns in EXPECTED_SCHEMA.items():
        if table_name not in table_names:
            return True
        existing_columns = {column["name"] for column in inspector.get_columns(table_name)}
        if expected_columns - existing_columns:
            return True

    return False
