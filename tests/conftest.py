import pathlib
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


@pytest.fixture(autouse=True)
def _media_in_tmp(settings: pytest.FixtureRequest, tmp_path: "pathlib.Path") -> None:
    # Uploaded files go to a per-test folder, never into the real media/ directory.
    settings.MEDIA_ROOT = tmp_path / "media"  # type: ignore[attr-defined]
