"""HTTP API: the only runtime boundary allowed to access PostgreSQL."""
from __future__ import annotations

import os
from functools import lru_cache
from typing import Annotated

import jwt
from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field

from repository import PostgresCaseStore, StoreConfig
from security import Principal, decode_access_token

bearer = HTTPBearer(auto_error=False)


class CaseCreate(BaseModel):
    case_type: str = Field(min_length=1, max_length=80)
    subject: str = Field(min_length=1, max_length=500)


class CaseView(BaseModel):
    case_type: str
    subject: str
    status: str


class IdentityView(BaseModel):
    user_id: str
    tenant_id: str
    org_unit_id: str


@lru_cache(maxsize=1)
def _database_dsn() -> str:
    value = os.getenv("PFARRBUERO_DATABASE_URL", "").strip()
    if not value:
        raise RuntimeError("PFARRBUERO_DATABASE_URL ist nicht konfiguriert.")
    return value


def get_current_principal(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
) -> Principal:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Anmeldung erforderlich.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        return decode_access_token(credentials.credentials)
    except jwt.PyJWTError as exc:
        # Do not disclose token-validation internals to clients.
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Ungültiges oder abgelaufenes Zugriffstoken.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc


def get_store(
    principal: Annotated[Principal, Depends(get_current_principal)],
) -> PostgresCaseStore:
    # Tenant, org unit and actor are taken exclusively from signed server-verified claims.
    config = StoreConfig(
        dsn=_database_dsn(),
        tenant_id=principal.tenant_id,
        org_unit_id=principal.org_unit_id,
        actor_user_id=principal.user_id,
    )
    return PostgresCaseStore(config)


def create_app() -> FastAPI:
    app = FastAPI(
        title="COMPELEC ONE Pfarrbüro-KI API",
        version="2.0.1-dev",
        docs_url=None,
        redoc_url=None,
    )

    @app.get("/healthz")
    def healthz():
        return {"status": "ok", "component": "pfarrbuero-api"}

    @app.get("/v1/me", response_model=IdentityView)
    def identity(principal: Annotated[Principal, Depends(get_current_principal)]):
        return IdentityView(
            user_id=principal.user_id,
            tenant_id=principal.tenant_id,
            org_unit_id=principal.org_unit_id,
        )

    @app.get("/v1/cases", response_model=list[CaseView])
    def list_cases(store: Annotated[PostgresCaseStore, Depends(get_store)]):
        try:
            return [
                CaseView(case_type=row[0], subject=row[1], status=row[2])
                for row in store.list_cases()
            ]
        except PermissionError as exc:
            raise HTTPException(status_code=403, detail="Zugriff nicht gestattet.") from exc

    @app.post("/v1/cases", status_code=201)
    def create_case(
        payload: CaseCreate,
        store: Annotated[PostgresCaseStore, Depends(get_store)],
    ):
        try:
            store.create_case(payload.case_type, payload.subject)
            return {"status": "created"}
        except PermissionError as exc:
            raise HTTPException(status_code=403, detail="Aktion nicht gestattet.") from exc
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

    return app


app = create_app()
