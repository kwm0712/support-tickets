from __future__ import annotations

import importlib
import os
import tempfile
import unittest
from pathlib import Path


class CoreSmokeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.temp_dir = tempfile.TemporaryDirectory()
        os.environ["CCS_DATA_DIR"] = str(Path(cls.temp_dir.name) / "data")

        import ccs_core

        cls.core = importlib.reload(ccs_core)
        cls.core.initialize_database()

    @classmethod
    def tearDownClass(cls) -> None:
        cls.temp_dir.cleanup()

    def test_admin_login(self) -> None:
        user = self.core.authenticate("admin", "Compelec-Start!")
        self.assertIsNotNone(user)
        self.assertEqual(user["role"], "admin")
        self.assertIsNone(self.core.authenticate("admin", "falsch"))

    def test_ticket_and_metrics(self) -> None:
        ticket_no = self.core.create_ticket(
            subject="Testticket",
            description="Datenbank Verbindung prüfen",
            customer="Compelec",
            priority="Hoch",
            actor="admin",
        )
        self.assertTrue(ticket_no.startswith("CCS-"))
        self.assertEqual(len(self.core.list_tickets()), 1)
        self.assertEqual(self.core.get_metrics()["critical"], 1)

    def test_knowledge_search(self) -> None:
        results = self.core.search_knowledge("Datenbank Verbindung")
        self.assertGreaterEqual(len(results), 1)
        self.assertIn("Datenbank", results[0]["title"])


if __name__ == "__main__":
    unittest.main()
