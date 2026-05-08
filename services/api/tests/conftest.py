import pytest

from app.auth import verify_token
from app.main import app


@pytest.fixture(autouse=True)
def disable_auth():
    """Override Bearer auth by default for all tests.

    Tests that exercise the real auth flow opt out via the `enable_auth` fixture.
    """
    app.dependency_overrides[verify_token] = lambda: None
    yield
    app.dependency_overrides.pop(verify_token, None)


@pytest.fixture
def enable_auth():
    """Restore the real verify_token dependency for auth-focused tests."""
    app.dependency_overrides.pop(verify_token, None)
    yield
