from __future__ import annotations

import os
import unittest
import uuid

from architecture import AuthorizationError, TenantContext, UserContext
from postgres_migrations import apply_postgres_migrations
from postgres_repository import PostgresRepository
from support_service import SupportService


class V03ServiceIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.database_url = os.getenv("CCS_TEST_POSTGRES_URL", "").strip()
        if not cls.database_url:
            raise unittest.SkipTest("CCS_TEST_POSTGRES_URL ist nicht gesetzt.")
        apply_postgres_migrations(cls.database_url)

    def make_service(self, role: str, tenant_id: str, username: str) -> SupportService:
        repo = PostgresRepository(self.database_url, TenantContext(tenant_id))
        service = SupportService(
            repo,
            UserContext(username=username, role=role, tenant_id=tenant_id),
        )
        service.ensure_tenant(f"Test {tenant_id}")
        return service

    def test_article_governance_hybrid_retrieval_and_assistant_logging(self) -> None:
        tenant = f"svc-{uuid.uuid4().hex[:10]}"
        admin = self.make_service("admin", tenant, "admin")
        article_id = admin.add_article(
            title="VPN Zertifikatsprüfung",
            category="Netzwerk",
            content="Bei VPN Fehlern Zertifikatsgültigkeit und Benutzerkonto prüfen.",
            source="Support-Handbuch",
            privacy_level="internal",
        )
        self.assertEqual(
            admin.search_evidence("VPN Zertifikat", privacy_level="internal"),
            [],
        )

        admin.review_article(article_id, "approved")
        evidence = admin.search_evidence("VPN Zertifikat", privacy_level="internal")
        self.assertTrue(any(item["source_id"] == article_id for item in evidence))
        self.assertTrue(any(item["vector_score"] > 0 for item in evidence))

        response = admin.ask_assistant(
            question="Was prüfe ich bei einem VPN Zertifikatsfehler?",
            privacy_level="internal",
        )
        self.assertGreater(response.run_id, 0)
        self.assertTrue(response.evidence)
        self.assertEqual(admin.list_assistant_runs(limit=1)[0]["id"], response.run_id)

        agent = self.make_service("agent", tenant, "support")
        with self.assertRaises(AuthorizationError):
            agent.search_evidence("VPN", privacy_level="confidential")

    def test_document_requires_approval_and_is_tenant_isolated(self) -> None:
        tenant_a = f"doc-a-{uuid.uuid4().hex[:8]}"
        tenant_b = f"doc-b-{uuid.uuid4().hex[:8]}"
        admin_a = self.make_service("admin", tenant_a, "admin-a")
        admin_b = self.make_service("admin", tenant_b, "admin-b")

        document_id = admin_a.import_document(
            filename="datenbank.txt",
            data=(
                b"Bei einem Datenbank Verbindungsfehler zuerst Dienststatus, Netzwerk "
                b"und Zugangsdaten pruefen."
            ),
            category="Datenbank",
            source="Pilot-Handbuch",
            privacy_level="internal",
        )
        self.assertEqual(
            admin_a.search_evidence("Datenbank Verbindungsfehler", privacy_level="internal"),
            [],
        )
        admin_a.review_document(document_id, "approved")
        evidence_a = admin_a.search_evidence(
            "Datenbank Verbindungsfehler", privacy_level="internal"
        )
        self.assertTrue(
            any(item["source_type"] == "document_chunk" for item in evidence_a)
        )
        self.assertEqual(
            admin_b.search_evidence("Datenbank Verbindungsfehler", privacy_level="internal"),
            [],
        )

    def test_viewer_cannot_create_ticket(self) -> None:
        tenant = f"viewer-{uuid.uuid4().hex[:10]}"
        viewer = self.make_service("viewer", tenant, "viewer")
        with self.assertRaises(AuthorizationError):
            viewer.create_ticket(
                subject="Nicht erlaubt",
                description="Viewer darf nicht schreiben",
                customer="Compelec",
                priority="Mittel",
            )


if __name__ == "__main__":
    unittest.main()
