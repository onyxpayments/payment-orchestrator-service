from pydantic import ValidationError
import pytest

from config.settings import Settings


def test_settings_mask_database_and_rabbitmq_secrets():
    settings = Settings(
        _env_file=None,
        database_url="postgresql://user:database-secret@db/payments",
        bank_service_url="http://bank",
        rabbitmq_password="broker-secret",
    )

    representation = repr(settings)

    assert "database-secret" not in representation
    assert "broker-secret" not in representation
    assert "**********" in representation


def test_rabbitmq_password_is_required(monkeypatch):
    monkeypatch.delenv("RABBITMQ_PASSWORD", raising=False)

    with pytest.raises(ValidationError):
        Settings(
            _env_file=None,
            database_url="postgresql://db/payments",
            bank_service_url="http://bank",
        )
