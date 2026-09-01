from __future__ import annotations

import unittest

from architecture import UserContext
from identity import (
    AuthenticationError,
    IdentityRequest,
    StaticIdentityProvider,
    TrustedHeaderIdentityProvider,
)


class IdentityProviderTests(unittest.TestCase):
    def test_trusted_headers_map_to_user_context(self):
        provider = TrustedHeaderIdentityProvider(default_tenant_id="compelec")
        user = provider.authenticate(
            IdentityRequest(
                headers={
                    "X-Compelec-User": "kmalter",
                    "X-Compelec-Role": "admin",
                    "X-Compelec-Tenant": "compelec",
                }
            )
        )
        self.assertEqual(user.username, "kmalter")
        self.assertEqual(user.role, "admin")
        self.assertEqual(user.tenant_id, "compelec")

    def test_missing_user_is_rejected(self):
        provider = TrustedHeaderIdentityProvider(default_tenant_id="compelec")
        with self.assertRaises(AuthenticationError):
            provider.authenticate(IdentityRequest(headers={"X-Compelec-Role": "viewer"}))

    def test_invalid_role_is_rejected(self):
        provider = TrustedHeaderIdentityProvider(default_tenant_id="compelec")
        with self.assertRaises(AuthenticationError):
            provider.authenticate(
                IdentityRequest(
                    headers={
                        "X-Compelec-User": "user1",
                        "X-Compelec-Role": "superuser",
                    }
                )
            )

    def test_static_provider_returns_configured_user(self):
        expected = UserContext(username="test", role="viewer", tenant_id="compelec")
        provider = StaticIdentityProvider(expected)
        self.assertEqual(provider.authenticate(IdentityRequest(headers={})), expected)


if __name__ == "__main__":
    unittest.main()
