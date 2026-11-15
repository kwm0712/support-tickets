from __future__ import annotations

import unittest

from identity import AuthenticationError, IdentityRequest, TrustedHeaderIdentityProvider


class TrustedHeaderProductionTests(unittest.TestCase):
    def setUp(self):
        self.provider = TrustedHeaderIdentityProvider(
            default_tenant_id="compelec",
            require_tenant_header=True,
            tenant_map={"idp-tenant-abc": "parish-a"},
        )

    def test_production_proxy_identity_requires_tenant_header(self):
        with self.assertRaisesRegex(AuthenticationError, "Mandantenkennung"):
            self.provider.authenticate(
                IdentityRequest(headers={
                    "x-compelec-user": "user1",
                    "x-compelec-role": "agent",
                })
            )

    def test_production_proxy_identity_rejects_unmapped_tenant(self):
        with self.assertRaisesRegex(AuthenticationError, "nicht freigegeben"):
            self.provider.authenticate(
                IdentityRequest(headers={
                    "x-compelec-user": "user1",
                    "x-compelec-role": "agent",
                    "x-compelec-tenant": "unknown-tenant",
                })
            )

    def test_production_proxy_identity_uses_explicit_tenant_header(self):
        user = self.provider.authenticate(
            IdentityRequest(headers={
                "x-compelec-user": "user1",
                "x-compelec-role": "agent",
                "x-compelec-tenant": "idp-tenant-abc",
            })
        )
        self.assertEqual(user.tenant_id, "parish-a")
        self.assertEqual(user.role, "agent")


if __name__ == "__main__":
    unittest.main()
