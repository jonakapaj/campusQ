from pathlib import Path

import pytest
from django.core.exceptions import ImproperlyConfigured

from config.env import env_bool, env_int, env_list, env_str, load_dotenv, parse_database_url


class TestEnvStr:
    def test_returns_value(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("CQ_TEST", "value")
        assert env_str("CQ_TEST") == "value"

    def test_missing_without_default_raises(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("CQ_TEST", raising=False)
        with pytest.raises(ImproperlyConfigured, match="CQ_TEST"):
            env_str("CQ_TEST")


class TestEnvBool:
    @pytest.mark.parametrize("raw", ["1", "true", "TRUE", "yes", "on", " True "])
    def test_truthy(self, monkeypatch: pytest.MonkeyPatch, raw: str) -> None:
        monkeypatch.setenv("CQ_FLAG", raw)
        assert env_bool("CQ_FLAG") is True

    @pytest.mark.parametrize("raw", ["0", "false", "no", "off", ""])
    def test_falsy(self, monkeypatch: pytest.MonkeyPatch, raw: str) -> None:
        monkeypatch.setenv("CQ_FLAG", raw)
        assert env_bool("CQ_FLAG", default=True) is False

    def test_unset_uses_default(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("CQ_FLAG", raising=False)
        assert env_bool("CQ_FLAG", default=True) is True

    def test_garbage_raises_instead_of_guessing(self, monkeypatch: pytest.MonkeyPatch) -> None:
        # A typo like DJANGO_DEBUG=ture must not silently become False (or True).
        monkeypatch.setenv("CQ_FLAG", "ture")
        with pytest.raises(ImproperlyConfigured):
            env_bool("CQ_FLAG")


def test_env_list_strips_and_drops_empty(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CQ_LIST", " a.al, b.al ,,")
    assert env_list("CQ_LIST") == ["a.al", "b.al"]


class TestParseDatabaseUrl:
    def test_full_url(self) -> None:
        cfg = parse_database_url("postgres://user:p%40ss@db.example.com:6543/campusq")
        assert (cfg.user, cfg.password, cfg.host, cfg.port, cfg.name) == (
            "user",
            "p@ss",
            "db.example.com",
            "6543",
            "campusq",
        )

    def test_postgresql_scheme_and_default_port(self) -> None:
        cfg = parse_database_url("postgresql://u:p@localhost/db")
        assert cfg.port == ""
        assert cfg.as_django()["ENGINE"] == "django.db.backends.postgresql"

    @pytest.mark.parametrize(
        "url", ["mysql://u:p@localhost/db", "postgres://u:p@localhost", "postgres://u:p@localhost/"]
    )
    def test_rejects_invalid(self, url: str) -> None:
        with pytest.raises(ImproperlyConfigured):
            parse_database_url(url)


def test_load_dotenv_never_overrides_real_env(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    dotenv = tmp_path / ".env"
    dotenv.write_text('# comment\nCQ_A=from_file\nCQ_B="quoted"\nnot a pair\n', encoding="utf-8")
    monkeypatch.setenv("CQ_A", "from_env")
    monkeypatch.delenv("CQ_B", raising=False)

    load_dotenv(dotenv)

    assert env_str("CQ_A") == "from_env"
    assert env_str("CQ_B") == "quoted"


class TestEnvInt:
    def test_parses(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("CQ_PORT", "2525")
        assert env_int("CQ_PORT", default=587) == 2525

    @pytest.mark.parametrize("raw", [None, "", "  "])
    def test_unset_or_blank_uses_default(
        self, monkeypatch: pytest.MonkeyPatch, raw: str | None
    ) -> None:
        if raw is None:
            monkeypatch.delenv("CQ_PORT", raising=False)
        else:
            monkeypatch.setenv("CQ_PORT", raw)
        assert env_int("CQ_PORT", default=587) == 587

    def test_garbage_raises(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("CQ_PORT", "58x")
        with pytest.raises(ImproperlyConfigured, match="CQ_PORT"):
            env_int("CQ_PORT", default=587)
