"""Day 1 smoke tests: package imports + Settings env loading."""

from pathlib import Path

import pytest
from pydantic import ValidationError

from k_fingraph import config, errors
from k_fingraph.config import Settings, get_settings

REQUIRED_ENV = {
    "NEO4J_URI": "neo4j+s://test.databases.neo4j.io",
    "NEO4J_USERNAME": "neo4j",
    "NEO4J_PASSWORD": "test-password",
    "DART_API_KEY": "test-dart-key",
    "OPENAI_API_KEY": "sk-test",
}


@pytest.mark.unit
def test_package_imports() -> None:
    import k_fingraph

    assert k_fingraph.__version__
    assert config is not None
    assert errors.KFinGraphError is not None


@pytest.mark.unit
def test_settings_reads_environment(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    # Run from a clean cwd so a developer's real .env isn't picked up.
    monkeypatch.chdir(tmp_path)
    for key, value in REQUIRED_ENV.items():
        monkeypatch.setenv(key, value)
    get_settings.cache_clear()

    settings = Settings()  # type: ignore[call-arg]

    assert settings.neo4j_uri == REQUIRED_ENV["NEO4J_URI"]
    assert settings.neo4j_username == "neo4j"
    assert settings.neo4j_password == REQUIRED_ENV["NEO4J_PASSWORD"]
    assert settings.dart_api_key == REQUIRED_ENV["DART_API_KEY"]
    assert settings.openai_api_key == REQUIRED_ENV["OPENAI_API_KEY"]
    assert settings.log_level == "INFO"


@pytest.mark.unit
def test_settings_missing_required_raises(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.chdir(tmp_path)
    for key in REQUIRED_ENV:
        monkeypatch.delenv(key, raising=False)
    get_settings.cache_clear()

    with pytest.raises(ValidationError):
        Settings()  # type: ignore[call-arg]
