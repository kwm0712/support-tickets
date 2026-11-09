from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

from production_config import ProductionConfig
from v03_runtime import build_support_service


def _config(environment="production"):
    return ProductionConfig(
        database_url="postgresql://app:secret@db.internal/compelec",
        tenant_id="compelec",
        tenant_name="Compelec Computersysteme GmbH",
        embedding_provider="openai-compatible",
        identity_mode="oidc",
        environment=environment,
    )


class V03RuntimeTenantTests(unittest.TestCase):
    @patch("v03_runtime.SupportService")
    @patch("v03_runtime.build_embedding_provider_from_env")
    @patch("v03_runtime.apply_postgres_migrations")
    @patch("v03_runtime.PostgresRepository")
    @patch("v03_runtime.load_production_config")
    def test_production_runtime_uses_authenticated_tenant_and_checks_role(
        self, load_config, repository_cls, apply_migrations, build_embedding, service_cls
    ):
        load_config.return_value = _config()
        repository = MagicMock()
        repository_cls.return_value = repository
        service = MagicMock()
        service_cls.return_value = service

        result = build_support_service(
            {
                "username": "oidc-user",
                "role": "agent",
                "tenant_id": "parish-a",
            }
        )

        repository_cls.assert_called_once()
        self.assertEqual(repository_cls.call_args.args[1].tenant_id, "parish-a")
        repository.ensure_safe_runtime_role.assert_called_once()
        apply_migrations.assert_called_once()
        service.ensure_tenant.assert_called_once_with("Compelec Computersysteme GmbH")
        self.assertIs(result, service)

    @patch("v03_runtime.load_production_config", return_value=_config())
    def test_production_runtime_rejects_missing_authenticated_tenant(self, _):
        with self.assertRaisesRegex(RuntimeError, "verifizierte Mandantenkennung"):
            build_support_service({"username": "user", "role": "agent"})

    @patch("v03_runtime.SupportService")
    @patch("v03_runtime.build_embedding_provider_from_env")
    @patch("v03_runtime.apply_postgres_migrations")
    @patch("v03_runtime.PostgresRepository")
    @patch("v03_runtime.load_production_config")
    def test_development_runtime_uses_configured_default_tenant(
        self, load_config, repository_cls, apply_migrations, build_embedding, service_cls
    ):
        load_config.return_value = _config(environment="development")
        repository_cls.return_value = MagicMock()
        service_cls.return_value = MagicMock()

        build_support_service({"username": "local-user", "role": "admin"})

        self.assertEqual(repository_cls.call_args.args[1].tenant_id, "compelec")
        repository_cls.return_value.ensure_safe_runtime_role.assert_not_called()


if __name__ == "__main__":
    unittest.main()
