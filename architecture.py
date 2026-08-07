from __future__ import annotations

from dataclasses import dataclass

PRIVACY_LEVELS = ("public", "internal", "confidential")

PERMISSION_TICKET_READ = "ticket.read"
PERMISSION_TICKET_WRITE = "ticket.write"
PERMISSION_KNOWLEDGE_READ = "knowledge.read"
PERMISSION_KNOWLEDGE_WRITE = "knowledge.write"
PERMISSION_KNOWLEDGE_REVIEW = "knowledge.review"
PERMISSION_DOCUMENT_READ = "document.read"
PERMISSION_DOCUMENT_IMPORT = "document.import"
PERMISSION_DOCUMENT_REVIEW = "document.review"
PERMISSION_ASSISTANT_USE = "assistant.use"
PERMISSION_ASSISTANT_INTERNAL = "assistant.internal"
PERMISSION_ASSISTANT_CONFIDENTIAL = "assistant.confidential"
PERMISSION_AUDIT_READ = "audit.read"
PERMISSION_TENANT_ADMIN = "tenant.admin"

ROLE_PERMISSIONS: dict[str, frozenset[str]] = {
    "viewer": frozenset(
        {
            PERMISSION_TICKET_READ,
            PERMISSION_KNOWLEDGE_READ,
            PERMISSION_DOCUMENT_READ,
            PERMISSION_ASSISTANT_USE,
        }
    ),
    "agent": frozenset(
        {
            PERMISSION_TICKET_READ,
            PERMISSION_TICKET_WRITE,
            PERMISSION_KNOWLEDGE_READ,
            PERMISSION_DOCUMENT_READ,
            PERMISSION_ASSISTANT_USE,
            PERMISSION_ASSISTANT_INTERNAL,
        }
    ),
    "admin": frozenset(
        {
            PERMISSION_TICKET_READ,
            PERMISSION_TICKET_WRITE,
            PERMISSION_KNOWLEDGE_READ,
            PERMISSION_KNOWLEDGE_WRITE,
            PERMISSION_KNOWLEDGE_REVIEW,
            PERMISSION_DOCUMENT_READ,
            PERMISSION_DOCUMENT_IMPORT,
            PERMISSION_DOCUMENT_REVIEW,
            PERMISSION_ASSISTANT_USE,
            PERMISSION_ASSISTANT_INTERNAL,
            PERMISSION_ASSISTANT_CONFIDENTIAL,
            PERMISSION_AUDIT_READ,
            PERMISSION_TENANT_ADMIN,
        }
    ),
}


class AuthorizationError(PermissionError):
    """Raised when a user is not allowed to perform an operation."""


@dataclass(frozen=True)
class TenantContext:
    tenant_id: str

    def __post_init__(self) -> None:
        if not self.tenant_id.strip():
            raise ValueError("tenant_id darf nicht leer sein.")


@dataclass(frozen=True)
class UserContext:
    username: str
    role: str
    tenant_id: str

    def __post_init__(self) -> None:
        if not self.username.strip():
            raise ValueError("username darf nicht leer sein.")
        if self.role not in ROLE_PERMISSIONS:
            raise ValueError(f"Unbekannte Rolle: {self.role}")
        if not self.tenant_id.strip():
            raise ValueError("tenant_id darf nicht leer sein.")

    @property
    def permissions(self) -> frozenset[str]:
        return ROLE_PERMISSIONS[self.role]


def has_permission(user: UserContext, permission: str) -> bool:
    return permission in user.permissions


def require_permission(user: UserContext, permission: str) -> None:
    if not has_permission(user, permission):
        raise AuthorizationError(
            f"Benutzer '{user.username}' mit Rolle '{user.role}' besitzt "
            f"die Berechtigung '{permission}' nicht."
        )


def require_same_tenant(user: UserContext, resource_tenant_id: str) -> None:
    """Enforce strict tenant isolation for all domain resources.

    V0.3 deliberately has no cross-tenant platform-admin bypass. A future platform
    administration role must be introduced explicitly instead of weakening this guard.
    """
    if user.tenant_id != resource_tenant_id:
        raise AuthorizationError(
            f"Mandantenzugriff verweigert: Benutzer '{user.username}' gehört zu "
            f"'{user.tenant_id}', die Ressource zu '{resource_tenant_id}'."
        )


def max_privacy_level(user: UserContext) -> str:
    if has_permission(user, PERMISSION_ASSISTANT_CONFIDENTIAL):
        return "confidential"
    if has_permission(user, PERMISSION_ASSISTANT_INTERNAL):
        return "internal"
    return "public"


def can_access_privacy(user: UserContext, requested_level: str) -> bool:
    if requested_level not in PRIVACY_LEVELS:
        raise ValueError(f"Ungültige Datenschutzstufe: {requested_level}")
    return PRIVACY_LEVELS.index(requested_level) <= PRIVACY_LEVELS.index(
        max_privacy_level(user)
    )


def require_privacy_access(user: UserContext, requested_level: str) -> None:
    if not can_access_privacy(user, requested_level):
        raise AuthorizationError(
            f"Datenschutzstufe '{requested_level}' ist für Rolle '{user.role}' "
            f"nicht freigegeben. Maximal zulässig: '{max_privacy_level(user)}'."
        )
