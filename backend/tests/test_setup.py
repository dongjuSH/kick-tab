from unittest.mock import MagicMock, patch

import psycopg
import pytest
from fastapi.testclient import TestClient

from app.check_database import main as check_database
from app.config import BACKEND_DIR, Settings
from app.database import CA_CERTIFICATE, get_connection
from app.main import app


def test_health_and_local_frontend_cors():
    client = TestClient(app)
    response = client.get("/health", headers={"Origin": "http://localhost:3000"})
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    assert response.headers["access-control-allow-origin"] == "http://localhost:3000"


def test_environment_loads_from_backend_directory_and_masks_secrets(tmp_path, monkeypatch):
    for key in ("API_FOOTBALL_KEY", "NAVER_CLIENT_ID", "NAVER_CLIENT_SECRET", "DATABASE_URL"):
        monkeypatch.setenv(key, f"test-{key.lower()}")
    monkeypatch.chdir(tmp_path)
    loaded = Settings()
    assert Settings.model_config["env_file"] == BACKEND_DIR / ".env"
    assert loaded.api_football_key.get_secret_value() == "test-api_football_key"
    assert loaded.naver_client_id.get_secret_value() == "test-naver_client_id"
    assert loaded.naver_client_secret.get_secret_value() == "test-naver_client_secret"
    assert loaded.database_url.get_secret_value() == "test-database_url"
    for value in loaded.model_dump().values():
        if hasattr(value, "get_secret_value"):
            assert value.get_secret_value() not in repr(loaded)
            assert value.get_secret_value() not in loaded.model_dump_json()


def test_database_connection_enforces_server_identity_verification(monkeypatch):
    monkeypatch.setattr("app.database.settings", Settings(database_url="test-database-url"))
    connection = MagicMock()
    with patch("app.database.psycopg.connect") as connect:
        connect.return_value.__enter__.return_value = connection
        with get_connection() as actual:
            assert actual is connection
        assert connect.call_args.kwargs["sslmode"] == "verify-full"
        assert connect.call_args.kwargs["sslrootcert"] == str(CA_CERTIFICATE)
        assert CA_CERTIFICATE.is_file()


def test_connection_error_is_propagated_to_transaction_context(monkeypatch):
    monkeypatch.setattr("app.database.settings", Settings(database_url="test-database-url"))
    with patch("app.database.psycopg.connect") as connect:
        with pytest.raises(RuntimeError, match="failed operation"), get_connection():
            raise RuntimeError("failed operation")
        assert connect.return_value.__exit__.call_args.args[0] is RuntimeError


def test_database_check_is_read_only_and_checks_tls(capsys):
    connection = MagicMock()
    connection.execute.return_value.fetchone.side_effect = [(1,), (True,)]
    with patch("app.check_database.get_connection") as connect:
        connect.return_value.__enter__.return_value = connection
        assert check_database() == 0
    assert connection.read_only is True
    assert "PASS (read-only)" in capsys.readouterr().out


def test_database_check_does_not_print_driver_connection_details(capsys):
    with patch("app.check_database.get_connection") as connect:
        connect.return_value.__enter__.side_effect = psycopg.OperationalError(
            "password=private-test-value"
        )
        assert check_database() == 1
    output = capsys.readouterr().out
    assert "private-test-value" not in output
    assert "Database check failed" in output
