from __future__ import annotations

from typing import Any


def build_system_diagnostics(
    *,
    version: str,
    environment: str,
    tenant_id: str,
    identity_mode: str,
    embedding_provider: str,
    database_ok: bool,
) -> dict[str, Any]:
    """Return a safe operational snapshot without credentials or personal data."""
    required = {
        "version": version,
        "environment": environment,
        "tenant_id": tenant_id,
        "identity_mode": identity_mode,
        "embedding_provider": embedding_provider,
    }
    if any(not str(value).strip() for value in required.values()):
        raise ValueError("Diagnoseparameter dürfen nicht leer sein.")

    return {
        "product": "COMPELEC ONE Business",
        "version": version,
        "status": "ready" if database_ok else "degraded",
        "checks": {
            "database": "ok" if database_ok else "failed",
            "identity": "configured",
            "embedding": "configured",
        },
        "configuration": {
            "environment": environment,
            "tenant_id": tenant_id,
            "identity_mode": identity_mode,
            "embedding_provider": embedding_provider,
        },
        "security": {
            "credentials_exposed": False,
            "scope": "current_authenticated_tenant",
        },
    }
