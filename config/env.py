"""Read settings from environment variables.

Real environment variables always win. For local development a `.env` file in the
project root is loaded first, without overriding anything already set, so
`uv run python manage.py ...` works without exporting variables by hand.
"""

import os
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import unquote, urlsplit

from django.core.exceptions import ImproperlyConfigured

_TRUE = {"1", "true", "yes", "on"}
_FALSE = {"0", "false", "no", "off", ""}


def load_dotenv(path: Path) -> None:
    """Load KEY=VALUE lines from `path` into os.environ, never overriding."""
    if not path.is_file():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip().strip("\"'"))


def env_str(name: str, default: str | None = None) -> str:
    value = os.environ.get(name, default)
    if value is None:
        raise ImproperlyConfigured(f"Missing required environment variable {name}")
    return value


def env_bool(name: str, default: bool = False) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    lowered = raw.strip().lower()
    if lowered in _TRUE:
        return True
    if lowered in _FALSE:
        return False
    raise ImproperlyConfigured(f"{name} must be a boolean, got {raw!r}")


def env_int(name: str, default: int) -> int:
    raw = os.environ.get(name)
    if raw is None or not raw.strip():
        return default
    try:
        return int(raw)
    except ValueError:
        raise ImproperlyConfigured(f"{name} must be an integer, got {raw!r}") from None


def env_list(name: str, default: str = "") -> list[str]:
    return [item.strip() for item in env_str(name, default).split(",") if item.strip()]


@dataclass(frozen=True)
class DatabaseConfig:
    name: str
    user: str
    password: str
    host: str
    port: str

    def as_django(self) -> dict[str, object]:
        return {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": self.name,
            "USER": self.user,
            "PASSWORD": self.password,
            "HOST": self.host,
            "PORT": self.port,
            "CONN_MAX_AGE": 60,
            "CONN_HEALTH_CHECKS": True,
        }


def parse_database_url(url: str) -> DatabaseConfig:
    """Parse `postgres://user:pass@host:port/name`, the format PaaS hosts provide."""
    parts = urlsplit(url)
    if parts.scheme not in {"postgres", "postgresql"}:
        raise ImproperlyConfigured("DATABASE_URL must use the postgres:// scheme")
    name = parts.path.lstrip("/")
    if not name:
        raise ImproperlyConfigured("DATABASE_URL must include a database name")
    return DatabaseConfig(
        name=unquote(name),
        user=unquote(parts.username or ""),
        password=unquote(parts.password or ""),
        host=parts.hostname or "",
        port=str(parts.port or ""),
    )
