"""
Private Local File Storage for DocTrust.

Enforces:
- Unguessable 64-character random hexadecimal storage keys.
- Sharded filesystem layout: <STORAGE_ROOT>/ab/cd/<storage_key>.
- Robust resolved-path containment check via Path.is_relative_to() to prevent directory traversal.
- Restrictive permissions (0o600 for files, 0o700 for directories).
- Private isolation: no public URLs and stored outside source/static/media trees.
- Explicit cleanup helpers for aborted operations.
"""

import os
import re
import secrets
from pathlib import Path
from django.conf import settings

STORAGE_KEY_REGEX = re.compile(r"^[0-9a-f]{64}$")


class StorageError(Exception):
    """Base exception for private document storage errors."""
    pass


class PathTraversalError(StorageError):
    """Raised when a resolved storage path escapes DOCUMENT_STORAGE_ROOT."""
    pass


class InvalidStorageKeyError(StorageError):
    """Raised when an invalid storage key format is provided."""
    pass


class PrivateDocumentStorage:
    """
    Manages encrypted/private physical document storage on local filesystem.
    Can be swapped with a private object-store adapter (e.g. S3/GCS) in future phases.
    """

    def __init__(self, root_path=None):
        raw_root = root_path or getattr(settings, "DOCUMENT_STORAGE_ROOT", None)
        if not raw_root:
            raise StorageError("DOCUMENT_STORAGE_ROOT setting is not configured.")
        self.root_path = Path(raw_root).resolve()
        self.temp_path = (self.root_path / "tmp").resolve()
        self._ensure_directories()

    def _ensure_directories(self):
        """Ensure storage root and temp directory exist with restrictive permissions."""
        self.root_path.mkdir(mode=0o700, parents=True, exist_ok=True)
        self.temp_path.mkdir(mode=0o700, parents=True, exist_ok=True)

    @staticmethod
    def generate_storage_key() -> str:
        """Generate a cryptographically secure 64-character lowercase hex storage key."""
        return secrets.token_hex(32)

    def validate_key(self, storage_key: str):
        """Validate key format strictly against ^[0-9a-f]{64}$."""
        if not isinstance(storage_key, str) or not STORAGE_KEY_REGEX.match(storage_key):
            raise InvalidStorageKeyError(f"Invalid storage key format: {storage_key!r}")

    def get_path(self, storage_key: str) -> Path:
        """
        Derive sharded filesystem path: <root>/ab/cd/<storage_key>
        Enforces proper resolved-path containment checking.
        """
        self.validate_key(storage_key)
        shard1 = storage_key[:2]
        shard2 = storage_key[2:4]

        candidate = (self.root_path / shard1 / shard2 / storage_key).resolve()

        # Robust containment check: ensure candidate is strictly inside root_path
        try:
            candidate.relative_to(self.root_path)
        except ValueError:
            raise PathTraversalError(f"Storage path escapes root directory: {candidate}")

        return candidate

    def save_stream(self, file_stream, storage_key: str) -> int:
        """
        Stream contents from file_stream (UploadedFile, file handle, or bytes)
        into sharded location with 0600 permissions.
        Returns total bytes written.
        """
        target_path = self.get_path(storage_key)
        target_path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)

        # Write to atomic temp file inside shard first, then rename
        tmp_target = target_path.with_suffix(".tmp")
        bytes_written = 0

        try:
            with open(tmp_target, "wb") as dest:
                if hasattr(file_stream, "chunks"):
                    for chunk in file_stream.chunks():
                        dest.write(chunk)
                        bytes_written += len(chunk)
                elif hasattr(file_stream, "read"):
                    while True:
                        chunk = file_stream.read(64 * 1024)
                        if not chunk:
                            break
                        dest.write(chunk)
                        bytes_written += len(chunk)
                elif isinstance(file_stream, (bytes, bytearray)):
                    dest.write(file_stream)
                    bytes_written = len(file_stream)
                else:
                    raise StorageError("Unsupported stream type for save_stream.")

            # Set restrictive permissions (read/write by owner only)
            try:
                os.chmod(tmp_target, 0o600)
            except OSError:
                pass  # Windows ACLs handle permissions through parent folder

            # Atomic replace
            os.replace(tmp_target, target_path)
            return bytes_written

        except Exception as exc:
            if tmp_target.exists():
                try:
                    tmp_target.unlink()
                except OSError:
                    pass
            raise StorageError(f"Failed to save document stream: {exc}") from exc

    def open(self, storage_key: str):
        """Open a binary file handle for streaming. Caller must close handle."""
        target_path = self.get_path(storage_key)
        if not target_path.is_file():
            raise FileNotFoundError(f"Stored file for key not found.")
        return open(target_path, "rb")

    def exists(self, storage_key: str) -> bool:
        """Return True if the file exists on disk and is a regular file."""
        try:
            target_path = self.get_path(storage_key)
            return target_path.is_file()
        except (InvalidStorageKeyError, PathTraversalError):
            return False

    def delete(self, storage_key: str) -> bool:
        """
        Securely delete physical file from disk.
        Returns True if file was removed, False if it did not exist.
        """
        target_path = self.get_path(storage_key)
        if target_path.is_file():
            try:
                target_path.unlink()
                # Clean up empty shard directories if empty
                try:
                    target_path.parent.rmdir()
                    target_path.parent.parent.rmdir()
                except OSError:
                    pass
                return True
            except OSError as exc:
                raise StorageError(f"Failed to delete stored file: {exc}") from exc
        return False

    def get_file_size(self, storage_key: str) -> int:
        """Return size in bytes of stored file."""
        target_path = self.get_path(storage_key)
        if not target_path.is_file():
            raise FileNotFoundError(f"Stored file for key not found.")
        return target_path.stat().st_size


# Default singleton instance
default_storage = PrivateDocumentStorage()


def get_user_storage_usage(user) -> int:
    """Return total bytes of active and archived documents owned by user."""
    from django.db.models import Sum
    from documents.models import Document
    res = Document.objects.filter(
        owner=user,
        status__in=[Document.Status.ACTIVE, Document.Status.ARCHIVED],
    ).aggregate(total=Sum("size"))
    return res["total"] or 0

