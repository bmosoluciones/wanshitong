# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 BMO Soluciones, S.A.

"""Base configuration for the app package."""

from __future__ import annotations

from os import environ, getcwd, path, sys
from pathlib import Path
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

from wanshitong.log import log


def load_config_from_file() -> dict:
    try:
        from configobj import ConfigObj
    except ImportError:
        log.debug("ConfigObj not available, skipping file-based configuration.")
        return {}

    search_paths = [
        "/etc/app/app.conf",
        "/etc/app.conf",
        path.expanduser("~/.config/app/app.conf"),
        path.join(getcwd(), "app.conf"),
    ]

    for config_path in search_paths:
        if config_path and path.isfile(config_path):
            try:
                log.info(f"Loading configuration from file: {config_path}")
                config_obj = ConfigObj(config_path, encoding="utf-8")
                config_dict = dict(config_obj)

                if "DATABASE_URL" in config_dict:
                    config_dict["SQLALCHEMY_DATABASE_URI"] = config_dict["DATABASE_URL"]

                if "REDIS_URL" in config_dict:
                    config_dict["CACHE_REDIS_URL"] = config_dict["REDIS_URL"]

                return config_dict
            except Exception as e:
                log.warning(f"Error loading configuration from {config_path}: {e}")
                continue

    log.trace("No configuration file found in search paths.")
    return {}


VALORES_TRUE = {*["1", "true", "yes", "on"], *["development", "dev"]}
DEBUG_VARS = ["DEBUG", "CI", "DEV", "DEVELOPMENT"]
FRAMEWORK_VARS = ["FLASK_ENV", "DJANGO_DEBUG", "NODE_ENV"]
GENERIC_VARS = ["ENV", "APP_ENV"]

DESARROLLO = any(
    str(environ.get(var, "")).strip().lower() in VALORES_TRUE for var in [*DEBUG_VARS, *FRAMEWORK_VARS, *GENERIC_VARS]
)

DIRECTORIO_ACTUAL: Path = Path(path.abspath(path.dirname(__file__)))
DIRECTORIO_APP: Path = DIRECTORIO_ACTUAL.parent.absolute()
DIRECTORIO_DESARROLLO: Path = DIRECTORIO_APP
DIRECTORIO_PLANTILLAS_BASE: str = path.join(DIRECTORIO_ACTUAL, "templates")
DIRECTORIO_ARCHIVOS_BASE: str = path.join(DIRECTORIO_ACTUAL, "static")

custom_data_dir = environ.get("NOW_LMS_DATA_DIR")
if custom_data_dir:
    log.trace("Data directory configuration found in environment variables.")
    DIRECTORIO_ARCHIVOS = custom_data_dir
else:
    DIRECTORIO_ARCHIVOS = DIRECTORIO_ARCHIVOS_BASE

custom_themes_dir = environ.get("NOW_LMS_THEMES_DIR")
if custom_themes_dir:
    log.trace("Themes directory configuration found in environment variables.")
    DIRECTORIO_PLANTILLAS = custom_themes_dir
else:
    DIRECTORIO_PLANTILLAS = DIRECTORIO_PLANTILLAS_BASE

DIRECTORIO_BASE_UPLOADS = Path(str(path.join(str(DIRECTORIO_ARCHIVOS), "files")))

TESTING = (
    "PYTEST_CURRENT_TEST" in environ
    or "PYTEST_VERSION" in environ
    or "TESTING" in environ
    or hasattr(sys, "_called_from_test")
    or environ.get("CI")
    or "pytest" in sys.modules
    or path.basename(sys.argv[0]) in ["pytest", "py.test"]
)

if TESTING:
    SQLITE: str = "sqlite:///:memory:"
else:
    sqlite_file = DIRECTORIO_DESARROLLO.joinpath("app.db")
    SQLITE = f"sqlite:///{sqlite_file.as_posix()}"

CONFIGURACION: dict[str, str | bool | Path] = {}
CONFIGURACION["SECRET_KEY"] = environ.get("SECRET_KEY") or "dev"

if not DESARROLLO and CONFIGURACION["SECRET_KEY"] == "dev":
    log.warning("Using default SECRET_KEY in production! This will can cause issues ")

CONFIGURACION["SQLALCHEMY_DATABASE_URI"] = environ.get("DATABASE_URL") or SQLITE
CONFIGURACION["PRESERVE_CONTEXT_ON_EXCEPTION"] = False

if DESARROLLO:
    log.warning("Using default configuration.")
    log.info("Default configuration is not recommended for use in production environments.")
    CONFIGURACION["SQLALCHEMY_TRACK_MODIFICATIONS"] = "False"
    CONFIGURACION["TEMPLATES_AUTO_RELOAD"] = True

if DATABASE_URL_BASE := CONFIGURACION.get("SQLALCHEMY_DATABASE_URI"):
    DATABASE_URL_CORREGIDA = DATABASE_URL_BASE
    prefix = DATABASE_URL_BASE.split(":", 1)[0]

    if environ.get("DYNO") and prefix in ("postgres", "postgresql"):
        parsed = urlparse(DATABASE_URL_BASE)
        query = parse_qs(parsed.query)
        query["sslmode"] = ["require"]
        DATABASE_URL_CORREGIDA = urlunparse(parsed._replace(scheme="postgresql", query=urlencode(query, doseq=True)))
    else:
        match prefix:
            case "postgresql":
                DATABASE_URL_CORREGIDA = "postgresql+pg8000" + DATABASE_URL_BASE[10:]
            case "postgres":
                DATABASE_URL_CORREGIDA = "postgresql+pg8000" + DATABASE_URL_BASE[8:]
            case "mysql":
                DATABASE_URL_CORREGIDA = "mysql+pymysql" + DATABASE_URL_BASE[5:]
            case "mariadb":
                DATABASE_URL_CORREGIDA = "mariadb+mariadbconnector" + DATABASE_URL_BASE[7:]
            case _:
                pass

    if DATABASE_URL_BASE != DATABASE_URL_CORREGIDA:
        log.info(f"Database URI corrected: {DATABASE_URL_BASE} → {DATABASE_URL_CORREGIDA}")
        CONFIGURACION["SQLALCHEMY_DATABASE_URI"] = DATABASE_URL_CORREGIDA

configuration = CONFIGURACION
