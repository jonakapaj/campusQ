from collections.abc import Iterator

import pytest
from django.core.cache import cache


@pytest.fixture(autouse=True)
def _fast_password_hashing(settings: pytest.FixtureRequest) -> None:
    settings.PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]  # type: ignore[attr-defined]


@pytest.fixture(autouse=True)
def _clear_rate_limits() -> Iterator[None]:
    # allauth keeps rate-limit counters in the cache; don't let tests share them.
    cache.clear()
    yield
    cache.clear()
