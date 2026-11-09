from __future__ import annotations

from functools import lru_cache
from typing import Any

from fastapi import Depends, FastAPI, HTTPException, Request
from pydantic import BaseModel, Field

from architecture import (
    AuthorizationError,
    PERMISSION_TENANT_ADMIN,
    TenantContext,
    has_permission,
)
from embedding import build_embedding_provider_from_env
from identity import (
    AuthenticationError,
    IdentityRequest,
    OIDCIdentityProvider,
    TrustedHeaderIdentityProvider,
)
from postgres_migrations import apply_postgres_migrations
from postgres_repository import PostgresRepository
from production_config import ProductionConfig, ProductionConfigError, load_production_config
from support_service import SupportService
from system_diagnostics import build_system_diagnostics

PRODUCT = "COMPELEC ONE Business - AI Support & Knowledge"
VERSION = "1.2.0-dev"

app = FastAPI(title=PRODUCT, version=VERSION)


def config() -> ProductionConfig:
    try:
        return load_production_config()
    except ProductionConfigError as exc:
        raise HTTPException(status_code=503, detail=f"Konfiguration nicht freigabefähig: {exc}") from exc


@lru_cache(maxsize=8)
def _cached_oidc_provider(
    issuer: str,
    audience: str,
    jwks_url: str,
    role_claim: str,
    tenant_claim: str,
    username_claim: str,
    role_map_items: tuple[tuple[str, str], ...],
) -> OIDCIdentityProvider:
    return OIDCIdentityProvider(
        issuer=issuer,
        audience=audience,
        jwks_url=jwks_url,
        role_claim=role_claim,
        tenant_claim=tenant_claim,
        username_claim=username_claim,
        role_map=dict(role_map_items),
    )


def build_identity_provider(cfg: ProductionConfig):
    if cfg.identity_mode == "oidc":
        return _cached_oidc_provider(
            cfg.oidc_issuer,
            cfg.oidc_audience,
            cfg.oidc_jwks_url,
            cfg.oidc_role_claim,
            cfg.oidc_tenant_claim,
            cfg.oidc_username_claim,
            tuple(sorted(cfg.oidc_role_map.items())),
        )
    return TrustedHeaderIdentityProvider(default_tenant_id=cfg.tenant_id)


def get_service(request: Request, cfg: ProductionConfig = Depends(config)) -> SupportService:
    try:
        provider = build_identity_provider(cfg)
        user = provider.authenticate(IdentityRequest(headers=request.headers))
        repository = PostgresRepository(cfg.database_url, TenantContext(user.tenant_id))
        service = SupportService(repository, user, embedding_provider=build_embedding_provider_from_env())
        service.ensure_tenant(cfg.tenant_name)
        return service
    except AuthenticationError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc
    except AuthorizationError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc


@app.on_event("startup")
def startup() -> None:
    cfg = load_production_config()
    apply_postgres_migrations(cfg.database_url)


@app.get("/health/live")
def liveness() -> dict[str, str]:
    return {"status": "ok", "product": PRODUCT, "version": VERSION}


@app.get("/health/ready")
def readiness(service: SupportService = Depends(get_service), cfg: ProductionConfig = Depends(config)) -> dict[str, Any]:
    db_ok = service.repository.healthcheck()
    return {
        "status": "ready" if db_ok else "degraded",
        "database": "ok" if db_ok else "failed",
        "environment": cfg.environment,
        "tenant": service.user.tenant_id,
        "embedding_provider": cfg.embedding_provider,
        "identity_mode": cfg.identity_mode,
        "version": VERSION,
    }


@app.get("/v1/system/diagnostics")
def system_diagnostics(service: SupportService = Depends(get_service), cfg: ProductionConfig = Depends(config)):
    if not has_permission(service.user, PERMISSION_TENANT_ADMIN):
        raise HTTPException(status_code=403, detail="Berechtigung tenant.admin erforderlich.")
    try:
        database_ok = service.repository.healthcheck()
    except Exception:
        database_ok = False
    return build_system_diagnostics(
        version=VERSION,
        environment=cfg.environment,
        tenant_id=service.user.tenant_id,
        identity_mode=cfg.identity_mode,
        embedding_provider=cfg.embedding_provider,
        database_ok=database_ok,
    )


@app.get("/v1/tickets")
def list_tickets(service: SupportService = Depends(get_service)):
    return service.list_tickets()


class TicketCreate(BaseModel):
    subject: str = Field(min_length=1, max_length=200)
    description: str = Field(min_length=1, max_length=20000)
    customer: str = Field(min_length=1, max_length=200)
    priority: str = Field(default="Mittel", pattern="^(Hoch|Mittel|Niedrig)$")


@app.post("/v1/tickets", status_code=201)
def create_ticket(payload: TicketCreate, service: SupportService = Depends(get_service)):
    return {"ticket_no": service.create_ticket(**payload.model_dump())}


class AssistantAsk(BaseModel):
    question: str = Field(min_length=1, max_length=10000)
    privacy_level: str = Field(default="internal", pattern="^(public|internal|confidential)$")


@app.post("/v1/assistant/ask")
def ask_assistant(payload: AssistantAsk, service: SupportService = Depends(get_service)):
    result = service.ask_assistant(**payload.model_dump())
    return {
        "provider": result.provider,
        "answer": result.answer,
        "privacy_level": result.privacy_level,
        "run_id": result.run_id,
        "evidence": [e.__dict__ for e in result.evidence],
    }


@app.get("/v1/knowledge")
def list_knowledge(service: SupportService = Depends(get_service)):
    return service.list_articles(include_unapproved=False)


@app.get("/v1/documents")
def list_documents(service: SupportService = Depends(get_service)):
    return service.list_documents()


@app.get("/v1/metrics")
def metrics(service: SupportService = Depends(get_service)):
    return service.get_metrics()


@app.get("/v1/audit")
def audit(limit: int = 100, service: SupportService = Depends(get_service)):
    return service.list_audit_entries(limit=max(1, min(limit, 500)))
