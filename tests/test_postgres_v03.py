from __future__ import annotations

import os
import unittest
from pathlib import Path


class PostgresV03IntegrationTests(unittest.TestCase):
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
        migration_path = (
            Path(__file__).resolve().parents[1]
            / "migrations"
            / "postgres"
            / "0001_v03_core.sql"
        )
        migration_sql = migration_path.read_text(encoding="utf-8")
        with psycopg.connect(cls.database_url, autocommit=True) as connection:
            connection.execute(migration_sql)

    def test_pgvector_extension_and_core_tables_exist(self) -> None:
        with self.psycopg.connect(self.database_url) as connection:
            extension = connection.execute(
                "SELECT extname FROM pg_extension WHERE extname = 'vector'"
            ).fetchone()
            self.assertEqual(extension[0], "vector")

            rows = connection.execute(
                """
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'public'
                  AND table_name IN (
                    'tenants', 'tickets', 'document_chunks',
                    'assistant_runs', 'assistant_evidence', 'audit_log'
                  )
                """
            ).fetchall()
            names = {row[0] for row in rows}
            self.assertEqual(
                names,
                {
                    "tenants",
                    "tickets",
                    "document_chunks",
                    "assistant_runs",
                    "assistant_evidence",
                    "audit_log",
                },
            )

    def test_ticket_numbers_are_unique_per_tenant_not_globally(self) -> None:
        with self.psycopg.connect(self.database_url) as connection:
            connection.execute(
                "INSERT INTO tenants (tenant_key, display_name) VALUES (%s, %s) "
                "ON CONFLICT (tenant_key) DO NOTHING",
                ("tenant-a", "Tenant A"),
            )
            connection.execute(
                "INSERT INTO tenants (tenant_key, display_name) VALUES (%s, %s) "
                "ON CONFLICT (tenant_key) DO NOTHING",
                ("tenant-b", "Tenant B"),
            )
            connection.execute(
                "DELETE FROM tickets WHERE tenant_key IN (%s, %s)",
                ("tenant-a", "tenant-b"),
            )
            for tenant_key in ("tenant-a", "tenant-b"):
                connection.execute(
                    """
                    INSERT INTO tickets (
                        tenant_key, ticket_no, subject, description, customer,
                        status, priority, created_by
                    ) VALUES (%s, %s, %s, %s, %s, 'Offen', 'Mittel', %s)
                    """,
                    (
                        tenant_key,
                        "CCS-2026-00001",
                        "Test",
                        "Mandantenprüfung",
                        "Compelec",
                        "test",
                    ),
                )
            connection.commit()

            count = connection.execute(
                "SELECT COUNT(*) FROM tickets WHERE ticket_no = %s",
                ("CCS-2026-00001",),
            ).fetchone()[0]
            self.assertEqual(count, 2)


if __name__ == "__main__":
    unittest.main()
