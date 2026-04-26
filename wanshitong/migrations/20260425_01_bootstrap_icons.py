"""Migrate legacy emoji icons to bootstrap icon names.

Revision ID: 20260425_01
Revises:
Create Date: 2026-04-25 00:00:00

"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "20260425_01"
down_revision = None
branch_labels = None
depends_on = None

LEGACY_EMOJI_TO_BOOTSTRAP = {
    "📁": "folder",
    "🏛️": "building",
    "📊": "bar-chart-line",
    "🧩": "diagram-3",
    "🔐": "lock",
    "🧠": "lightbulb",
    "⚙️": "gear",
    "🛠️": "gear",
    "💼": "bag",
    "📚": "book",
    "🏷️": "tag",
    "📌": "pin",
    "🔥": "exclamation-octagon",
    "🧪": "bug",
    "🧱": "braces",
    "🚀": "send",
    "✅": "list-check",
    "📝": "pencil",
    "📎": "paperclip",
    "🔖": "bookmark",
    "🔓": "unlock",
    "✈️": "airplane",
    "🏠": "house",
    "📧": "envelope",
    "💰": "cash-coin",
    "💖": "heart",
}


def _migrate_table(table_name: str, entity_type: str) -> None:
    bind = op.get_bind()
    rows = bind.execute(sa.text(f"SELECT id, icono FROM {table_name} WHERE icono IS NOT NULL")).mappings().all()

    for row in rows:
        old_icon = (row["icono"] or "").strip()
        new_icon = LEGACY_EMOJI_TO_BOOTSTRAP.get(old_icon)
        if not new_icon or new_icon == old_icon:
            continue

        bind.execute(
            sa.text("""
                INSERT INTO icon_migration_backup(entity_type, entity_id, old_icon, new_icon)
                VALUES (:entity_type, :entity_id, :old_icon, :new_icon)
                """),
            {
                "entity_type": entity_type,
                "entity_id": row["id"],
                "old_icon": old_icon,
                "new_icon": new_icon,
            },
        )
        bind.execute(
            sa.text(f"UPDATE {table_name} SET icono = :new_icon WHERE id = :entity_id"),
            {"new_icon": new_icon, "entity_id": row["id"]},
        )


def upgrade() -> None:
    op.create_table(
        "icon_migration_backup",
        sa.Column("entity_type", sa.String(length=20), nullable=False),
        sa.Column("entity_id", sa.String(length=26), nullable=False),
        sa.Column("old_icon", sa.String(length=32), nullable=False),
        sa.Column("new_icon", sa.String(length=32), nullable=False),
        sa.PrimaryKeyConstraint("entity_type", "entity_id", name="pk_icon_migration_backup"),
    )

    _migrate_table("categoria", "categoria")
    _migrate_table("etiqueta", "etiqueta")


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if not inspector.has_table("icon_migration_backup"):
        return

    rows = bind.execute(sa.text("""
            SELECT entity_type, entity_id, old_icon
            FROM icon_migration_backup
            ORDER BY entity_type, entity_id
            """)).mappings().all()

    for row in rows:
        table_name = "categoria" if row["entity_type"] == "categoria" else "etiqueta"
        bind.execute(
            sa.text(f"UPDATE {table_name} SET icono = :old_icon WHERE id = :entity_id"),
            {"old_icon": row["old_icon"], "entity_id": row["entity_id"]},
        )

    op.drop_table("icon_migration_backup")
