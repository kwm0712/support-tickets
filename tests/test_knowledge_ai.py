from __future__ import annotations

import importlib
import os
import tempfile
import unittest
from pathlib import Path


class KnowledgeAiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        os.environ["CCS_DATA_DIR"] = str(Path(self.temp_dir.name) / "data")

        import ccs_core
        import knowledge_ai

        self.core = importlib.reload(ccs_core)
        self.ai = importlib.reload(knowledge_ai)
        self.core.initialize_database()
        self.ai.initialize_knowledge_ai()

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_draft_article_is_not_used_before_approval(self) -> None:
        article_id = self.ai.add_governed_article(
            title="Spezialprüfung Druckdienst",
            category="Support",
            content="Den Druckdienst neu starten und die Warteschlange kontrollieren.",
            source="Testquelle",
            approval_status="draft",
            privacy_level="internal",
            actor="admin",
        )

        self.assertEqual(
            self.ai.search_governed_knowledge("Druckdienst", privacy_level="internal"),
            [],
        )

        self.ai.set_article_status(article_id, "approved", "admin")
        results = self.ai.search_governed_knowledge("Druckdienst", privacy_level="internal")
        self.assertEqual(results[0]["id"], article_id)

    def test_document_requires_approval_for_retrieval(self) -> None:
        document_id = self.ai.import_document(
            filename="support.txt",
            data=(
                b"Bei einem VPN Verbindungsfehler zuerst Erreichbarkeit, Benutzerkonto "
                b"und Zertifikatsgueltigkeit pruefen."
            ),
            category="Netzwerk",
            source="Support-Handbuch",
            privacy_level="internal",
            actor="admin",
        )

        self.assertEqual(
            self.ai.retrieve_evidence("VPN Verbindungsfehler", privacy_level="internal"),
            [],
        )

        self.ai.set_document_status(document_id, "approved", "admin")
        evidence = self.ai.retrieve_evidence("VPN Verbindungsfehler", privacy_level="internal")
        self.assertGreaterEqual(len(evidence), 1)
        self.assertEqual(evidence[0].title, "support.txt")

    def test_privacy_level_filters_confidential_sources(self) -> None:
        article_id = self.ai.add_governed_article(
            title="Vertraulicher Administrationshinweis",
            category="Administration",
            content="Geheimes Wartungskennwort niemals in einem Ticket dokumentieren.",
            source="Interne Richtlinie",
            approval_status="approved",
            privacy_level="confidential",
            actor="admin",
        )

        internal_results = self.ai.search_governed_knowledge(
            "Wartungskennwort", privacy_level="internal"
        )
        confidential_results = self.ai.search_governed_knowledge(
            "Wartungskennwort", privacy_level="confidential"
        )
        self.assertEqual(internal_results, [])
        self.assertEqual(confidential_results[0]["id"], article_id)

    def test_assistant_run_is_logged_with_evidence(self) -> None:
        article_id = self.ai.add_governed_article(
            title="Datenbankdienst prüfen",
            category="Datenbank",
            content="Dienststatus und Netzwerkverbindung kontrollieren.",
            source="Support-Handbuch",
            approval_status="approved",
            privacy_level="internal",
            actor="admin",
        )
        response = self.ai.generate_assistant_answer(
            question="Wie prüfe ich den Datenbankdienst?",
            privacy_level="internal",
            actor="support",
        )

        self.assertGreater(response.run_id, 0)
        self.assertEqual(response.provider, "local-evidence")
        self.assertTrue(any(item.source_id == article_id for item in response.evidence))
        self.assertEqual(self.ai.list_assistant_runs(limit=1)[0]["id"], response.run_id)

    def test_unknown_provider_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            self.ai.generate_assistant_answer(
                question="Testfrage",
                privacy_level="internal",
                actor="admin",
                provider_name="external-provider",
            )


if __name__ == "__main__":
    unittest.main()
