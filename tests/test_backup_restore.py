from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from backup_restore import sha256_file, verify_backup


class BackupRestoreTests(unittest.TestCase):
    def test_sha256_file_is_stable(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "backup.dump"
            path.write_bytes(b"compelec-one-backup")
            self.assertEqual(
                sha256_file(path),
                "4953049899e537af549860eaa0758e22099de6f5095ce8999b28e5bc5381ff5e",
            )

    @patch("backup_restore._require_tool", return_value="pg_restore")
    @patch("backup_restore.subprocess.run")
    def test_verify_backup_checks_checksum_and_pg_restore_list(self, run, require_tool) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            dump = root / "backup.dump"
            manifest = root / "backup.manifest.json"
            dump.write_bytes(b"valid-backup")
            manifest.write_text(
                json.dumps({"sha256": sha256_file(dump)}), encoding="utf-8"
            )

            verify_backup(dump, manifest)

            require_tool.assert_called_once_with("pg_restore")
            run.assert_called_once()

    @patch("backup_restore._require_tool", return_value="pg_restore")
    def test_verify_backup_rejects_checksum_mismatch(self, require_tool) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            dump = root / "backup.dump"
            manifest = root / "backup.manifest.json"
            dump.write_bytes(b"tampered")
            manifest.write_text(json.dumps({"sha256": "0" * 64}), encoding="utf-8")

            with self.assertRaises(RuntimeError):
                verify_backup(dump, manifest)


if __name__ == "__main__":
    unittest.main()
