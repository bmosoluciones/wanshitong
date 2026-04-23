# Copyright 2025 BMO Soluciones, S.A.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

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
