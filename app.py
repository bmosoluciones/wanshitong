# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 BMO Soluciones, S.A.

# <-------------------------------------------------------------------------> #
# Standard library
# <-------------------------------------------------------------------------> #

# <-------------------------------------------------------------------------> #
# Third party libraries
# <-------------------------------------------------------------------------> #

# <-------------------------------------------------------------------------> #
# Local modules
# <-------------------------------------------------------------------------> #
from os import environ
from pathlib import Path

# Asegurar que por defecto use un archivo sqlite en la raíz del repositorio
# llamado `app.db` si no se suministra `DATABASE_URL`.
repo_root = Path(__file__).resolve().parent
default_db_path = repo_root.joinpath("app.db")
default_db_uri = f"sqlite:///{default_db_path}"
# For development use repo-root `app.db` only if DATABASE_URL was not provided.
environ.setdefault("DATABASE_URL", default_db_uri)

from wanshitong import create_app, ensure_database_initialized
from wanshitong.log import log
from wanshitong.config import configuration

# ---------------------------------------------------------------------------------------
# Crear aplicación.
# ---------------------------------------------------------------------------------------
app = create_app(configuration)
log.trace("app module: application instance created")


# ---------------------------------------------------------------------------------------
# Servidor predefinido.
# ---------------------------------------------------------------------------------------
def serve():
    from waitress import serve

    # Asegura que la base de datos esté inicializada y exista un administrador.
    try:
        log.trace("serve: ensuring database initialized")
        log.trace(
            f"serve: Flask SQLALCHEMY_DATABASE_URI = {app.config.get('SQLALCHEMY_DATABASE_URI')}"
        )
        ensure_database_initialized(app)
        log.trace("serve: ensure_database_initialized completed")
    except Exception as exc:
        log.trace(f"serve: ensure_database_initialized raised: {exc}")
        try:
            log.exception("serve: ensure_database_initialized exception")
        except Exception:
            pass

    port = int(environ.get("PORT", "8080"))
    log.trace(f"serve: starting waitress on 0.0.0.0:{port}")
    serve(app, host="0.0.0.0", port=port)


if __name__ == "__main__":
    serve()
