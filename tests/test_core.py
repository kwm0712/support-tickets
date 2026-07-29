from __future__ import annotations

import importlib
import os
import tempfile
import unittest
from pathlib import Path

PASSWORD_ENV_VARS = (
    "CCS_ADMIN_PASSWORD",
    "CCS_SUPPORT_PASSWORD",
    "CCS_VIEWER_PASSWORD",
)


def clear_security_environment() -> None:
    os.environ.pop("CCS_LICENSE_MODE", None)
    os.environ.pop("CCS_LICENSE_EXPIRES", None)
    for variable in PASSWORD_ENV_VARS:
        os.environ.pop(variable, None)


class CoreSmokeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        clear_security_environment()
        cls.temp_dir = tempfile.TemporaryDirectory()
        os.environ["CCS_DATA_DIR"] = str(Path(cls.temp_dir.name) / "data")

        import ccs_core

        cls.core = importlib.reload(ccs_core)
        cls.core.initialize_database()

    @classmethod
    def tearDownClass(cls) -> None:
        cls.temp_dir.cleanup()
        os.environ.pop("CCS_DATA_DIR", None)
        clear_security_environment()

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


class LicensedCredentialTests(unittest.TestCase):
    def setUp(self) -> None:
        clear_security_environment()
        self.temp_dir = tempfile.TemporaryDirectory()
        os.environ["CCS_DATA_DIR"] = str(Path(self.temp_dir.name) / "data")

    def tearDown(self) -> None:
        self.temp_dir.cleanup()
        os.environ.pop("CCS_DATA_DIR", None)
        clear_security_environment()

    @staticmethod
    def reload_core():
        import ccs_core

        return importlib.reload(ccs_core)

    def test_licensed_mode_requires_explicit_passwords(self) -> None:
        os.environ["CCS_LICENSE_MODE"] = "licensed"
        core = self.reload_core()

        with self.assertRaisesRegex(RuntimeError, "CCS_ADMIN_PASSWORD"):
            core.initialize_database()

    def test_licensed_mode_accepts_strong_configured_passwords(self) -> None:
        os.environ["CCS_LICENSE_MODE"] = "licensed"
        os.environ["CCS_ADMIN_PASSWORD"] = "Admin-Pilot-2026!"
        os.environ["CCS_SUPPORT_PASSWORD"] = "Support-Pilot-2026!"
        os.environ["CCS_VIEWER_PASSWORD"] = "Viewer-Pilot-2026!"
        core = self.reload_core()
        core.initialize_database()

        self.assertIsNotNone(core.authenticate("admin", "Admin-Pilot-2026!"))
        self.assertIsNone(core.authenticate("admin", "Compelec-Start!"))

    def test_existing_demo_credentials_block_license_switch(self) -> None:
        demo_core = self.reload_core()
        demo_core.initialize_database()
        self.assertIsNotNone(demo_core.authenticate("admin", "Compelec-Start!"))

        os.environ["CCS_LICENSE_MODE"] = "licensed"
        licensed_core = self.reload_core()
        with self.assertRaisesRegex(RuntimeError, "Demo-Kennwort"):
            licensed_core.initialize_database()


if __name__ == "__main__":
    unittest.main()
