from unittest.mock import patch

import pytest
from pydantic import ValidationError

from app.core.config import DEFAULT_SECRET_KEY, Settings


def _production_settings(**overrides):
    return Settings(
        _env_file=None,  # ignore the developer's local .env
        ENVIRONMENT="production",
        **{"SECRET_KEY": "x" * 48, **overrides},
    )


def test_production_refuses_default_secret():
    with pytest.raises(ValidationError, match="SECRET_KEY"):
        _production_settings(SECRET_KEY=DEFAULT_SECRET_KEY)


def test_production_refuses_empty_secret():
    with pytest.raises(ValidationError, match="SECRET_KEY"):
        _production_settings(SECRET_KEY="")


def test_production_accepts_strong_secret():
    settings = _production_settings()
    assert settings.ENVIRONMENT == "production"


def test_production_warns_on_short_secret():
    with pytest.warns(UserWarning, match="SECRET_KEY"):
        _production_settings(SECRET_KEY="x" * 16)


def test_development_allows_default_secret():
    settings = Settings(_env_file=None, ENVIRONMENT="development")
    assert settings.SECRET_KEY == DEFAULT_SECRET_KEY


def test_environment_defaults_to_development():
    settings = Settings(_env_file=None)
    assert settings.ENVIRONMENT == "development"


def test_settings_loads_from_real_environment():
    with patch.dict("os.environ", {"SECRET_KEY": "env-provided-secret"}):
        settings = Settings(_env_file=None)
    assert settings.SECRET_KEY == "env-provided-secret"
