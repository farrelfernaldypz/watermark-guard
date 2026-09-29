import hashlib
import sqlite3

import pytest
from cryptography.fernet import Fernet

from watermark.secret_key_registry import SecretKeyRegistry, SecretKeyRegistryError


def create_registry(database_path, encryption_key):
    return SecretKeyRegistry(database_path, encryption_key)


def test_registry_keys_are_unique_across_one_thousand_watermarks(tmp_path):
    database_path = tmp_path / "registry.sqlite3"
    registry = create_registry(database_path, Fernet.generate_key())

    credentials = [
        registry.create_pending(f"Owner {index}")
        for index in range(1000)
    ]

    assert len({credential.secret_key for credential in credentials}) == 1000
    assert len({credential.key_fingerprint for credential in credentials}) == 1000


def test_secret_key_stays_registered_and_unchanged_after_registry_restart(tmp_path):
    database_path = tmp_path / "registry.sqlite3"
    encryption_key = Fernet.generate_key()
    first_registry = create_registry(database_path, encryption_key)
    credential = first_registry.create_pending("Persistent Owner")
    first_registry.activate(credential.key_fingerprint)

    restarted_registry = create_registry(database_path, encryption_key)

    assert restarted_registry.is_registered(credential.secret_key)
    with sqlite3.connect(database_path) as connection:
        encrypted_key = connection.execute(
            "SELECT encrypted_secret_key FROM watermark_registry WHERE key_fingerprint = ?",
            (credential.key_fingerprint,),
        ).fetchone()[0]
    assert Fernet(encryption_key).decrypt(encrypted_key).decode("utf-8") == credential.secret_key
    assert credential.secret_key.encode("utf-8") not in database_path.read_bytes()


def test_database_unique_constraint_rejects_duplicate_key_fingerprint(tmp_path):
    database_path = tmp_path / "registry.sqlite3"
    registry = create_registry(database_path, Fernet.generate_key())
    credential = registry.create_pending("Unique Owner")

    with sqlite3.connect(database_path) as connection:
        row = connection.execute(
            """
            SELECT key_fingerprint, encrypted_secret_key, owner_identity,
                   algorithm, created_at, status
            FROM watermark_registry WHERE key_fingerprint = ?
            """,
            (credential.key_fingerprint,),
        ).fetchone()

        with pytest.raises(sqlite3.IntegrityError):
            connection.execute(
                """
                INSERT INTO watermark_registry (
                    key_fingerprint, encrypted_secret_key, owner_identity,
                    algorithm, created_at, status
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                row,
            )


def test_database_prevents_secret_key_changes_and_record_deletion(tmp_path):
    database_path = tmp_path / "registry.sqlite3"
    registry = create_registry(database_path, Fernet.generate_key())
    credential = registry.create_pending("Immutable Owner")

    with sqlite3.connect(database_path) as connection:
        with pytest.raises(sqlite3.IntegrityError, match="immutable"):
            connection.execute(
                "UPDATE watermark_registry SET encrypted_secret_key = ? WHERE key_fingerprint = ?",
                (b"replacement", credential.key_fingerprint),
            )
        with pytest.raises(sqlite3.IntegrityError, match="permanent"):
            connection.execute(
                "DELETE FROM watermark_registry WHERE key_fingerprint = ?",
                (credential.key_fingerprint,),
            )


def test_legacy_watermark_id_column_is_migrated_away_without_losing_keys(tmp_path):
    database_path = tmp_path / "legacy.sqlite3"
    encryption_key = Fernet.generate_key()
    fernet = Fernet(encryption_key)
    secret_key = "legacy-persisted-key"
    fingerprint = hashlib.sha256(secret_key.encode("utf-8")).hexdigest()
    encrypted_secret_key = fernet.encrypt(secret_key.encode("utf-8"))

    with sqlite3.connect(database_path) as connection:
        connection.execute(
            """
            CREATE TABLE watermark_registry (
                watermark_id TEXT PRIMARY KEY,
                key_fingerprint TEXT NOT NULL UNIQUE,
                encrypted_secret_key BLOB NOT NULL,
                owner_identity TEXT NOT NULL,
                algorithm TEXT NOT NULL,
                created_at TEXT NOT NULL,
                status TEXT NOT NULL
            )
            """
        )
        connection.execute(
            """
            INSERT INTO watermark_registry VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "legacy-watermark-id",
                fingerprint,
                encrypted_secret_key,
                "Legacy Owner",
                "hybrid-dwt-dct",
                "2026-09-29T00:00:00+00:00",
                "active",
            ),
        )

    registry = create_registry(database_path, encryption_key)

    assert registry.is_registered(secret_key)
    with sqlite3.connect(database_path) as connection:
        column_names = {
            row[1] for row in connection.execute("PRAGMA table_info(watermark_registry)")
        }
    assert "watermark_id" not in column_names


def test_railway_requires_persistent_volume_instead_of_ephemeral_filesystem(monkeypatch):
    monkeypatch.setenv("RAILWAY_ENVIRONMENT", "production")
    monkeypatch.delenv("RAILWAY_VOLUME_MOUNT_PATH", raising=False)

    with pytest.raises(SecretKeyRegistryError, match="Persistent application storage"):
        SecretKeyRegistry.from_environment()


def test_railway_registry_uses_mounted_volume(tmp_path, monkeypatch):
    monkeypatch.setenv("RAILWAY_ENVIRONMENT", "production")
    monkeypatch.setenv("RAILWAY_VOLUME_MOUNT_PATH", str(tmp_path))
    monkeypatch.setenv("WATERMARK_ENCRYPTION_KEY", Fernet.generate_key().decode("ascii"))

    registry = SecretKeyRegistry.from_environment()
    credential = registry.create_pending("Railway Owner")
    registry.activate(credential.key_fingerprint)

    assert (tmp_path / "watermarkguard.sqlite3").exists()
    assert registry.is_registered(credential.secret_key)
