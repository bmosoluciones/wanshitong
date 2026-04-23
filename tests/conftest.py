"""Shared pytest fixtures for the test suite."""

import pytest

from wanshitong import create_app, ensure_database_initialized


@pytest.fixture(scope="session")
def app():
    """Single application instance shared across the entire test session."""
    cfg = {
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        "TESTING": True,
        "SECRET_KEY": "test-secret",
        "WTF_CSRF_ENABLED": False,
    }
    application = create_app(cfg)
    with application.app_context():
        ensure_database_initialized(application)
    return application
