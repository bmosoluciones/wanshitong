"""Add editable deployment identity settings.

Revision ID: 20260919_04
Revises: 20260512_03
Create Date: 2026-09-19 00:00:00
"""

from __future__ import annotations

from datetime import date, datetime, timezone

import sqlalchemy as sa
from alembic import op

revision = "20260919_04"
down_revision = "20260512_03"
branch_labels = None
depends_on = None

SETTINGS = (
    ("01K5H000000000000000000001", "operator_name", "BMO Soluciones, S.A."),
    (
        "01K5H000000000000000000002",
        "security_contact",
        "https://github.com/bmosoluciones/wanshitong/security/advisories/new",
    ),
    ("01K5H000000000000000000003", "public_origin", ""),
)


def upgrade() -> None:
    bind = op.get_bind()
    now = datetime.now(timezone.utc)
    today = date.today()
    for setting_id, key, value in SETTINGS:
        exists = bind.execute(
            sa.text("SELECT 1 FROM app_config WHERE clave = :key"), {"key": key}
        ).scalar()
        if exists:
            continue
        bind.execute(
            sa.text(
                """
                INSERT INTO app_config
                    (id, timestamp, creado, creado_por, clave, valor, tipo, descripcion)
                VALUES
                    (:id, :timestamp, :created, :created_by, :key, :value, 'string', :description)
                """
            ),
            {
                "id": setting_id,
                "timestamp": now,
                "created": today,
                "created_by": "migration:20260919_04",
                "key": key,
                "value": value,
                "description": "Editable deployment identity setting",
            },
        )


def downgrade() -> None:
    bind = op.get_bind()
    bind.execute(
        sa.text(
            """
            DELETE FROM app_config
            WHERE clave IN ('operator_name', 'security_contact', 'public_origin')
              AND creado_por = 'migration:20260919_04'
            """
        )
    )
