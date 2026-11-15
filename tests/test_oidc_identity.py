from __future__ import annotations

import unittest
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import patch

import jwt
from cryptography.hazmat.primitives.asymmetric import rsa

from identity import AuthenticationError, IdentityRequest, OIDCIdentityProvider


class FakeJwksClient:
    def __init__(self, key=None, error=None):
        self.key = key or object()
        self.error = error

    def get_signing_key_from_jwt(self, token):
        if self.error:
            raise self.error
        return SimpleNamespace(key=self.key)


class OIDCIdentityProviderTests(unittest.TestCase):
    def setUp(self):
        self.private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        self.public_key = self.private_key.public_key()
        now = datetime.now(timezone.utc)
        self.claims = {
            "iss": "https://login.example.test/tenant/v2.0",
            "aud": "compelec-one-business",
            "sub": "subject-123",
            "iat": int(now.timestamp()) - 10,
            "exp": int((now + timedelta(hours=1)).timestamp()),
            "preferred_username": "user@example.test",
            "tid": "tenant-abc",
            "roles": ["Business.Support.Agent"],
        }
        self.provider = OIDCIdentityProvider(
            issuer="https://login.example.test/tenant/v2.0",
            audience="compelec-one-business",
            jwks_url="https://login.example.test/keys",
            role_map={"Business.Support.Admin": "admin", "Business.Support.Agent": "agent"},
            tenant_map={"tenant-abc": "compelec"},
            jwks_client=FakeJwksClient(self.public_key),
        )

    def _token(self, claims=None, key=None):
        return jwt.encode(claims or self.claims, key or self.private_key, algorithm="RS256")

    def test_valid_signed_rs256_token_maps_identity_and_tenant(self):
        user = self.provider.authenticate(
            IdentityRequest(headers={"Authorization": f"Bearer {self._token()}"})
        )
        self.assertEqual(user.username, "user@example.test")
        self.assertEqual(user.role, "agent")
        self.assertEqual(user.tenant_id, "compelec")

    def test_missing_bearer_token_is_rejected(self):
        with self.assertRaises(AuthenticationError):
            self.provider.authenticate(IdentityRequest(headers={}))

    def test_unknown_role_is_rejected(self):
        claims = {**self.claims, "roles": ["Unmapped.Role"]}
        with patch("identity.jwt.decode", return_value=claims):
            with self.assertRaises(AuthenticationError):
                self.provider.authenticate(IdentityRequest(headers={"Authorization": "Bearer token"}))

    def test_ambiguous_roles_are_rejected(self):
        claims = {**self.claims, "roles": ["Business.Support.Admin", "Business.Support.Agent"]}
        with patch("identity.jwt.decode", return_value=claims):
            with self.assertRaises(AuthenticationError):
                self.provider.authenticate(IdentityRequest(headers={"Authorization": "Bearer token"}))

    def test_missing_tenant_claim_is_rejected(self):
        claims = {key: value for key, value in self.claims.items() if key != "tid"}
        with patch("identity.jwt.decode", return_value=claims):
            with self.assertRaises(AuthenticationError):
                self.provider.authenticate(IdentityRequest(headers={"Authorization": "Bearer token"}))

    def test_unmapped_external_tenant_is_rejected(self):
        claims = {**self.claims, "tid": "unknown-tenant"}
        with patch("identity.jwt.decode", return_value=claims):
            with self.assertRaises(AuthenticationError):
                self.provider.authenticate(IdentityRequest(headers={"Authorization": "Bearer token"}))

    def test_invalid_signature_is_rejected(self):
        other_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        token = self._token(key=other_key)
        with self.assertRaises(AuthenticationError):
            self.provider.authenticate(IdentityRequest(headers={"Authorization": f"Bearer {token}"}))

    def test_expired_token_is_rejected(self):
        expired_claims = {
            **self.claims,
            "iat": int((datetime.now(timezone.utc) - timedelta(hours=2)).timestamp()),
            "exp": int((datetime.now(timezone.utc) - timedelta(hours=1)).timestamp()),
        }
        token = self._token(claims=expired_claims)
        with self.assertRaises(AuthenticationError):
            self.provider.authenticate(IdentityRequest(headers={"Authorization": f"Bearer {token}"}))

    def test_jwks_failure_fails_closed(self):
        provider = OIDCIdentityProvider(
            issuer="https://login.example.test",
            audience="compelec-one-business",
            jwks_url="https://login.example.test/keys",
            tenant_map={"tenant-abc": "compelec"},
            jwks_client=FakeJwksClient(error=RuntimeError("network unavailable")),
        )
        with self.assertRaises(AuthenticationError):
            provider.authenticate(IdentityRequest(headers={"Authorization": "Bearer token"}))

    def test_insecure_endpoints_are_rejected(self):
        with self.assertRaises(ValueError):
            OIDCIdentityProvider(
                issuer="http://login.example.test",
                audience="compelec-one-business",
                jwks_url="https://login.example.test/keys",
                tenant_map={"tenant-abc": "compelec"},
            )
        with self.assertRaises(ValueError):
            OIDCIdentityProvider(
                issuer="https://login.example.test",
                audience="compelec-one-business",
                jwks_url="http://login.example.test/keys",
                tenant_map={"tenant-abc": "compelec"},
            )


if __name__ == "__main__":
    unittest.main()
