import os
import unittest

import psycopg

from repository import PostgresCaseStore, StoreConfig


@unittest.skipUnless(
    os.getenv("PFARRBUERO_TEST_DATABASE_URL"),
    "PostgreSQL integration test requires PFARRBUERO_TEST_DATABASE_URL",
)
class PostgresRepositoryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.dsn = os.environ["PFARRBUERO_TEST_DATABASE_URL"]
        cls.tenant_id = os.environ["PFARRBUERO_TENANT_ID"]
        cls.org_unit_id = os.environ["PFARRBUERO_ORG_UNIT_ID"]
        cls.user_id = os.environ["PFARRBUERO_USER_ID"]
        cls.store = PostgresCaseStore(
            StoreConfig(
                dsn=cls.dsn,
                tenant_id=cls.tenant_id,
                org_unit_id=cls.org_unit_id,
                actor_user_id=cls.user_id,
            )
        )

    def test_health_check_requires_membership_and_case_read(self):
        self.store.health_check()

    def test_list_cases_hides_foreign_tenant_and_seelsorge_secret(self):
        rows = self.store.list_cases()
        subjects = [row[1] for row in rows]
        self.assertIn("Testfall A", subjects)
        self.assertFalse(any("Testfall B" in subject for subject in subjects))
        self.assertFalse(any("Vertraulicher Seelsorgevorgang" in subject for subject in subjects))

    def test_create_case_and_audit_event_are_atomic(self):
        subject = "Automatisierter V2.0 Integrationstest"
        self.store.create_case("Test", subject)
        with psycopg.connect(self.dsn) as conn:
            conn.execute(
                "SELECT set_config('app.tenant_id', %s, true)",
                (self.tenant_id,),
            )
            case = conn.execute(
                "SELECT id FROM parish_cases WHERE tenant_id=%s AND subject=%s",
                (self.tenant_id, subject),
            ).fetchone()
            self.assertIsNotNone(case)
            audit = conn.execute(
                """
                SELECT count(*) FROM parish_audit_events
                WHERE tenant_id=%s AND entity_type='parish_case'
                  AND entity_id=%s AND event_type='case.created'
                """,
                (self.tenant_id, str(case[0])),
            ).fetchone()[0]
            self.assertEqual(audit, 1)

    def test_read_only_role_cannot_create_cases(self):
        readonly_store = PostgresCaseStore(
            StoreConfig(
                dsn=self.dsn,
                tenant_id=self.tenant_id,
                org_unit_id=self.org_unit_id,
                actor_user_id="10000000-0000-0000-0000-000000000103",
            )
        )
        with self.assertRaises(PermissionError):
            readonly_store.create_case("Test", "Darf nicht angelegt werden")

    def test_missing_tenant_context_returns_no_cases(self):
        with psycopg.connect(self.dsn) as conn:
            count = conn.execute("SELECT count(*) FROM parish_cases").fetchone()[0]
            self.assertEqual(count, 0)


if __name__ == "__main__":
    unittest.main()
