# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 BMO Soluciones, S.A.

from click.testing import CliRunner
from wanshitong.cli import main


def test_cli_version():
    runner = CliRunner()
    result = runner.invoke(main, ["version"])
    assert result.exit_code == 0
    assert "0.0.7" in result.output


def test_cli_user_list(app, monkeypatch):
    runner = CliRunner()
    with app.app_context():
        # Avoid creating another app by patching _app to return our already setup app
        monkeypatch.setattr("wanshitong.cli._app", lambda: app)
        result = runner.invoke(main, ["user", "list"])
        assert result.exit_code == 0
        assert "app-admin" in result.output


def test_cli_sync_schema(app, monkeypatch):
    runner = CliRunner()
    with app.app_context():
        monkeypatch.setattr("wanshitong.cli._app", lambda: app)
        result = runner.invoke(main, ["sync-schema"])
        assert result.exit_code == 0
        assert "schema-synced" in result.output


def test_cli_admin_reset(app, monkeypatch):
    runner = CliRunner()
    with app.app_context():
        monkeypatch.setattr("wanshitong.cli._app", lambda: app)
        result = runner.invoke(
            main,
            ["user", "admin_reset", "--username", "cli-test-admin", "--password", "clipass123"],
        )
        assert result.exit_code == 0
        assert "username=cli-test-admin" in result.output
        assert "password=clipass123" in result.output
