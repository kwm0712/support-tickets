"""Small standard-library HTTP client used by the Windows desktop UI."""
from __future__ import annotations

import json
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from collections.abc import Callable


class ApiCaseStore:
    def __init__(self, base_url: str, token_provider: Callable[[], str]):
        self.base_url = base_url.rstrip("/")
        self.token_provider = token_provider
        if not self.base_url:
            raise RuntimeError("PFARRBUERO_API_URL ist nicht konfiguriert.")
        if not callable(self.token_provider):
            raise RuntimeError("Ein OIDC-Tokenprovider ist erforderlich.")

    def _request(self, method: str, path: str, payload=None):
        body = None if payload is None else json.dumps(payload).encode("utf-8")
        request = Request(
            self.base_url + path,
            data=body,
            method=method,
            headers={
                "Authorization": f"Bearer {self.token_provider()}",
                "Accept": "application/json",
                "Content-Type": "application/json",
            },
        )
        try:
            with urlopen(request, timeout=15) as response:
                raw = response.read()
                return json.loads(raw.decode("utf-8")) if raw else None
        except HTTPError as exc:
            if exc.code == 401:
                raise RuntimeError("Anmeldung abgelaufen oder ungültig. Bitte erneut anmelden.") from exc
            if exc.code == 403:
                raise PermissionError("Für diese Aktion fehlen die erforderlichen Rechte.") from exc
            detail = exc.read().decode("utf-8", errors="replace")[:500]
            raise RuntimeError(f"API-Fehler {exc.code}: {detail}") from exc
        except URLError as exc:
            raise RuntimeError(f"Pfarrbüro-API nicht erreichbar: {exc.reason}") from exc

    def health_check(self):
        self._request("GET", "/v1/me")

    def list_cases(self):
        rows = self._request("GET", "/v1/cases")
        return [(row["case_type"], row["subject"], row["status"]) for row in rows]

    def create_case(self, case_type: str, subject: str):
        self._request("POST", "/v1/cases", {"case_type": case_type, "subject": subject})
