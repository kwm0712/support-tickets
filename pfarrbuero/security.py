"""OIDC access-token validation for the Pfarrbüro-KI API."""
from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache

import jwt
from jwt import PyJWKClient


@dataclass(frozen=True)
class Principal:
    user_id: str
    tenant_id: str
    org_unit_id: str


@lru_cache(maxsize=1)
def _jwks_client() -> PyJWKClient:
    url = os.getenv("PFARRBUERO_OIDC_JWKS_URL", "").strip()
    if not url:
        raise RuntimeError("PFARRBUERO_OIDC_JWKS_URL ist nicht konfiguriert.")
    return PyJWKClient(url, cache_jwk_set=True, lifespan=300)


def decode_access_token(token: str) -> Principal:
    issuer = os.getenv("PFARRBUERO_OIDC_ISSUER", "").strip()
    audience = os.getenv("PFARRBUERO_OIDC_AUDIENCE", "").strip()
    if not issuer or not audience:
        raise RuntimeError("OIDC issuer/audience sind nicht vollständig konfiguriert.")
    signing_key = _jwks_client().get_signing_key_from_jwt(token).key
    claims = jwt.decode(
        token,
        signing_key,
        algorithms=["RS256"],
        issuer=issuer,
        audience=audience,
        options={"require": ["exp", "iat", "sub", "tenant_id", "org_unit_id"]},
        leeway=30,
    )
    values = (claims.get("sub"), claims.get("tenant_id"), claims.get("org_unit_id"))
    if not all(isinstance(value, str) and value.strip() for value in values):
        raise jwt.InvalidTokenError("sub, tenant_id und org_unit_id müssen Strings sein.")
    return Principal(user_id=values[0], tenant_id=values[1], org_unit_id=values[2])
