"""Desktop OIDC Authorization Code + PKCE client.

Access tokens stay in memory. Refresh tokens are persisted in Windows Credential
Manager through keyring's Windows Vault backend. No client secret is used.
"""
from __future__ import annotations

import base64
import hashlib
import json
import os
import secrets
import threading
import time
import urllib.parse
import urllib.request
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any

import jwt
import keyring
from jwt import PyJWKClient


SERVICE_NAME = "COMPELEC ONE Pfarrbuero-KI"
TOKEN_ACCOUNT = "oidc-refresh-token"


def _b64url(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


def create_pkce_pair() -> tuple[str, str]:
    verifier = _b64url(secrets.token_bytes(48))
    challenge = _b64url(hashlib.sha256(verifier.encode("ascii")).digest())
    return verifier, challenge


def verify_oauth_state(received: str, expected: str) -> None:
    if not received or not secrets.compare_digest(received, expected):
        raise RuntimeError("OIDC state stimmt nicht überein; Anmeldung abgebrochen.")


class OidcAuthClient:
    def __init__(self):
        if os.name != "nt":
            raise RuntimeError("Der sichere OIDC-Token-Speicher ist für Windows vorgesehen.")
        from keyring.backends.Windows import WinVaultKeyring
        keyring.set_keyring(WinVaultKeyring())
        self.issuer = os.getenv("PFARRBUERO_OIDC_ISSUER", "").rstrip("/")
        self.client_id = os.getenv("PFARRBUERO_OIDC_CLIENT_ID", "").strip()
        self.scope = os.getenv("PFARRBUERO_OIDC_SCOPE", "openid profile offline_access")
        self._metadata: dict[str, Any] | None = None
        self._access_token: str | None = None
        self._access_expires_at = 0.0
        if not self.issuer or not self.client_id:
            raise RuntimeError("PFARRBUERO_OIDC_ISSUER und PFARRBUERO_OIDC_CLIENT_ID müssen konfiguriert sein.")
        parsed = urllib.parse.urlparse(self.issuer)
        if parsed.scheme != "https" and parsed.hostname not in ("localhost", "127.0.0.1"):
            raise RuntimeError("OIDC-Issuer muss HTTPS verwenden.")

    def _request_json(self, url: str, data: dict[str, str] | None = None) -> dict[str, Any]:
        body = None if data is None else urllib.parse.urlencode(data).encode("utf-8")
        request = urllib.request.Request(
            url, data=body,
            headers={"Accept": "application/json", "Content-Type": "application/x-www-form-urlencoded"},
        )
        with urllib.request.urlopen(request, timeout=20) as response:
            result = json.loads(response.read().decode("utf-8"))
        if not isinstance(result, dict):
            raise RuntimeError("Ungültige Antwort des Identity Providers.")
        return result

    def _discovery(self) -> dict[str, Any]:
        if self._metadata is None:
            metadata = self._request_json(self.issuer + "/.well-known/openid-configuration")
            if metadata.get("issuer", "").rstrip("/") != self.issuer:
                raise RuntimeError("OIDC-Discovery-Issuer stimmt nicht mit der Konfiguration überein.")
            for field in ("authorization_endpoint", "token_endpoint", "jwks_uri"):
                endpoint = metadata.get(field, "")
                parsed = urllib.parse.urlparse(endpoint)
                if not endpoint or (parsed.scheme != "https" and parsed.hostname not in ("localhost", "127.0.0.1")):
                    raise RuntimeError(f"OIDC-Discovery liefert keinen sicheren {field}.")
            self._metadata = metadata
        return self._metadata

    def _validate_id_token(self, token: str, nonce: str) -> None:
        metadata = self._discovery()
        signing_key = PyJWKClient(metadata["jwks_uri"]).get_signing_key_from_jwt(token).key
        claims = jwt.decode(
            token, signing_key, algorithms=["RS256"],
            issuer=self.issuer, audience=self.client_id,
            options={"require": ["exp", "iat", "sub", "nonce"]}, leeway=30,
        )
        if not secrets.compare_digest(str(claims.get("nonce", "")), nonce):
            raise jwt.InvalidTokenError("OIDC nonce stimmt nicht überein.")

    def _exchange(self, data: dict[str, str]) -> dict[str, Any]:
        metadata = self._discovery()
        result = self._request_json(metadata["token_endpoint"], data)
        access = result.get("access_token")
        if not isinstance(access, str) or not access:
            raise RuntimeError("Identity Provider hat kein Access-Token geliefert.")
        if "id_token" in result:
            # The initial authorization response must carry an ID token. Refresh responses
            # may omit it depending on provider policy.
            pass
        self._access_token = access
        self._access_expires_at = time.time() + max(30, int(result.get("expires_in", 300)) - 30)
        refresh = result.get("refresh_token")
        if isinstance(refresh, str) and refresh:
            keyring.set_password(SERVICE_NAME, TOKEN_ACCOUNT, refresh)
        return result

    def login(self) -> str:
        metadata = self._discovery()
        verifier, challenge = create_pkce_pair()
        state, nonce = secrets.token_urlsafe(32), secrets.token_urlsafe(32)
        received: dict[str, str] = {}
        completed = threading.Event()

        class CallbackHandler(BaseHTTPRequestHandler):
            def do_GET(self):
                parsed = urllib.parse.urlparse(self.path)
                query = urllib.parse.parse_qs(parsed.query)
                received["state"] = query.get("state", [""])[0]
                received["code"] = query.get("code", [""])[0]
                received["error"] = query.get("error", [""])[0]
                self.send_response(200 if received["code"] else 400)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Cache-Control", "no-store")
                self.end_headers()
                self.wfile.write(
                    b"<html><body><h2>COMPELEC ONE</h2><p>Anmeldung verarbeitet. "
                    b"Dieses Fenster kann geschlossen werden.</p></body></html>"
                )
                completed.set()

            def log_message(self, *_args):
                return

        server = HTTPServer(("127.0.0.1", 0), CallbackHandler)
        server.timeout = 1
        port = server.server_address[1]
        redirect_uri = f"http://127.0.0.1:{port}/callback"
        params = {
            "response_type": "code", "client_id": self.client_id,
            "redirect_uri": redirect_uri, "scope": self.scope,
            "state": state, "nonce": nonce,
            "code_challenge": challenge, "code_challenge_method": "S256",
        }
        auth_url = metadata["authorization_endpoint"] + "?" + urllib.parse.urlencode(params)
        if not webbrowser.open(auth_url):
            server.server_close()
            raise RuntimeError("Der Browser konnte nicht geöffnet werden.")
        deadline = time.monotonic() + 180
        try:
            while not completed.is_set() and time.monotonic() < deadline:
                server.handle_request()
        finally:
            server.server_close()
        if not completed.is_set():
            raise TimeoutError("OIDC-Anmeldung wurde nicht innerhalb von drei Minuten abgeschlossen.")
        if received.get("error"):
            raise RuntimeError("OIDC-Anmeldung wurde vom Identity Provider abgebrochen.")
        verify_oauth_state(received.get("state", ""), state)
        code = received.get("code", "")
        if not code:
            raise RuntimeError("Kein Authorization Code empfangen.")

        tokens = self._exchange({
            "grant_type": "authorization_code", "client_id": self.client_id,
            "code": code, "redirect_uri": redirect_uri, "code_verifier": verifier,
        })
        id_token = tokens.get("id_token")
        if not isinstance(id_token, str):
            self.clear()
            raise RuntimeError("Identity Provider lieferte kein ID-Token.")
        try:
            self._validate_id_token(id_token, nonce)
        except Exception:
            self.clear()
            raise
        return self.access_token()

    def access_token(self) -> str:
        if self._access_token and time.time() < self._access_expires_at:
            return self._access_token
        refresh = keyring.get_password(SERVICE_NAME, TOKEN_ACCOUNT)
        if not refresh:
            raise RuntimeError("Keine aktive Anmeldung. Bitte anmelden.")
        result = self._exchange({
            "grant_type": "refresh_token", "client_id": self.client_id,
            "refresh_token": refresh,
        })
        return self._access_token or ""

    def clear(self) -> None:
        self._access_token = None
        self._access_expires_at = 0.0
        try:
            keyring.delete_password(SERVICE_NAME, TOKEN_ACCOUNT)
        except keyring.errors.PasswordDeleteError:
            pass
