# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 BMO Soluciones, S.A.

from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.exc import OperationalError, ProgrammingError

from wanshitong import alembic, create_app
from wanshitong.model import Categoria, Etiqueta, db


def test_alembic_upgrade_app_context(tmp_path, monkeypatch):
    database_path = tmp_path / "alembic_roundtrip.db"
    database_url = f"sqlite:///{database_path.as_posix()}"

    monkeypatch.setenv("DATABASE_URL", database_url)

    app = create_app(
        {
            "SQLALCHEMY_DATABASE_URI": database_url,
            "TESTING": True,
            "SECRET_KEY": "test-secret",
            "WTF_CSRF_ENABLED": False,
        }
    )

    with app.app_context():
        db.drop_all()
        db.create_all()
        db.session.commit()

        # Si create_app dejó la BD en head, volvemos a base para validar el upgrade real.
        alembic.downgrade("base")
        db.session.commit()

        categoria = Categoria(
            nombre="clientes",
            slug="clientes",
            icono="📁",
            color="#0ea5e9",
        )
        etiqueta = Etiqueta(
            nombre="correo",
            slug="correo",
            icono="🏷️",
            color="#22c55e",
        )
        db.session.add_all([categoria, etiqueta])
        db.session.commit()

        alembic.upgrade()
        db.session.commit()

        categoria_upgraded = db.session.get(Categoria, categoria.id)
        etiqueta_upgraded = db.session.get(Etiqueta, etiqueta.id)
        assert categoria_upgraded is not None
        assert etiqueta_upgraded is not None
        assert categoria_upgraded.icono == "folder"
        assert etiqueta_upgraded.icono == "tag"

        version_after_upgrade = db.session.execute(text("SELECT version_num FROM alembic_version")).scalar()
        assert version_after_upgrade == "20260425_01"

        alembic.upgrade()
        db.session.commit()
        version_after_second_upgrade = db.session.execute(text("SELECT version_num FROM alembic_version")).scalar()
        assert version_after_second_upgrade == "20260425_01"

        alembic.downgrade("base")
        db.session.commit()
        db.session.expire_all()

        categoria_downgraded = db.session.get(Categoria, categoria.id)
        etiqueta_downgraded = db.session.get(Etiqueta, etiqueta.id)
        assert categoria_downgraded is not None
        assert etiqueta_downgraded is not None
        assert categoria_downgraded.icono == "📁"
        assert etiqueta_downgraded.icono == "🏷️"

        try:
            version_after_downgrade = db.session.execute(text("SELECT version_num FROM alembic_version")).scalar()
            assert version_after_downgrade is None
        except (OperationalError, ProgrammingError):
            pass

        alembic.upgrade()
        db.session.commit()
        db.session.expire_all()

        categoria_upgraded_again = db.session.get(Categoria, categoria.id)
        etiqueta_upgraded_again = db.session.get(Etiqueta, etiqueta.id)
        assert categoria_upgraded_again is not None
        assert etiqueta_upgraded_again is not None
        assert categoria_upgraded_again.icono == "folder"
        assert etiqueta_upgraded_again.icono == "tag"

        version_after_final_upgrade = db.session.execute(text("SELECT version_num FROM alembic_version")).scalar()
        assert version_after_final_upgrade == "20260425_01"
