from __future__ import annotations

import os
from typing import Any

from fastapi import Depends, FastAPI, Header, HTTPException, Request
from pydantic import BaseModel, Field

from architecture import AuthorizationError, TenantContext
from embedding import build_embedding_provider_from_env
from identity import AuthenticationError, IdentityProvider, IdentityRequest, TrustedHeaderIdentityProvider
from postgres_migrations import apply_postgres_migrations
from postgres_repository import PostgresRepository
from support_service import SupportService

PRODUCT = "COMPELEC ONE Business - AI Support & Knowledge"
VERSION = "0.4.0-dev"

app = FastAPI(title=PRODUCT, version=VERSION)


def _database_url() -> str:
    value = os.getenv("CCS_DATABASE_URL", "").strip()
    if not value:
        raise RuntimeError("CCS_DATABASE_URL ist verpflichtend.")
    return value


def _identity_provider() -> IdentityProvider:
    tenant = os.getenv("CCS_TENANT_ID", "compelec").strip() or "compelec"
    return TrustedHeaderIdentityProvider(default_tenant_id=tenant)


def get_service(request: Request) -> SupportService:
    try:
        user = _identity_provider().authenticate(IdentityRequest(headers=request.headers))
        database_url = _database_url()
        tenant_name = os.getenv("CCS_TENANT_NAME", user.tenant_id).strip() or user.tenant_id
        repository = PostgresRepository(database_url, TenantContext(user.tenant_id))
        service = SupportService(
            repository,
            user,
            embedding_provider=build_embedding_provider_from_env(),
        )
        service.ensure_tenant(tenant_name)
        return service
    except AuthenticationError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc
    except AuthorizationError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc


@app.on_event("startup")
def startup() -> None:
    apply_postgres_migrations(_database_url())


@app.exception_handler(AuthorizationError)
def authorization_error_handler(request: Request, exc: AuthorizationError):
    from fastapi.responses import JSONResponse
    return JSONResponse(status_code=403, content={"detail": str(exc)})


@app.get("/health")
def health(service: SupportService = Depends(get_service)) -> dict[str, Any]:
    return {
        "status": "ok" if service.repository.healthcheck() else "degraded",
        "product": PRODUCT,
        "version": VERSION,
        "tenant": service.user.tenant_id,
        "identity": _identity_provider().provider_name,
    }


@app.get("/v1/tickets")
def list_tickets(service: SupportService = Depends(get_service)):
    return service.list_tickets()


class TicketCreate(BaseModel):
    subject: str = Field(min_length=1, max_length=200)
    description: str = Field(min_length=1)
    customer: str = Field(min_length=1, max_length=200)
    priority: str = "Mittel"


@app.post("/v1/tickets", status_code=201)
def create_ticket(payload: TicketCreate, service: SupportService = Depends(get_service)):
    ticket_no = service.create_ticket(**payload.model_dump())
    return {"ticket_no": ticket_no}


class AssistantAsk(BaseModel):
    question: str = Field(min_length=1)
    privacy_level: str = "internal"


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


@app.get("/v1/metrics")
def metrics(service: SupportService = Depends(get_service)):
    return service.get_metrics()
