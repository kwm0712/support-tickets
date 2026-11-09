from __future__ import annotations

import unittest
from types import SimpleNamespace
from unittest.mock import patch

import jwt

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
        self.claims = {
            "iss": "https://login.example.test/tenant/v2.0",
            "aud": "compelec-one-business",
            "sub": "subject-123",
            "iat": 1_800_000_000,
            "exp": 1_800_003_600,
            "preferred_username": "user@example.test",
            "tid": "tenant-abc",
            "roles": ["Business.Support.Agent"],
        }
        self.provider = OIDCIdentityProvider(
            issuer="https://login.example.test/tenant/v2.0",
            audience="compelec-one-business",
            jwks_url="https://login.example.test/keys",
            role_map={"Business.Support.Admin": "admin", "Business.Support.Agent": "agent"},
            jwks_client=FakeJwksClient(),
        )

    def test_valid_bearer_token_maps_identity_and_tenant(self):
        with patch("identity.jwt.decode", return_value=self.claims) as decode:
            user = self.provider.authenticate(
                IdentityRequest(headers={"Authorization": "Bearer signed-token"})
            )
        self.assertEqual(user.username, "user@example.test")
        self.assertEqual(user.role, "agent")
        self.assertEqual(user.tenant_id, "tenant-abc")
        decode.assert_called_once()
        self.assertEqual(decode.call_args.kwargs["algorithms"], ["RS256"])
        self.assertEqual(decode.call_args.kwargs["audience"], "compelec-one-business")
        self.assertEqual(decode.call_args.kwargs["issuer"], "https://login.example.test/tenant/v2.0")

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

    def test_invalid_signature_or_claims_are_rejected(self):
        with patch("identity.jwt.decode", side_effect=jwt.InvalidTokenError("invalid")):
            with self.assertRaises(AuthenticationError):
                self.provider.authenticate(IdentityRequest(headers={"Authorization": "Bearer token"}))

    def test_jwks_failure_fails_closed(self):
        provider = OIDCIdentityProvider(
            issuer="https://login.example.test",
            audience="compelec-one-business",
            jwks_url="https://login.example.test/keys",
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
            )
        with self.assertRaises(ValueError):
            OIDCIdentityProvider(
                issuer="https://login.example.test",
                audience="compelec-one-business",
                jwks_url="http://login.example.test/keys",
            )


if __name__ == "__main__":
    unittest.main()
