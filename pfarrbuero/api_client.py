"""Small standard-library HTTP client used by the Windows desktop UI."""
from __future__ import annotations
import json
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from collections.abc import Callable

class ApiCaseStore:
    def __init__(self,base_url:str,token_provider:Callable[[],str]):
        self.base_url=base_url.rstrip("/"); self.token_provider=token_provider
        if not self.base_url: raise RuntimeError("PFARRBUERO_API_URL ist nicht konfiguriert.")
        if not callable(self.token_provider): raise RuntimeError("Ein OIDC-Tokenprovider ist erforderlich.")
    def _request(self,method,path,payload=None):
        body=None if payload is None else json.dumps(payload).encode("utf-8")
        request=Request(self.base_url+path,data=body,method=method,headers={
          "Authorization":f"Bearer {self.token_provider()}","Accept":"application/json","Content-Type":"application/json"})
        try:
            with urlopen(request,timeout=15) as response:
                raw=response.read(); return json.loads(raw.decode("utf-8")) if raw else None
        except HTTPError as exc:
            if exc.code==401: raise RuntimeError("Anmeldung abgelaufen oder ungültig. Bitte erneut anmelden.") from exc
            if exc.code==403: raise PermissionError("Für diese Aktion fehlen die erforderlichen Rechte.") from exc
            detail=exc.read().decode("utf-8",errors="replace")[:500]
            raise RuntimeError(f"API-Fehler {exc.code}: {detail}") from exc
        except URLError as exc: raise RuntimeError(f"Pfarrbüro-API nicht erreichbar: {exc.reason}") from exc
    def health_check(self): self._request("GET","/v1/me")
    def list_cases(self):
        return [(r["case_type"],r["subject"],r["status"]) for r in self._request("GET","/v1/cases")]
    def create_case(self,case_type,subject):
        self._request("POST","/v1/cases",{"case_type":case_type,"subject":subject})
    def list_admin_org_units(self): return self._request("GET","/v1/admin/org-units")
    def create_admin_org_unit(self,unit_type,unit_key,display_name,parent_id=None):
        return self._request("POST","/v1/admin/org-units",{"unit_type":unit_type,"unit_key":unit_key,
            "display_name":display_name,"parent_id":parent_id})
    def list_admin_users(self): return self._request("GET","/v1/admin/users")
    def create_admin_user(self,email,display_name):
        return self._request("POST","/v1/admin/users",{"email":email,"display_name":display_name})
    def list_admin_roles(self): return self._request("GET","/v1/admin/roles")
    def create_admin_membership(self,user_id,org_unit_id,role_key):
        return self._request("POST","/v1/admin/memberships",{"user_id":user_id,"org_unit_id":org_unit_id,"role_key":role_key})
