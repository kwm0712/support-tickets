from __future__ import annotations

import os
import unittest
from unittest.mock import patch

from production_config import ProductionConfigError, load_production_config


class OIDCProductionConfigTests(unittest.TestCase):
    def _env(self, **overrides):
        values = {
            "CCS_DATABASE_URL": "postgresql://ccs:secret@db.internal/compelec",
            "CCS_TENANT_ID": "compelec",
            "CCS_TENANT_NAME": "Compelec Computersysteme GmbH",
            "CCS_EMBEDDING_PROVIDER": "openai-compatible",
            "CCS_LICENSE_MODE": "licensed",
            "CCS_IDENTITY_MODE": "oidc",
            "CCS_ENVIRONMENT": "production",
            "CCS_OIDC_ISSUER": "https://login.microsoftonline.com/example/v2.0",
            "CCS_OIDC_AUDIENCE": "api://compelec-one-business",
            "CCS_OIDC_JWKS_URL": "https://login.microsoftonline.com/common/discovery/v2.0/keys",
            "CCS_OIDC_ROLE_CLAIM": "roles",
            "CCS_OIDC_TENANT_CLAIM": "tid",
            "CCS_OIDC_USERNAME_CLAIM": "preferred_username",
            "CCS_OIDC_ROLE_MAP": '{"Compelec.Admin":"admin","Compelec.Support":"agent","Compelec.ReadOnly":"viewer"}',
            "CCS_OIDC_TENANT_MAP": '{"11111111-2222-3333-4444-555555555555":"compelec"}',
        }
        values.update(overrides)
        return patch.dict(os.environ, values, clear=True)

    def test_valid_production_oidc_configuration(self):
        with self._env():
            cfg = load_production_config()
        self.assertEqual(cfg.identity_mode, "oidc")
        self.assertEqual(cfg.oidc_audience, "api://compelec-one-business")
        self.assertEqual(cfg.oidc_role_map["Compelec.Admin"], "admin")
        self.assertEqual(cfg.oidc_tenant_map["11111111-2222-3333-4444-555555555555"], "compelec")

    def test_oidc_requires_https_jwks(self):
        with self._env(CCS_OIDC_JWKS_URL="http://login.example.test/keys"):
            with self.assertRaises(ProductionConfigError):
                load_production_config()

    def test_production_oidc_requires_explicit_role_mapping(self):
        with self._env(CCS_OIDC_ROLE_MAP=""):
            with self.assertRaises(ProductionConfigError):
                load_production_config()

    def test_oidc_requires_explicit_tenant_mapping(self):
        with self._env(CCS_OIDC_TENANT_MAP=""):
            with self.assertRaises(ProductionConfigError):
                load_production_config()

    def test_oidc_rejects_unknown_internal_role(self):
        with self._env(CCS_OIDC_ROLE_MAP='{"Compelec.Admin":"superuser"}'):
            with self.assertRaises(ProductionConfigError):
                load_production_config()

    def test_oidc_requires_audience(self):
        with self._env(CCS_OIDC_AUDIENCE=""):
            with self.assertRaises(ProductionConfigError):
                load_production_config()


if __name__ == "__main__":
    unittest.main()
