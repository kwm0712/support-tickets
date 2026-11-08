"""REST routes for tenant and parish administration."""
from __future__ import annotations
import os
from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from security import Principal
from api import get_current_principal
from admin_repository import AdminConfig, AdminRepository

router=APIRouter(prefix="/v1/admin",tags=["administration"])

def get_admin_repository(principal: Annotated[Principal,Depends(get_current_principal)]):
    dsn=os.getenv("PFARRBUERO_DATABASE_URL","").strip()
    if not dsn: raise HTTPException(status_code=503,detail="Datenbank nicht konfiguriert.")
    return AdminRepository(AdminConfig(dsn,principal.tenant_id,principal.org_unit_id,principal.user_id))

class OrgUnitCreate(BaseModel):
    unit_type: str=Field(pattern="^(diocese|pastoral_region|parish|parish_office)$")
    unit_key: str=Field(min_length=2,max_length=80)
    display_name: str=Field(min_length=2,max_length=200)
    parent_id: str|None=None
class UserCreate(BaseModel):
    email: str=Field(min_length=3,max_length=320)
    display_name: str=Field(min_length=2,max_length=200)
class MembershipCreate(BaseModel):
    user_id: str
    org_unit_id: str
    role_key: str=Field(min_length=2,max_length=80)

def _call(fn):
    try: return fn()
    except PermissionError as exc: raise HTTPException(status_code=403,detail="Zugriff nicht gestattet.") from exc
    except ValueError as exc: raise HTTPException(status_code=422,detail=str(exc)) from exc

@router.get("/org-units")
def list_org_units(repo: Annotated[AdminRepository,Depends(get_admin_repository)]):
    return _call(repo.list_org_units)
@router.post("/org-units",status_code=201)
def create_org_unit(payload: OrgUnitCreate,repo: Annotated[AdminRepository,Depends(get_admin_repository)]):
    return _call(lambda:repo.create_org_unit(payload.unit_type,payload.unit_key,payload.display_name,payload.parent_id))
@router.get("/users")
def list_users(repo: Annotated[AdminRepository,Depends(get_admin_repository)]):
    return _call(repo.list_users)
@router.post("/users",status_code=201)
def create_user(payload: UserCreate,repo: Annotated[AdminRepository,Depends(get_admin_repository)]):
    return _call(lambda:repo.create_user(payload.email,payload.display_name))
@router.get("/roles")
def list_roles(repo: Annotated[AdminRepository,Depends(get_admin_repository)]):
    return _call(repo.list_roles)
@router.post("/memberships",status_code=201)
def create_membership(payload: MembershipCreate,repo: Annotated[AdminRepository,Depends(get_admin_repository)]):
    return _call(lambda:repo.create_membership(payload.user_id,payload.org_unit_id,payload.role_key))
