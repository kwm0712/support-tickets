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

bearer=HTTPBearer(auto_error=False)
class CaseCreate(BaseModel):
    case_type: str=Field(min_length=1,max_length=80)
    subject: str=Field(min_length=1,max_length=500)
class CaseView(BaseModel):
    case_type: str
    subject: str
    status: str
class IdentityView(BaseModel):
    user_id: str
    tenant_id: str
    org_unit_id: str

@lru_cache(maxsize=1)
def _database_dsn():
    value=os.getenv("PFARRBUERO_DATABASE_URL","").strip()
    if not value: raise RuntimeError("PFARRBUERO_DATABASE_URL ist nicht konfiguriert.")
    return value

def get_current_principal(credentials: Annotated[HTTPAuthorizationCredentials|None,Depends(bearer)]) -> Principal:
    if credentials is None or credentials.scheme.lower()!="bearer":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,detail="Anmeldung erforderlich.",
                            headers={"WWW-Authenticate":"Bearer"})
    try: return decode_access_token(credentials.credentials)
    except jwt.PyJWTError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="Ungültiges oder abgelaufenes Zugriffstoken.",
                            headers={"WWW-Authenticate":"Bearer"}) from exc

def get_store(principal: Annotated[Principal,Depends(get_current_principal)]):
    return PostgresCaseStore(StoreConfig(_database_dsn(),principal.tenant_id,principal.org_unit_id,principal.user_id))

def create_app():
    app=FastAPI(title="COMPELEC ONE Pfarrbüro-KI API",version="2.0.3-dev",docs_url=None,redoc_url=None)
    @app.get("/healthz")
    def healthz(): return {"status":"ok","component":"pfarrbuero-api"}
    @app.get("/v1/me",response_model=IdentityView)
    def identity(principal: Annotated[Principal,Depends(get_current_principal)]):
        return IdentityView(user_id=principal.user_id,tenant_id=principal.tenant_id,org_unit_id=principal.org_unit_id)
    @app.get("/v1/cases",response_model=list[CaseView])
    def list_cases(store: Annotated[PostgresCaseStore,Depends(get_store)]):
        try: return [CaseView(case_type=r[0],subject=r[1],status=r[2]) for r in store.list_cases()]
        except PermissionError as exc: raise HTTPException(status_code=403,detail="Zugriff nicht gestattet.") from exc
    @app.post("/v1/cases",status_code=201)
    def create_case(payload: CaseCreate,store: Annotated[PostgresCaseStore,Depends(get_store)]):
        try:
            store.create_case(payload.case_type,payload.subject)
            return {"status":"created"}
        except PermissionError as exc: raise HTTPException(status_code=403,detail="Aktion nicht gestattet.") from exc
        except ValueError as exc: raise HTTPException(status_code=422,detail=str(exc)) from exc
    # Import after dependency definitions: admin routes reuse the same verified Principal.
    from admin_routes import router as admin_router
    app.include_router(admin_router)
    return app

app=create_app()
