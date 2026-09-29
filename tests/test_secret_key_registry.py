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
    assert len({credential.watermark_id for credential in credentials}) == 1000


def test_secret_key_is_recovered_unchanged_after_registry_restart(tmp_path):
    database_path = tmp_path / "registry.sqlite3"
    encryption_key = Fernet.generate_key()
    first_registry = create_registry(database_path, encryption_key)
    credential = first_registry.create_pending("Persistent Owner")
    first_registry.activate(credential.watermark_id)

    restarted_registry = create_registry(database_path, encryption_key)

    assert restarted_registry.get_secret_key(credential.watermark_id) == credential.secret_key
    assert restarted_registry.is_registered(credential.secret_key)
    assert restarted_registry.get_secret_key(credential.watermark_id) == credential.secret_key
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
            FROM watermark_registry WHERE watermark_id = ?
            """,
            (credential.watermark_id,),
        ).fetchone()

        try:
            connection.execute(
                """
                INSERT INTO watermark_registry (
                    watermark_id, key_fingerprint, encrypted_secret_key,
                    owner_identity, algorithm, created_at, status
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                ("second-watermark-id", *row),
            )
        except sqlite3.IntegrityError:
            duplicate_rejected = True
        else:
            duplicate_rejected = False

    assert duplicate_rejected


def test_database_prevents_identity_changes_and_record_deletion(tmp_path):
    database_path = tmp_path / "registry.sqlite3"
    registry = create_registry(database_path, Fernet.generate_key())
    credential = registry.create_pending("Immutable Owner")

    with sqlite3.connect(database_path) as connection:
        with pytest.raises(sqlite3.IntegrityError, match="immutable"):
            connection.execute(
                "UPDATE watermark_registry SET encrypted_secret_key = ? WHERE watermark_id = ?",
                (b"replacement", credential.watermark_id),
            )
        with pytest.raises(sqlite3.IntegrityError, match="permanent"):
            connection.execute(
                "DELETE FROM watermark_registry WHERE watermark_id = ?",
                (credential.watermark_id,),
            )


def test_railway_requires_persistent_volume_instead_of_ephemeral_filesystem(monkeypatch):
    monkeypatch.setenv("RAILWAY_ENVIRONMENT", "production")
    monkeypatch.delenv("RAILWAY_VOLUME_MOUNT_PATH", raising=False)

    with pytest.raises(SecretKeyRegistryError, match="Railway Volume"):
        SecretKeyRegistry.from_environment()


def test_railway_registry_uses_mounted_volume(tmp_path, monkeypatch):
    monkeypatch.setenv("RAILWAY_ENVIRONMENT", "production")
    monkeypatch.setenv("RAILWAY_VOLUME_MOUNT_PATH", str(tmp_path))
    monkeypatch.setenv("WATERMARK_ENCRYPTION_KEY", Fernet.generate_key().decode("ascii"))

    registry = SecretKeyRegistry.from_environment()
    credential = registry.create_pending("Railway Owner")
    registry.activate(credential.watermark_id)

    assert (tmp_path / "watermarkguard.sqlite3").exists()
    assert registry.get_secret_key(credential.watermark_id) == credential.secret_key
