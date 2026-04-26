# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 BMO Soluciones, S.A.

"""Shared pytest fixtures for the test suite."""

import pytest

from wanshitong import create_app, ensure_database_initialized


@pytest.fixture(scope="session")
def app(tmp_path_factory):
    """Single application instance shared across the entire test session."""
    database_path = tmp_path_factory.mktemp("db") / "test.db"
    cfg = {
        "SQLALCHEMY_DATABASE_URI": f"sqlite:///{database_path.as_posix()}",
        "TESTING": True,
        "SECRET_KEY": "test-secret",
        "WTF_CSRF_ENABLED": False,
    }
    application = create_app(cfg)
    with application.app_context():
        ensure_database_initialized(application)
    return application
