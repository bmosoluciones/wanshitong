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

from wanshitong import create_app, ensure_database_initialized
from wanshitong.log import log
from wanshitong.config import configuration

# ---------------------------------------------------------------------------------------
# Crear aplicación.
# ---------------------------------------------------------------------------------------
app = create_app(configuration)
log.info("app module: application instance created")


# ---------------------------------------------------------------------------------------
# Servidor predefinido.
# ---------------------------------------------------------------------------------------
def serve():
    from waitress import serve

    # Asegura que la base de datos esté inicializada y exista un administrador.
    try:
        log.warning("serve: ensuring database initialized")
        log.warning(
            "serve: env presence "
            f"DATABASE_URL={'yes' if 'DATABASE_URL' in environ else 'no'}, "
            f"ADMIN_USER={'yes' if 'ADMIN_USER' in environ else 'no'}, "
            f"ADMIN_PASSWORD={'yes' if 'ADMIN_PASSWORD' in environ else 'no'}"
        )
        log.warning(
            f"serve: Flask SQLALCHEMY_DATABASE_URI = {app.config.get('SQLALCHEMY_DATABASE_URI')}"
        )
        ensure_database_initialized(app)
        log.info("serve: ensure_database_initialized completed")
    except Exception as exc:
        log.warning(f"serve: ensure_database_initialized raised: {exc}")
        try:
            log.exception("serve: ensure_database_initialized exception")
        except Exception:
            pass

    port = int(environ.get("PORT", "9099"))
    log.warning(f"serve: starting waitress on 0.0.0.0:{port}")
    serve(app, host="0.0.0.0", port=port)


if __name__ == "__main__":
    serve()
