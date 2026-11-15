from __future__ import annotations

import os
import shutil
import tempfile
import unittest
import uuid
from pathlib import Path
from urllib.parse import urlparse, urlunparse

import psycopg
from psycopg import sql

from backup_restore import create_backup, restore_backup, verify_backup


DATABASE_URL = os.getenv("CCS_TEST_POSTGRES_URL", "").strip()
TOOLS_AVAILABLE = bool(shutil.which("pg_dump") and shutil.which("pg_restore"))


def _database_url(base_url: str, database: str) -> str:
    parsed = urlparse(base_url)
    return urlunparse(parsed._replace(path=f"/{database}"))


@unittest.skipUnless(DATABASE_URL and TOOLS_AVAILABLE, "PostgreSQL-Testdienst oder pg_dump/pg_restore nicht verfügbar")
class BackupRestorePostgresIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.suffix = uuid.uuid4().hex[:10]
        cls.source_name = f"ccs_backup_src_{cls.suffix}"
        cls.target_name = f"ccs_backup_dst_{cls.suffix}"
        parsed = urlparse(DATABASE_URL)
        cls.admin_url = urlunparse(parsed._replace(path="/postgres"))
        cls.source_url = _database_url(DATABASE_URL, cls.source_name)
        cls.target_url = _database_url(DATABASE_URL, cls.target_name)

        with psycopg.connect(cls.admin_url, autocommit=True) as connection:
            connection.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(cls.source_name)))
            connection.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(cls.target_name)))

        with psycopg.connect(cls.source_url) as connection:
            connection.execute(
                "CREATE TABLE release_restore_probe (id integer PRIMARY KEY, marker text NOT NULL)"
            )
            connection.execute(
                "INSERT INTO release_restore_probe (id, marker) VALUES (1, 'COMPELEC-RESTORE-OK')"
            )

    @classmethod
    def tearDownClass(cls):
        if not DATABASE_URL or not TOOLS_AVAILABLE:
            return
        with psycopg.connect(cls.admin_url, autocommit=True) as connection:
            connection.execute(
                sql.SQL("DROP DATABASE IF EXISTS {} WITH (FORCE)").format(sql.Identifier(cls.target_name))
            )
            connection.execute(
                sql.SQL("DROP DATABASE IF EXISTS {} WITH (FORCE)").format(sql.Identifier(cls.source_name))
            )

    def test_real_pg_dump_verify_and_restore_roundtrip(self):
        with tempfile.TemporaryDirectory() as tmp:
            dump_path, manifest_path = create_backup(self.source_url, Path(tmp))
            self.assertTrue(dump_path.is_file())
            self.assertTrue(manifest_path.is_file())

            verify_backup(dump_path, manifest_path)
            restore_backup(self.target_url, dump_path, manifest_path)

            with psycopg.connect(self.target_url) as connection:
                row = connection.execute(
                    "SELECT marker FROM release_restore_probe WHERE id = 1"
                ).fetchone()
            self.assertEqual(row[0], "COMPELEC-RESTORE-OK")


if __name__ == "__main__":
    unittest.main()
