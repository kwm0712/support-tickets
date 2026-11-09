from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Protocol

import jwt

from architecture import ROLE_PERMISSIONS, UserContext


class AuthenticationError(PermissionError):
    """Raised when an incoming request cannot be mapped to a trusted identity."""


@dataclass(frozen=True)
class IdentityRequest:
    headers: Mapping[str, str]


class IdentityProvider(Protocol):
    """Replaceable authentication boundary for COMPELEC ONE Business."""

    provider_name: str

    def authenticate(self, request: IdentityRequest) -> UserContext:
        ...


class TrustedHeaderIdentityProvider:
    """Identity provider for a trusted reverse-proxy/SSO gateway.

    The upstream gateway MUST authenticate the user, remove all inbound
    x-compelec-* headers and set fresh values itself. This adapter does not
    validate a token and is safe only behind that explicitly trusted boundary.
    """

    provider_name = "trusted-header"

    def __init__(
        self,
        *,
        default_tenant_id: str,
        username_header: str = "x-compelec-user",
        role_header: str = "x-compelec-role",
        tenant_header: str = "x-compelec-tenant",
        require_tenant_header: bool = False,
    ) -> None:
        if not default_tenant_id.strip():
            raise ValueError("default_tenant_id darf nicht leer sein.")
        self.default_tenant_id = default_tenant_id.strip()
        self.username_header = username_header.lower()
        self.role_header = role_header.lower()
        self.tenant_header = tenant_header.lower()
        self.require_tenant_header = require_tenant_header

    def authenticate(self, request: IdentityRequest) -> UserContext:
        headers = {str(k).lower(): str(v).strip() for k, v in request.headers.items()}
        username = headers.get(self.username_header, "")
        role = headers.get(self.role_header, "")
        supplied_tenant_id = headers.get(self.tenant_header, "")
        if self.require_tenant_header and not supplied_tenant_id:
            raise AuthenticationError("Mandantenkennung aus dem vertrauenswürdigen Proxy fehlt.")
        tenant_id = supplied_tenant_id or self.default_tenant_id

        if not username:
            raise AuthenticationError("Authentifizierter Benutzer fehlt.")
        if role not in ROLE_PERMISSIONS:
            raise AuthenticationError("Ungültige oder fehlende Benutzerrolle.")
        if not tenant_id:
            raise AuthenticationError("Mandant fehlt.")

        return UserContext(username=username, role=role, tenant_id=tenant_id)


