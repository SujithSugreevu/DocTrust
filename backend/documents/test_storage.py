"""Focused tests for private document storage initialization and I/O."""

from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory

from django.test import SimpleTestCase, override_settings
from django.utils.functional import SimpleLazyObject

from documents.storage import (
    InvalidStorageKeyError,
    PrivateDocumentStorage,
    StorageError,
    default_storage,
)


class PrivateDocumentStorageTests(SimpleTestCase):
    def test_default_storage_does_not_touch_filesystem_during_import(self):
        self.assertIsInstance(default_storage, SimpleLazyObject)

    def test_initializes_missing_root_and_temp_directories(self):
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "private" / "documents"
            storage = PrivateDocumentStorage(root)

            self.assertTrue(storage.root_path.is_dir())
            self.assertTrue(storage.temp_path.is_dir())

    def test_save_open_exists_and_delete_round_trip(self):
        with TemporaryDirectory() as temp_dir:
            storage = PrivateDocumentStorage(Path(temp_dir) / "documents")
            storage_key = "a" * 64
            contents = b"private document contents"

            written = storage.save_stream(BytesIO(contents), storage_key)

            self.assertEqual(written, len(contents))
            self.assertTrue(storage.exists(storage_key))
            with storage.open(storage_key) as stored_file:
                self.assertEqual(stored_file.read(), contents)
            self.assertTrue(storage.delete(storage_key))
            self.assertFalse(storage.exists(storage_key))

    def test_invalid_storage_configuration_fails_when_storage_is_used(self):
        with override_settings(DOCUMENT_STORAGE_ROOT=""):
            with self.assertRaises(StorageError):
                PrivateDocumentStorage()

    def test_invalid_storage_key_is_rejected(self):
        with TemporaryDirectory() as temp_dir:
            storage = PrivateDocumentStorage(Path(temp_dir) / "documents")

            with self.assertRaises(InvalidStorageKeyError):
                storage.get_path("../outside")
