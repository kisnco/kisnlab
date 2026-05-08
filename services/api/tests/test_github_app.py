"""Unit tests for github_app: credential loading, JWT, token cache."""

from __future__ import annotations

import time
from unittest.mock import MagicMock, patch

import jwt
import pytest

from app.agents.tools import github_app


# ---- helpers ----------------------------------------------------------------

# Test RSA key (generated for tests only — not a real GitHub App key).
# Use a small key for fast test signing.
@pytest.fixture(scope="module")
def rsa_key() -> str:
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric import rsa

    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    return key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode()


@pytest.fixture
def secrets_dir(tmp_path, monkeypatch, rsa_key):
    env_file = tmp_path / "kisnlab-test.env"
    env_file.write_text("GH_APP_ID=42\nGH_INSTALLATION_ID=99\n")
    pem_file = tmp_path / "kisnlab-test.private-key.pem"
    pem_file.write_text(rsa_key)
    monkeypatch.setattr(github_app, "SECRETS_DIR", tmp_path)
    return tmp_path


# ---- load_credentials -------------------------------------------------------


def test_load_credentials_from_secrets_dir(secrets_dir, rsa_key):
    creds = github_app.load_credentials("kisnlab-test")
    assert creds.app_id == "42"
    assert creds.installation_id == "99"
    assert creds.private_key_pem == rsa_key


def test_load_credentials_falls_back_to_env_vars(tmp_path, monkeypatch, rsa_key):
    monkeypatch.setattr(github_app, "SECRETS_DIR", tmp_path)
    monkeypatch.setenv("GH_APP_ID", "111")
    monkeypatch.setenv("GH_INSTALLATION_ID", "222")
    monkeypatch.setenv("GH_APP_PRIVATE_KEY", rsa_key)

    creds = github_app.load_credentials("missing-app")
    assert creds.app_id == "111"
    assert creds.installation_id == "222"
    assert creds.private_key_pem == rsa_key


def test_load_credentials_raises_when_nothing_configured(tmp_path, monkeypatch):
    monkeypatch.setattr(github_app, "SECRETS_DIR", tmp_path)
    monkeypatch.delenv("GH_APP_ID", raising=False)
    monkeypatch.delenv("GH_INSTALLATION_ID", raising=False)
    monkeypatch.delenv("GH_APP_PRIVATE_KEY", raising=False)

    with pytest.raises(RuntimeError, match="credentials missing"):
        github_app.load_credentials("absent")


def test_parse_env_file_handles_quotes_and_comments(tmp_path):
    f = tmp_path / "x.env"
    f.write_text(
        '# comment\n'
        'GH_APP_ID="123"\n'
        "GH_INSTALLATION_ID='456'\n"
        "\n"
        "EMPTY_LINE_OK=1\n"
    )
    parsed = github_app._parse_env_file(f)
    assert parsed == {"GH_APP_ID": "123", "GH_INSTALLATION_ID": "456", "EMPTY_LINE_OK": "1"}


# ---- _build_jwt -------------------------------------------------------------


def test_build_jwt_is_decodable_with_public_key(rsa_key):
    creds = github_app.AppCredentials(
        app_id="42", installation_id="99", private_key_pem=rsa_key
    )
    token = github_app._build_jwt(creds, now=1_700_000_000)

    from cryptography.hazmat.primitives import serialization

    private = serialization.load_pem_private_key(rsa_key.encode(), password=None)
    public_pem = private.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    ).decode()

    payload = jwt.decode(
        token, public_pem, algorithms=["RS256"], options={"verify_exp": False}
    )
    assert payload["iss"] == "42"
    assert payload["iat"] == 1_700_000_000 - 60
    assert payload["exp"] == 1_700_000_000 + github_app.JWT_TTL_SECONDS


# ---- InstallationTokenProvider ---------------------------------------------


def test_token_provider_caches_within_ttl(secrets_dir):
    provider = github_app.InstallationTokenProvider("kisnlab-test")

    with patch.object(github_app, "_exchange_jwt_for_token") as exchange:
        exchange.return_value = "tok-1"
        assert provider.get_token() == "tok-1"
        assert provider.get_token() == "tok-1"
        assert exchange.call_count == 1


def test_token_provider_refreshes_after_expiry(secrets_dir):
    provider = github_app.InstallationTokenProvider("kisnlab-test")

    with patch.object(github_app, "_exchange_jwt_for_token") as exchange:
        exchange.side_effect = ["tok-1", "tok-2"]

        assert provider.get_token() == "tok-1"
        # Simulate expiry by rewinding the cached deadline.
        provider._expires_at = 0.0
        assert provider.get_token() == "tok-2"
        assert exchange.call_count == 2


def test_token_provider_invalidate_forces_refresh(secrets_dir):
    provider = github_app.InstallationTokenProvider("kisnlab-test")

    with patch.object(github_app, "_exchange_jwt_for_token") as exchange:
        exchange.side_effect = ["tok-1", "tok-2"]
        assert provider.get_token() == "tok-1"
        provider.invalidate()
        assert provider.get_token() == "tok-2"


# ---- _exchange_jwt_for_token -----------------------------------------------


def test_exchange_jwt_for_token_extracts_token(rsa_key):
    creds = github_app.AppCredentials(
        app_id="42", installation_id="99", private_key_pem=rsa_key
    )
    fake_response = MagicMock()
    fake_response.json.return_value = {"token": "ghs_abc"}
    fake_response.raise_for_status.return_value = None

    with patch.object(github_app.httpx, "post", return_value=fake_response) as post:
        token = github_app._exchange_jwt_for_token(creds, "fake-jwt")
        assert token == "ghs_abc"
        post.assert_called_once()
        # Authorization header must carry the JWT
        kwargs = post.call_args.kwargs
        assert kwargs["headers"]["Authorization"] == "Bearer fake-jwt"


def test_exchange_jwt_for_token_raises_when_token_missing(rsa_key):
    creds = github_app.AppCredentials(
        app_id="42", installation_id="99", private_key_pem=rsa_key
    )
    fake_response = MagicMock()
    fake_response.json.return_value = {"message": "Bad credentials"}
    fake_response.raise_for_status.return_value = None

    with patch.object(github_app.httpx, "post", return_value=fake_response):
        with pytest.raises(RuntimeError, match="Installation token missing"):
            github_app._exchange_jwt_for_token(creds, "fake-jwt")
