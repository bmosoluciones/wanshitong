"""remove_user_level_permissions

Revision ID: 20260512_03
Revises: 20260426_02
Create Date: 2026-05-12 21:00:00

"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "20260512_03"
down_revision = "20260426_02"
branch_labels = None
depends_on = None

def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = [c["name"] for c in inspector.get_columns("permiso_documento")]

    if "usuario_id" in columns:
        with op.batch_alter_table("permiso_documento", schema=None) as batch_op:
            batch_op.drop_column("usuario_id")

def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = [c["name"] for c in inspector.get_columns("permiso_documento")]

    if "usuario_id" not in columns:
        with op.batch_alter_table("permiso_documento", schema=None) as batch_op:
            batch_op.add_column(sa.Column("usuario_id", sa.String(length=26), nullable=True))
            batch_op.create_foreign_key(
                "fk_permiso_documento_usuario_id_usuario",
                "usuario",
                ["usuario_id"],
                ["id"]
            )
