from __future__ import annotations

import os

from architecture import TenantContext, UserContext
from postgres_migrations import apply_postgres_migrations
from postgres_repository import PostgresRepository
from support_service import SupportService


def build_support_service(user: dict, *, migrate: bool = True) -> SupportService:
    database_url = os.getenv("CCS_DATABASE_URL", "").strip()
    if not database_url:
        raise RuntimeError(
            "CCS_DATABASE_URL ist für die V0.3-PostgreSQL-Laufzeit verpflichtend."
        )

    tenant_id = os.getenv("CCS_TENANT_ID", "compelec").strip() or "compelec"
    tenant_name = os.getenv("CCS_TENANT_NAME", "Compelec Computersysteme GmbH").strip()
    if migrate:
        apply_postgres_migrations(database_url)

    context = UserContext(
        username=user["username"],
        role=user["role"],
        tenant_id=tenant_id,
    )
    repository = PostgresRepository(database_url, TenantContext(tenant_id))
    service = SupportService(repository, context)
    service.ensure_tenant(tenant_name or tenant_id)
    return service
