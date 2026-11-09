from __future__ import annotations

import os
import unittest
from unittest.mock import patch

from production_config import ProductionConfigError, load_production_config


class ProductionConfigTests(unittest.TestCase):
    def _env(self, **overrides):
        base = {
            "CCS_DATABASE_URL": "postgresql://user:pass@db.internal/compelec",
            "CCS_TENANT_ID": "compelec",
            "CCS_TENANT_NAME": "Compelec",
            "CCS_EMBEDDING_PROVIDER": "openai-compatible",
            "CCS_LICENSE_MODE": "licensed",
            "CCS_IDENTITY_MODE": "trusted-header",
            "CCS_TRUSTED_HEADER_MODE_ACK": "I_TRUST_MY_AUTHENTICATING_PROXY",
            "CCS_TRUSTED_TENANT_MAP": '{"entra-tenant-guid":"compelec"}',
            "CCS_ENVIRONMENT": "production",
        }
        base.update(overrides)
        return patch.dict(os.environ, base, clear=True)

    def test_valid_production_config(self):
        with self._env():
            cfg = load_production_config()
        self.assertTrue(cfg.is_production)
        self.assertEqual(cfg.tenant_id, "compelec")

    def test_production_rejects_demo_license_mode(self):
        with self._env(CCS_LICENSE_MODE="demo"):
            with self.assertRaises(ProductionConfigError):
                load_production_config()

    def test_trusted_header_production_requires_explicit_proxy_acknowledgement(self):
        with self._env(CCS_TRUSTED_HEADER_MODE_ACK=""):
            with self.assertRaises(ProductionConfigError):
                load_production_config()

    def test_trusted_header_production_requires_tenant_allowlist(self):
        with self._env(CCS_TRUSTED_TENANT_MAP=""):
            with self.assertRaises(ProductionConfigError):
                load_production_config()

    def test_local_hash_is_rejected_in_production(self):
        with self._env(CCS_EMBEDDING_PROVIDER="local-hash"):
            with self.assertRaises(ProductionConfigError):
                load_production_config()

    def test_localhost_database_is_rejected_in_production(self):
        with self._env(CCS_DATABASE_URL="postgresql://u:p@127.0.0.1/db"):
            with self.assertRaises(ProductionConfigError):
                load_production_config()

    def test_missing_tenant_is_rejected(self):
        with self._env(CCS_TENANT_ID=""):
            with self.assertRaises(ProductionConfigError):
                load_production_config()


if __name__ == "__main__":
    unittest.main()
