"""GitHub App authentication: load credentials, sign JWT, exchange for installation token.

Credentials lookup order (per app name):
  1. ``/secrets/<app_name>.env`` + ``/secrets/<app_name>.private-key.pem`` (volume mount)
  2. Environment variables: ``GH_APP_ID``, ``GH_INSTALLATION_ID``, ``GH_APP_PRIVATE_KEY``

Tokens are short-lived (~1h on GitHub side); we cache with a safety buffer.
"""

from __future__ import annotations

import os
import threading
import time
from dataclasses import dataclass
from pathlib import Path

import httpx
import jwt

DEFAULT_APP_NAME = "kisnlab-dev"
SECRETS_DIR = Path("/secrets")
TOKEN_TTL_SECONDS = 50 * 60  # GitHub gives 1h, cache for 50min for safety
JWT_TTL_SECONDS = 9 * 60  # GitHub max is 10min, use 9min for clock drift tolerance
GITHUB_API_BASE = "https://api.github.com"


@dataclass(frozen=True)
class AppCredentials:
    app_id: str
    installation_id: str
    private_key_pem: str


def load_credentials(app_name: str = DEFAULT_APP_NAME) -> AppCredentials:
    """Load credentials from secrets dir, fall back to env vars."""
    env_file = SECRETS_DIR / f"{app_name}.env"
    pem_file = SECRETS_DIR / f"{app_name}.private-key.pem"

    if env_file.is_file() and pem_file.is_file():
        env_values = _parse_env_file(env_file)
        return AppCredentials(
            app_id=_require(env_values, "GH_APP_ID", str(env_file)),
            installation_id=_require(env_values, "GH_INSTALLATION_ID", str(env_file)),
            private_key_pem=pem_file.read_text(),
        )

    app_id = os.getenv("GH_APP_ID")
    installation_id = os.getenv("GH_INSTALLATION_ID")
    private_key = os.getenv("GH_APP_PRIVATE_KEY")
    missing = [
        name
        for name, value in (
            ("GH_APP_ID", app_id),
            ("GH_INSTALLATION_ID", installation_id),
            ("GH_APP_PRIVATE_KEY", private_key),
        )
        if not value
    ]
    if missing:
        raise RuntimeError(
            f"GitHub App credentials missing: {missing}. "
            f"Either mount secrets at {SECRETS_DIR}/{app_name}.{{env,private-key.pem}} "
            f"or set env vars."
        )
    assert app_id and installation_id and private_key  # narrow for type checker
    return AppCredentials(
        app_id=app_id,
        installation_id=installation_id,
        private_key_pem=private_key,
    )


def _parse_env_file(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for raw_line in path.read_text().splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def _require(values: dict[str, str], key: str, source: str) -> str:
    value = values.get(key)
    if not value:
        raise RuntimeError(f"{key} missing in {source}")
    return value


def _build_jwt(creds: AppCredentials, now: int | None = None) -> str:
    now = now if now is not None else int(time.time())
    payload = {
        "iat": now - 60,  # tolerate clock drift
        "exp": now + JWT_TTL_SECONDS,
        "iss": creds.app_id,
    }
    return jwt.encode(payload, creds.private_key_pem, algorithm="RS256")


def _exchange_jwt_for_token(creds: AppCredentials, app_jwt: str) -> str:
    url = f"{GITHUB_API_BASE}/app/installations/{creds.installation_id}/access_tokens"
    response = httpx.post(
        url,
        headers={
            "Authorization": f"Bearer {app_jwt}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        },
        timeout=10.0,
    )
    response.raise_for_status()
    token = response.json().get("token")
    if not token:
        raise RuntimeError("Installation token missing from GitHub response")
    return token


class InstallationTokenProvider:
    """Thread-safe cache for installation tokens."""

    def __init__(self, app_name: str = DEFAULT_APP_NAME) -> None:
        self._app_name = app_name
        self._lock = threading.Lock()
        self._token: str | None = None
        self._expires_at: float = 0.0

    def get_token(self) -> str:
        with self._lock:
            if self._token and time.time() < self._expires_at:
                return self._token
            creds = load_credentials(self._app_name)
            app_jwt = _build_jwt(creds)
            token = _exchange_jwt_for_token(creds, app_jwt)
            self._token = token
            self._expires_at = time.time() + TOKEN_TTL_SECONDS
            return token

    def invalidate(self) -> None:
        with self._lock:
            self._token = None
            self._expires_at = 0.0
