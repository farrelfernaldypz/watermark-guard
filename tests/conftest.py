import pytest
from cryptography.fernet import Fernet


@pytest.fixture(autouse=True)
def configure_temporary_secret_registry(tmp_path, monkeypatch):
    monkeypatch.setenv("WATERMARK_DB_PATH", str(tmp_path / "watermarkguard.sqlite3"))
    monkeypatch.setenv(
        "WATERMARK_ENCRYPTION_KEY",
        Fernet.generate_key().decode("ascii"),
    )
