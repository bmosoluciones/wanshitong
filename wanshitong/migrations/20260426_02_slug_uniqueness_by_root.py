"""Scope category and tag slug uniqueness to root nodes only.

Revision ID: 20260426_02
Revises: 20260425_01
Create Date: 2026-04-26 00:00:00

"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "20260426_02"
down_revision = "20260425_01"
branch_labels = None
depends_on = None


def _drop_index_if_exists(table_name: str, index_name: str) -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing = {idx["name"] for idx in inspector.get_indexes(table_name)}
    if index_name in existing:
        op.drop_index(index_name, table_name=table_name)


def _create_index_if_missing(
    table_name: str,
    index_name: str,
    columns: list[str],
    *,
    unique: bool,
    sqlite_where: sa.TextClause | None = None,
    postgresql_where: sa.TextClause | None = None,
) -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing = {idx["name"] for idx in inspector.get_indexes(table_name)}
    if index_name in existing:
        return
    op.create_index(
        index_name,
        table_name,
        columns,
        unique=unique,
        sqlite_where=sqlite_where,
        postgresql_where=postgresql_where,
    )


def upgrade() -> None:
    # Remove global slug uniqueness indexes created from unique=True.
    _drop_index_if_exists("categoria", "ix_categoria_slug")
    _drop_index_if_exists("etiqueta", "ix_etiqueta_slug")

    # Keep a regular non-unique lookup index for slug.
    _create_index_if_missing("categoria", "ix_categoria_slug", ["slug"], unique=False)
    _create_index_if_missing("etiqueta", "ix_etiqueta_slug", ["slug"], unique=False)

    # Enforce uniqueness only for root nodes (parent_id IS NULL).
    _create_index_if_missing(
        "categoria",
        "ux_categoria_slug_root",
        ["slug"],
        unique=True,
        sqlite_where=sa.text("parent_id IS NULL"),
        postgresql_where=sa.text("parent_id IS NULL"),
    )
    _create_index_if_missing(
        "etiqueta",
        "ux_etiqueta_slug_root",
        ["slug"],
        unique=True,
        sqlite_where=sa.text("parent_id IS NULL"),
        postgresql_where=sa.text("parent_id IS NULL"),
    )


def downgrade() -> None:
    _drop_index_if_exists("categoria", "ux_categoria_slug_root")
    _drop_index_if_exists("etiqueta", "ux_etiqueta_slug_root")

    _drop_index_if_exists("categoria", "ix_categoria_slug")
    _drop_index_if_exists("etiqueta", "ix_etiqueta_slug")

    _create_index_if_missing("categoria", "ix_categoria_slug", ["slug"], unique=True)
    _create_index_if_missing("etiqueta", "ix_etiqueta_slug", ["slug"], unique=True)
