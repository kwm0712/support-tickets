from __future__ import annotations

import os
import unittest
from pathlib import Path

from architecture import TenantContext
from postgres_repository import PostgresRepository


class PostgresRepositoryV03Tests(unittest.TestCase):
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
        with cls.psycopg.connect(cls.database_url, autocommit=True) as connection:
            connection.execute(migration_sql)

    def setUp(self) -> None:
        with self.psycopg.connect(self.database_url) as connection:
            connection.execute(
                "DELETE FROM audit_log WHERE tenant_key IN (%s, %s)",
                ("repo-a", "repo-b"),
            )
            connection.execute(
                "DELETE FROM tickets WHERE tenant_key IN (%s, %s)",
                ("repo-a", "repo-b"),
            )

    def test_repository_is_tenant_scoped(self) -> None:
        repo_a = PostgresRepository(self.database_url, TenantContext("repo-a"))
        repo_b = PostgresRepository(self.database_url, TenantContext("repo-b"))
        self.assertTrue(repo_a.healthcheck())

        repo_a.ensure_tenant("Repository Tenant A")
        repo_b.ensure_tenant("Repository Tenant B")

        ticket_a = repo_a.create_ticket(
            subject="A",
            description="Nur Tenant A",
            customer="Compelec",
            priority="Hoch",
            actor="admin-a",
        )
        ticket_b = repo_b.create_ticket(
            subject="B",
            description="Nur Tenant B",
            customer="Compelec",
            priority="Mittel",
            actor="admin-b",
        )

        tickets_a = repo_a.list_tickets()
        tickets_b = repo_b.list_tickets()
        self.assertEqual([item["ticket_no"] for item in tickets_a], [ticket_a])
        self.assertEqual([item["ticket_no"] for item in tickets_b], [ticket_b])
        self.assertNotEqual(ticket_a, ticket_b)

        with self.psycopg.connect(self.database_url) as connection:
            audit_a = connection.execute(
                "SELECT COUNT(*) FROM audit_log WHERE tenant_key = %s AND entity_id = %s",
                ("repo-a", ticket_a),
            ).fetchone()[0]
            audit_b = connection.execute(
                "SELECT COUNT(*) FROM audit_log WHERE tenant_key = %s AND entity_id = %s",
                ("repo-b", ticket_b),
            ).fetchone()[0]
            self.assertEqual(audit_a, 1)
            self.assertEqual(audit_b, 1)


if __name__ == "__main__":
    unittest.main()