class OIDCIdentityProvider:
    """Validate signed OIDC access tokens against an HTTPS JWKS endpoint.

    Only RS256 is accepted. Issuer, audience, expiry, issued-at and subject are
    mandatory. Application roles are mapped explicitly to the internal RBAC
    roles; the tenant claim is mandatory and never falls back to a default.
    """

    provider_name = "oidc"

    def __init__(
        self,
        *,
        issuer: str,
        audience: str,
        jwks_url: str,
        role_claim: str = "roles",
        tenant_claim: str = "tid",
        username_claim: str = "preferred_username",
        role_map: Mapping[str, str] | None = None,
        tenant_map: Mapping[str, str] | None = None,
        leeway_seconds: int = 30,
        jwks_client: object | None = None,
    ) -> None:
        self.issuer = issuer.strip()
        self.audience = audience.strip()
        self.jwks_url = jwks_url.strip()
        if not self.issuer.startswith("https://"):
            raise ValueError("OIDC-Issuer muss HTTPS verwenden.")
        if not self.audience:
            raise ValueError("OIDC-Audience darf nicht leer sein.")
        if not self.jwks_url.startswith("https://"):
            raise ValueError("OIDC-JWKS-Endpunkt muss HTTPS verwenden.")
        if not role_claim.strip() or not tenant_claim.strip():
            raise ValueError("OIDC-Rollen- und Mandanten-Claim müssen gesetzt sein.")
        if leeway_seconds < 0 or leeway_seconds > 120:
            raise ValueError("OIDC-Leeway muss zwischen 0 und 120 Sekunden liegen.")

        normalized_map = dict(role_map or {
            "admin": "admin",
            "agent": "agent",
            "viewer": "viewer",
        })
        if not normalized_map:
            raise ValueError("OIDC-Rollenmapping darf nicht leer sein.")
        if any(target not in ROLE_PERMISSIONS for target in normalized_map.values()):
            raise ValueError("OIDC-Rollenmapping enthält eine unbekannte COMPELEC-Rolle.")

        self.role_claim = role_claim
        self.tenant_claim = tenant_claim
        self.username_claim = username_claim
        normalized_tenant_map = dict(tenant_map or {})
        if not normalized_tenant_map:
            raise ValueError("OIDC-Mandantenmapping darf nicht leer sein.")
        if any(not external.strip() or not internal.strip() for external, internal in normalized_tenant_map.items()):
            raise ValueError("OIDC-Mandantenmapping enthält leere Kennungen.")
        self.role_map = normalized_map
        self.tenant_map = normalized_tenant_map
        self.leeway_seconds = leeway_seconds
        self._jwks_client = jwks_client or jwt.PyJWKClient(
            self.jwks_url,
            cache_jwk_set=True,
            lifespan=300,
            timeout=5,
        )

    def authenticate(self, request: IdentityRequest) -> UserContext:
        headers = {str(k).lower(): str(v).strip() for k, v in request.headers.items()}
        authorization = headers.get("authorization", "")
        scheme, separator, token = authorization.partition(" ")
        if not separator or scheme.lower() != "bearer" or not token.strip():
            raise AuthenticationError("Bearer-Token fehlt oder ist ungültig.")

        try:
            signing_key = self._jwks_client.get_signing_key_from_jwt(token.strip())
            claims = jwt.decode(
                token.strip(),
                signing_key.key,
                algorithms=["RS256"],
                audience=self.audience,
                issuer=self.issuer,
                leeway=self.leeway_seconds,
                options={"require": ["exp", "iat", "iss", "aud", "sub"]},
            )
        except (jwt.PyJWTError, jwt.PyJWKClientError, KeyError, TypeError, ValueError) as exc:
            raise AuthenticationError("OIDC-Token konnte nicht validiert werden.") from exc
        except Exception as exc:
            # Network/JWKS failures are deliberately converted to an auth failure;
            # raw provider errors must not leak into API responses or logs.
            raise AuthenticationError("OIDC-Schlüssel konnten nicht sicher geladen werden.") from exc

        subject = str(claims.get("sub", "")).strip()
        username = str(claims.get(self.username_claim) or subject).strip()
        external_tenant_id = str(claims.get(self.tenant_claim, "")).strip()
        if not subject or not username:
            raise AuthenticationError("OIDC-Benutzerkennung fehlt.")
        if not external_tenant_id:
            raise AuthenticationError("OIDC-Mandantenkennung fehlt.")
        tenant_id = self.tenant_map.get(external_tenant_id, "")
        if not tenant_id:
            raise AuthenticationError("OIDC-Mandant ist für COMPELEC nicht freigegeben.")

        raw_roles = claims.get(self.role_claim)
        role_values = [raw_roles] if isinstance(raw_roles, str) else raw_roles
        if not isinstance(role_values, list) or not role_values:
            raise AuthenticationError("OIDC-Rollen-Claim fehlt oder ist ungültig.")
        mapped_roles = {
            self.role_map[value]
            for value in role_values
            if isinstance(value, str) and value in self.role_map
        }
        if len(mapped_roles) != 1:
            raise AuthenticationError("OIDC-Rolle fehlt, ist unbekannt oder mehrdeutig.")

        return UserContext(
            username=username,
            role=next(iter(mapped_roles)),
            tenant_id=tenant_id,
        )


class StaticIdentityProvider:
    """Explicit local/test identity provider; never use as production SSO."""

    provider_name = "static"

    def __init__(self, user: UserContext) -> None:
        self.user = user

    def authenticate(self, request: IdentityRequest) -> UserContext:
        return self.user
