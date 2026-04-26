# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 BMO Soluciones, S.A.

from __future__ import annotations

import secrets

import click

from wanshitong import create_app, ensure_database_initialized
from wanshitong.auth import proteger_passwd
from wanshitong.config import configuration
from wanshitong.model import Usuario, database
from wanshitong.version import __version__


def _commit_or_rollback() -> None:
    try:
        database.session.commit()
    except Exception:
        database.session.rollback()
        raise


def _app():
    return create_app(configuration)


@click.group()
def main() -> None:
    """WanShiTong operational CLI."""


@main.command()
def version() -> None:
    click.echo(__version__)


@main.group()
def user() -> None:
    """User administration commands."""


@user.command("admin_reset")
@click.option("--username", default="admin-reset", show_default=True)
@click.option("--password", default=None)
def admin_reset(username: str, password: str | None) -> None:
    app = _app()
    with app.app_context():
        ensure_database_initialized(app)
        generated_password = password or secrets.token_urlsafe(16)
        user = database.session.execute(
            database.select(Usuario).where(Usuario.usuario == username)
        ).scalar_one_or_none()
        if user is None:
            user = Usuario()
            user.usuario = username
            user.tipo = "admin"
            user.activo = True
            user.creado_por = "docsctl"
            database.session.add(user)
        user.acceso = proteger_passwd(generated_password)
        user.tipo = "admin"
        user.activo = True
        user.modificado_por = "docsctl"
        _commit_or_rollback()
        click.echo(f"username={username}")
        click.echo(f"password={generated_password}")


@user.command("list")
def list_users() -> None:
    app = _app()
    with app.app_context():
        ensure_database_initialized(app)
        users = database.session.execute(database.select(Usuario).order_by(Usuario.usuario)).scalars().all()
        for user in users:
            click.echo(f"{user.usuario}\t{user.tipo}\t{'active' if user.activo else 'inactive'}")


@main.command("sync-schema")
def sync_schema() -> None:
    app = _app()
    with app.app_context():
        ensure_database_initialized(app)
    click.echo("schema-synced")


if __name__ == "__main__":
    main()
