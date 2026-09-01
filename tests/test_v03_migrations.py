from __future__ import annotations

import os
import sqlite3
import tempfile
import unittest
import uuid
from pathlib import Path

from migrate_v02_sqlite_to_v03_postgres import migrate_v02_sqlite_to_v03_postgres
from postgres_migrations import apply_postgres_migrations


class V03MigrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.database_url = os.getenv("CCS_TEST_POSTGRES_URL", "").strip()
        if not cls.database_url:
            raise unittest.SkipTest("CCS_TEST_POSTGRES_URL ist nicht gesetzt.")
        try:
            import psycopg
        except ImportError as exc:
            raise unittest.SkipTest("psycopg ist nicht installiert.") from exc
        cls.psycopg = psycopg

    def test_postgres_migration_runner_is_idempotent(self) -> None:
        apply_postgres_migrations(self.database_url)
        second_run = apply_postgres_migrations(self.database_url)
        self.assertEqual(second_run, [])
        with self.psycopg.connect(self.database_url) as connection:
            versions = {
                row[0]
                for row in connection.execute(
                    "SELECT version FROM schema_migrations ORDER BY version"
                ).fetchall()
            }
        self.assertIn("0001_v03_core", versions)
        self.assertIn("0002_v03_hybrid_retrieval", versions)

    def test_v02_sqlite_core_data_can_be_migrated(self) -> None:
        tenant = f"migration-{uuid.uuid4().hex[:10]}"
        with tempfile.TemporaryDirectory() as temp_dir:
            sqlite_path = Path(temp_dir) / "ccs_support.db"
            source = sqlite3.connect(sqlite_path)
            source.executescript(
                """
                CREATE TABLE users (
                    id INTEGER PRIMARY KEY,
                    username TEXT,
                    display_name TEXT,
                    role TEXT,
                    password_salt TEXT,
                    password_hash TEXT,
                    active INTEGER,
                    created_at TEXT
                );
                CREATE TABLE tickets (
                    id INTEGER PRIMARY KEY,
                    ticket_no TEXT,
                    subject TEXT,
                    description TEXT,
                    customer TEXT,
                    status TEXT,
                    priority TEXT,
                    assignee TEXT,
                    created_by TEXT,
                    created_at TEXT,
                    updated_at TEXT
                );
                CREATE TABLE knowledge_articles (
                    id INTEGER PRIMARY KEY,
                    title TEXT,
                    category TEXT,
                    content TEXT,
                    source TEXT,
                    created_by TEXT,
                    created_at TEXT,
                    approval_status TEXT,
                    privacy_level TEXT,
                    updated_at TEXT
                );
                CREATE TABLE audit_log (
                    id INTEGER PRIMARY KEY,
                    actor TEXT,
                    action TEXT,
                    entity_type TEXT,
                    entity_id TEXT,
                    details TEXT,
                    created_at TEXT
                );
                """
            )
            source.execute(
                "INSERT INTO users VALUES (1, 'admin', 'Admin', 'admin', 'aa', 'bb', 1, '2026-08-08T00:00:00Z')"
            )
            source.execute(
                """
                INSERT INTO tickets VALUES (
                    1, 'CCS-2026-00001', 'Migration', 'Test', 'Compelec',
                    'Offen', 'Hoch', NULL, 'admin',
                    '2026-08-08T00:00:00Z', '2026-08-08T00:00:00Z'
                )
                """
            )
            source.execute(
                """
                INSERT INTO knowledge_articles VALUES (
                    1, 'Migration Wissen', 'Support', 'Datenbankdienst pruefen',
                    'Testquelle', 'admin', '2026-08-08T00:00:00Z',
                    'approved', 'internal', '2026-08-08T00:00:00Z'
                )
                """
            )
            source.execute(
                """
                INSERT INTO audit_log VALUES (
                    1, 'admin', 'CREATE', 'ticket', 'CCS-2026-00001',
                    'Migrationstest', '2026-08-08T00:00:00Z'
                )
                """
            )
            source.commit()
            source.close()

            dry_run = migrate_v02_sqlite_to_v03_postgres(
                sqlite_path=sqlite_path,
                database_url=self.database_url,
                tenant_key=tenant,
                tenant_name="Migration Test",
                dry_run=True,
            )
            self.assertEqual(dry_run.tickets, 1)
            self.assertEqual(dry_run.articles, 1)

            summary = migrate_v02_sqlite_to_v03_postgres(
                sqlite_path=sqlite_path,
                database_url=self.database_url,
                tenant_key=tenant,
                tenant_name="Migration Test",
            )
            self.assertEqual(summary.users, 1)
            self.assertEqual(summary.tickets, 1)
            self.assertEqual(summary.articles, 1)
            self.assertEqual(summary.audit_entries, 1)

            with self.psycopg.connect(self.database_url) as connection:
                ticket_count = connection.execute(
                    "SELECT COUNT(*) FROM tickets WHERE tenant_key = %s",
                    (tenant,),
                ).fetchone()[0]
                article_count = connection.execute(
                    "SELECT COUNT(*) FROM knowledge_articles WHERE tenant_key = %s",
                    (tenant,),
                ).fetchone()[0]
                embedding_model = connection.execute(
                    "SELECT embedding_model FROM knowledge_articles WHERE tenant_key = %s",
                    (tenant,),
                ).fetchone()[0]
            self.assertEqual(ticket_count, 1)
            self.assertEqual(article_count, 1)
            self.assertEqual(embedding_model, "ccs-local-hash-v1")


if __name__ == "__main__":
    unittest.main()
