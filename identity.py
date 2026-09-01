from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Protocol

from architecture import ROLE_PERMISSIONS, UserContext


class AuthenticationError(PermissionError):
    """Raised when an incoming request cannot be mapped to a trusted identity."""


@dataclass(frozen=True)
class IdentityRequest:
    headers: Mapping[str, str]


class IdentityProvider(Protocol):
    """Replaceable authentication boundary for COMPELEC ONE Business V0.4."""

    provider_name: str

    def authenticate(self, request: IdentityRequest) -> UserContext:
        ...


class TrustedHeaderIdentityProvider:
    """Identity provider for reverse-proxy/SSO integration.

    The upstream gateway is responsible for authenticating the user and stripping
    untrusted client-supplied identity headers. This provider only accepts the
    normalized headers configured below and maps them to the existing UserContext.
    """

    provider_name = "trusted-header"

    def __init__(
        self,
        *,
        default_tenant_id: str,
        username_header: str = "x-compelec-user",
        role_header: str = "x-compelec-role",
        tenant_header: str = "x-compelec-tenant",
    ) -> None:
        if not default_tenant_id.strip():
            raise ValueError("default_tenant_id darf nicht leer sein.")
        self.default_tenant_id = default_tenant_id.strip()
        self.username_header = username_header.lower()
        self.role_header = role_header.lower()
        self.tenant_header = tenant_header.lower()

    def authenticate(self, request: IdentityRequest) -> UserContext:
        headers = {str(k).lower(): str(v).strip() for k, v in request.headers.items()}
        username = headers.get(self.username_header, "")
        role = headers.get(self.role_header, "")
        tenant_id = headers.get(self.tenant_header, "") or self.default_tenant_id

        if not username:
            raise AuthenticationError("Authentifizierter Benutzer fehlt.")
        if role not in ROLE_PERMISSIONS:
            raise AuthenticationError("Ungültige oder fehlende Benutzerrolle.")
        if not tenant_id:
            raise AuthenticationError("Mandant fehlt.")

        return UserContext(username=username, role=role, tenant_id=tenant_id)


class StaticIdentityProvider:
    """Explicit local/test identity provider; never use as production SSO."""

    provider_name = "static"

    def __init__(self, user: UserContext) -> None:
        self.user = user

    def authenticate(self, request: IdentityRequest) -> UserContext:
        return self.user
