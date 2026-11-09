from __future__ import annotations

from architecture import TenantContext, UserContext
from embedding import build_embedding_provider_from_env
from postgres_migrations import apply_postgres_migrations
from postgres_repository import PostgresRepository
from production_config import load_production_config
from support_service import SupportService


def build_support_service(user: dict, *, migrate: bool = True) -> SupportService:
    cfg = load_production_config()
    database_url = cfg.database_url
    tenant_id = str(user.get("tenant_id") or cfg.tenant_id).strip()
    if not tenant_id:
        raise RuntimeError("Authentifizierter Mandant fehlt für die PostgreSQL-Laufzeit.")
    if cfg.is_production and not user.get("tenant_id"):
        raise RuntimeError("Produktiver Benutzerkontext muss eine verifizierte Mandantenkennung enthalten.")

    repository = PostgresRepository(database_url, TenantContext(tenant_id))
    if cfg.is_production:
        repository.assert_safe_runtime_role()
    if migrate:
        apply_postgres_migrations(database_url)

    context = UserContext(
        username=user["username"],
        role=user["role"],
        tenant_id=tenant_id,
    )
    embedding_provider = build_embedding_provider_from_env()
    service = SupportService(
        repository,
        context,
        embedding_provider=embedding_provider,
    )
    tenant_name = cfg.tenant_name.strip() or tenant_id
    service.ensure_tenant(tenant_name)
    return service
