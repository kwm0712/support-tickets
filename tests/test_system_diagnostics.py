from __future__ import annotations

import unittest

from system_diagnostics import build_system_diagnostics


class SystemDiagnosticsTests(unittest.TestCase):
    def _build(self, database_ok: bool = True):
        return build_system_diagnostics(
            version="1.2.0-dev",
            environment="test",
            tenant_id="tenant-a",
            identity_mode="trusted-header",
            embedding_provider="local-hash",
            database_ok=database_ok,
        )

    def test_ready_snapshot_is_tenant_scoped_and_secret_free(self):
        result = self._build()
        self.assertEqual(result["status"], "ready")
        self.assertEqual(result["checks"]["database"], "ok")
        self.assertEqual(result["configuration"]["tenant_id"], "tenant-a")
        self.assertFalse(result["security"]["credentials_exposed"])
        self.assertNotIn("database_url", result)
        self.assertNotIn("password", str(result).lower())

    def test_database_failure_is_degraded(self):
        result = self._build(database_ok=False)
        self.assertEqual(result["status"], "degraded")
        self.assertEqual(result["checks"]["database"], "failed")

    def test_empty_configuration_is_rejected(self):
        with self.assertRaises(ValueError):
            build_system_diagnostics(
                version="1.2.0-dev",
                environment="test",
                tenant_id="",
                identity_mode="trusted-header",
                embedding_provider="local-hash",
                database_ok=True,
            )


if __name__ == "__main__":
    unittest.main()
