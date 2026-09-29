import hashlib
import os
import secrets
import sqlite3
from contextlib import closing
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from cryptography.fernet import Fernet


class SecretKeyRegistryError(RuntimeError):
    """Raised when the persistent secret key registry is unavailable."""


@dataclass(frozen=True)
class SecretKeyCredential:
    secret_key: str
    key_fingerprint: str


class SecretKeyRegistry:
    """Persistent registry for unique, encrypted watermark secret keys."""

    def __init__(self, database_path: Path, encryption_key: bytes) -> None:
        self.database_path = database_path
        try:
            self._fernet = Fernet(encryption_key)
        except (TypeError, ValueError) as error:
            raise SecretKeyRegistryError(
                "WATERMARK_ENCRYPTION_KEY harus berupa Fernet key yang valid."
            ) from error

        try:
            self.database_path.parent.mkdir(parents=True, exist_ok=True)
            self._initialize_database()
        except sqlite3.Error as error:
            raise SecretKeyRegistryError(
                "Database Secret Key tidak dapat dibuka atau disiapkan."
            ) from error
        except OSError as error:
            raise SecretKeyRegistryError(
                "Lokasi database Secret Key tidak dapat diakses."
            ) from error

    @classmethod
    def from_environment(cls, project_root: Path | None = None) -> "SecretKeyRegistry":
        """Build the registry from local settings or a Railway persistent volume."""
        root = project_root or Path(__file__).resolve().parents[1]
        configured_storage_path = os.environ.get("SECRET_KEY_STORAGE_PATH")
        volume_path = os.environ.get("RAILWAY_VOLUME_MOUNT_PATH")
        is_railway = bool(volume_path) or any(
            os.environ.get(name)
            for name in (
                "RAILWAY_ENVIRONMENT",
                "RAILWAY_PROJECT_ID",
                "RAILWAY_SERVICE_ID",
            )
        )
        if configured_storage_path:
            storage_path = Path(configured_storage_path).expanduser()
            if is_railway and not storage_path.is_absolute():
                raise SecretKeyRegistryError(
                    "Persistent application storage must use an absolute path."
                )
            database_path = storage_path / "watermarkguard.sqlite3"
        elif volume_path:
            database_path = Path(volume_path) / "watermarkguard.sqlite3"
        elif is_railway:
            raise SecretKeyRegistryError(
                "Persistent application storage is not configured."
            )
        else:
            configured_path = os.environ.get("WATERMARK_DB_PATH")
            database_path = (
                Path(configured_path).expanduser()
                if configured_path
                else root / ".watermarkguard" / "watermarkguard.sqlite3"
            )

        configured_key = os.environ.get("WATERMARK_ENCRYPTION_KEY")
        if configured_key:
            try:
                encryption_key = configured_key.encode("ascii")
            except UnicodeEncodeError as error:
                raise SecretKeyRegistryError(
                    "WATERMARK_ENCRYPTION_KEY harus berupa Fernet key yang valid."
                ) from error
        else:
            encryption_key = cls._load_or_create_local_encryption_key(database_path)
        return cls(database_path, encryption_key)

    @staticmethod
    def _load_or_create_local_encryption_key(database_path: Path) -> bytes:
        key_path = database_path.with_suffix(database_path.suffix + ".key")
        try:
            key_path.parent.mkdir(parents=True, exist_ok=True)
            try:
                descriptor = os.open(
                    key_path,
                    os.O_CREAT | os.O_EXCL | os.O_WRONLY,
                    0o600,
                )
            except FileExistsError:
                return key_path.read_bytes().strip()

            with os.fdopen(descriptor, "wb") as key_file:
                key_file.write(Fernet.generate_key())
            return key_path.read_bytes().strip()
        except OSError as error:
            raise SecretKeyRegistryError(
                "Encryption key lokal tidak dapat disiapkan."
            ) from error

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path, timeout=30)
        connection.execute("PRAGMA busy_timeout = 30000")
        return connection

    def _initialize_database(self) -> None:
        with closing(self._connect()) as connection, connection:
            table = connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table' AND name = 'watermark_registry'"
            ).fetchone()
            if table is None:
                self._create_registry_table(connection, "watermark_registry")
            else:
                columns = {
                    row[1]
                    for row in connection.execute(
                        "PRAGMA table_info(watermark_registry)"
                    ).fetchall()
                }
                if "watermark_id" in columns:
                    self._migrate_legacy_watermark_ids(connection)
                elif "key_fingerprint" not in columns:
                    raise SecretKeyRegistryError(
                        "Database Secret Key tidak memiliki skema yang didukung."
                    )

            self._create_registry_triggers(connection)

    @staticmethod
    def _create_registry_table(
        connection: sqlite3.Connection,
        table_name: str,
    ) -> None:
        connection.execute(
            f"""
            CREATE TABLE {table_name} (
                key_fingerprint TEXT PRIMARY KEY,
                encrypted_secret_key BLOB NOT NULL,
                owner_identity TEXT NOT NULL,
                algorithm TEXT NOT NULL,
                created_at TEXT NOT NULL,
                status TEXT NOT NULL CHECK (status IN ('pending', 'active', 'failed'))
            )
            """
        )

    def _migrate_legacy_watermark_ids(self, connection: sqlite3.Connection) -> None:
        connection.execute("DROP TABLE IF EXISTS watermark_registry_without_ids")
        self._create_registry_table(connection, "watermark_registry_without_ids")
        connection.execute(
            """
            INSERT INTO watermark_registry_without_ids (
                key_fingerprint, encrypted_secret_key, owner_identity,
                algorithm, created_at, status
            )
            SELECT key_fingerprint, encrypted_secret_key, owner_identity,
                   algorithm, created_at, status
            FROM watermark_registry
            """
        )
        connection.execute("DROP TABLE watermark_registry")
        connection.execute(
            "ALTER TABLE watermark_registry_without_ids RENAME TO watermark_registry"
        )

    @staticmethod
    def _create_registry_triggers(connection: sqlite3.Connection) -> None:
        connection.execute(
            """
            CREATE TRIGGER IF NOT EXISTS prevent_secret_key_identity_update
            BEFORE UPDATE OF key_fingerprint, encrypted_secret_key,
                             owner_identity, algorithm, created_at
            ON watermark_registry
            BEGIN
                SELECT RAISE(ABORT, 'secret key identity is immutable');
            END
            """
        )
        connection.execute(
            """
            CREATE TRIGGER IF NOT EXISTS prevent_secret_key_delete
            BEFORE DELETE ON watermark_registry
            BEGIN
                SELECT RAISE(ABORT, 'secret key records are permanent');
            END
            """
        )
        connection.execute(
            """
            CREATE TRIGGER IF NOT EXISTS validate_secret_key_status_transition
            BEFORE UPDATE OF status ON watermark_registry
            WHEN OLD.status != 'pending'
                 OR NEW.status NOT IN ('active', 'failed')
            BEGIN
                SELECT RAISE(ABORT, 'invalid secret key status transition');
            END
            """
        )

    @staticmethod
    def fingerprint(secret_key: str) -> str:
        return hashlib.sha256(secret_key.encode("utf-8")).hexdigest()

    def create_pending(
        self,
        owner_identity: str,
        algorithm: str = "hybrid-dwt-dct",
    ) -> SecretKeyCredential:
        """Reserve a fresh unique key before embedding starts."""
        for _ in range(20):
            secret_key = secrets.token_urlsafe(32)
            key_fingerprint = self.fingerprint(secret_key)
            created_at = datetime.now(timezone.utc).isoformat()
            try:
                with closing(self._connect()) as connection, connection:
                    connection.execute("BEGIN IMMEDIATE")
                    connection.execute(
                        """
                        INSERT INTO watermark_registry (
                            key_fingerprint,
                            encrypted_secret_key,
                            owner_identity,
                            algorithm,
                            created_at,
                            status
                        ) VALUES (?, ?, ?, ?, ?, 'pending')
                        """,
                        (
                            key_fingerprint,
                            self._fernet.encrypt(secret_key.encode("utf-8")),
                            owner_identity,
                            algorithm,
                            created_at,
                        ),
                    )
                return SecretKeyCredential(secret_key, key_fingerprint)
            except sqlite3.IntegrityError:
                continue
            except sqlite3.Error as error:
                raise SecretKeyRegistryError(
                    "Secret Key tidak dapat disimpan ke database persisten."
                ) from error

        raise SecretKeyRegistryError(
            "Tidak berhasil membuat Secret Key unik setelah beberapa percobaan."
        )

    def activate(self, key_fingerprint: str) -> None:
        self._set_status(key_fingerprint, "active")

    def mark_failed(self, key_fingerprint: str) -> None:
        self._set_status(key_fingerprint, "failed")

    def _set_status(self, key_fingerprint: str, status: str) -> None:
        try:
            with closing(self._connect()) as connection, connection:
                cursor = connection.execute(
                    "UPDATE watermark_registry SET status = ? WHERE key_fingerprint = ?",
                    (status, key_fingerprint),
                )
                if cursor.rowcount != 1:
                    raise SecretKeyRegistryError("Secret Key tidak ditemukan.")
        except sqlite3.Error as error:
            raise SecretKeyRegistryError(
                "Status Secret Key tidak dapat disimpan."
            ) from error

    def is_registered(self, secret_key: str) -> bool:
        try:
            with closing(self._connect()) as connection:
                row = connection.execute(
                    """
                    SELECT 1 FROM watermark_registry
                    WHERE key_fingerprint = ? AND status = 'active'
                    """,
                    (self.fingerprint(secret_key),),
                ).fetchone()
            return row is not None
        except sqlite3.Error as error:
            raise SecretKeyRegistryError(
                "Secret Key tidak dapat divalidasi melalui database."
            ) from error
