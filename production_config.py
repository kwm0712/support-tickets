from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from urllib.parse import urlparse

from architecture import ROLE_PERMISSIONS


class ProductionConfigError(RuntimeError):
    pass


@dataclass(frozen=True)
class ProductionConfig:
    database_url: str
    tenant_id: str
    tenant_name: str
    embedding_provider: str
    identity_mode: str
    environment: str
    oidc_issuer: str = ""
    oidc_audience: str = ""
    oidc_jwks_url: str = ""
    oidc_role_claim: str = "roles"
    oidc_tenant_claim: str = "tid"
    oidc_username_claim: str = "preferred_username"
    oidc_role_map: dict[str, str] = field(default_factory=dict)
    oidc_tenant_map: dict[str, str] = field(default_factory=dict)
    trusted_tenant_map: dict[str, str] = field(default_factory=dict)

    @property
    def is_production(self) -> bool:
        return self.environment == "production"


def load_production_config() -> ProductionConfig:
    database_url = os.getenv("CCS_DATABASE_URL", "").strip()
    tenant_id = os.getenv("CCS_TENANT_ID", "").strip()
    tenant_name = os.getenv("CCS_TENANT_NAME", tenant_id).strip()
    embedding_provider = os.getenv("CCS_EMBEDDING_PROVIDER", "local-hash").strip().lower()
    identity_mode = os.getenv("CCS_IDENTITY_MODE", "trusted-header").strip().lower()
    trusted_header_ack = os.getenv("CCS_TRUSTED_HEADER_MODE_ACK", "").strip()
    environment = os.getenv("CCS_ENVIRONMENT", "development").strip().lower()

    oidc_issuer = os.getenv("CCS_OIDC_ISSUER", "").strip()
    oidc_audience = os.getenv("CCS_OIDC_AUDIENCE", "").strip()
    oidc_jwks_url = os.getenv("CCS_OIDC_JWKS_URL", "").strip()
    oidc_role_claim = os.getenv("CCS_OIDC_ROLE_CLAIM", "roles").strip()
    oidc_tenant_claim = os.getenv("CCS_OIDC_TENANT_CLAIM", "tid").strip()
    oidc_username_claim = os.getenv("CCS_OIDC_USERNAME_CLAIM", "preferred_username").strip()
    role_map_raw = os.getenv("CCS_OIDC_ROLE_MAP", "").strip()
    tenant_map_raw = os.getenv("CCS_OIDC_TENANT_MAP", "").strip()
    trusted_tenant_map_raw = os.getenv("CCS_TRUSTED_TENANT_MAP", "").strip()

    errors: list[str] = []
    parsed = urlparse(database_url) if database_url else None
    if not database_url:
        errors.append("CCS_DATABASE_URL fehlt")
    elif parsed and parsed.scheme not in {"postgresql", "postgres"}:
        errors.append("CCS_DATABASE_URL muss PostgreSQL verwenden")
    if not tenant_id:
        errors.append("CCS_TENANT_ID fehlt")
    if environment not in {"development", "test", "production"}:
        errors.append("CCS_ENVIRONMENT ist ungültig")
    if identity_mode not in {"trusted-header", "oidc"}:
        errors.append("CCS_IDENTITY_MODE muss trusted-header oder oidc sein")

    oidc_role_map: dict[str, str] = {}
    oidc_tenant_map: dict[str, str] = {}
    trusted_tenant_map: dict[str, str] = {}
    if role_map_raw:
        try:
            parsed_role_map = json.loads(role_map_raw)
            if not isinstance(parsed_role_map, dict):
                raise ValueError("Mapping muss ein JSON-Objekt sein.")
            if not all(isinstance(key, str) and isinstance(value, str) for key, value in parsed_role_map.items()):
                raise ValueError("Mapping-Schlüssel und -Werte müssen Zeichenketten sein.")
            oidc_role_map = parsed_role_map
        except (json.JSONDecodeError, ValueError) as exc:
            errors.append(f"CCS_OIDC_ROLE_MAP ist ungültig: {exc}")
    if tenant_map_raw:
        try:
            parsed_tenant_map = json.loads(tenant_map_raw)
            if not isinstance(parsed_tenant_map, dict):
                raise ValueError("Mapping muss ein JSON-Objekt sein.")
            if not all(isinstance(key, str) and isinstance(value, str) for key, value in parsed_tenant_map.items()):
                raise ValueError("Mapping-Schlüssel und -Werte müssen Zeichenketten sein.")
            oidc_tenant_map = parsed_tenant_map
        except (json.JSONDecodeError, ValueError) as exc:
            errors.append(f"CCS_OIDC_TENANT_MAP ist ungültig: {exc}")
    if trusted_tenant_map_raw:
        try:
            parsed_trusted_tenant_map = json.loads(trusted_tenant_map_raw)
            if not isinstance(parsed_trusted_tenant_map, dict):
                raise ValueError("Mapping muss ein JSON-Objekt sein.")
            if not all(isinstance(key, str) and isinstance(value, str) for key, value in parsed_trusted_tenant_map.items()):
                raise ValueError("Mapping-Schlüssel und -Werte müssen Zeichenketten sein.")
            trusted_tenant_map = parsed_trusted_tenant_map
        except (json.JSONDecodeError, ValueError) as exc:
            errors.append(f"CCS_TRUSTED_TENANT_MAP ist ungültig: {exc}")

    if environment == "production" and identity_mode == "trusted-header":
        if not trusted_tenant_map:
            errors.append("CCS_TRUSTED_TENANT_MAP muss für produktive Trusted-Header-Authentifizierung explizit gesetzt sein")
        if any(not key.strip() or not value.strip() for key, value in trusted_tenant_map.items()):
            errors.append("CCS_TRUSTED_TENANT_MAP enthält leere Kennungen")
        if trusted_header_ack != "I_TRUST_MY_AUTHENTICATING_PROXY":
            errors.append("Trusted-Header-Authentifizierung in Produktion erfordert explizite Proxy-Vertrauensbestätigung CCS_TRUSTED_HEADER_MODE_ACK")

    if identity_mode == "oidc":
        if not oidc_issuer.startswith("https://"):
            errors.append("CCS_OIDC_ISSUER muss eine HTTPS-Adresse sein")
        if not oidc_audience:
            errors.append("CCS_OIDC_AUDIENCE fehlt")
        if not oidc_jwks_url.startswith("https://"):
            errors.append("CCS_OIDC_JWKS_URL muss eine HTTPS-Adresse sein")
        if not oidc_role_claim or not oidc_tenant_claim:
            errors.append("OIDC-Rollen- und Mandanten-Claim müssen gesetzt sein")
        if environment == "production" and not oidc_role_map:
            errors.append("CCS_OIDC_ROLE_MAP muss in Produktion explizit gesetzt sein")
        if not oidc_tenant_map:
            errors.append("CCS_OIDC_TENANT_MAP muss für OIDC explizit gesetzt sein")
        if any(not key.strip() or not value.strip() for key, value in oidc_tenant_map.items()):
            errors.append("CCS_OIDC_TENANT_MAP enthält leere Kennungen")
        if any(target not in ROLE_PERMISSIONS for target in oidc_role_map.values()):
            errors.append("CCS_OIDC_ROLE_MAP enthält eine unbekannte COMPELEC-Rolle")

    if errors:
        raise ProductionConfigError("; ".join(errors))

    if environment == "production":
        if embedding_provider in {"local", "local-hash", "ccs-local-hash-v1"}:
            errors.append("lokaler Hash-Embedding-Provider ist in Produktion verboten")
        if parsed and parsed.hostname in {"localhost", "127.0.0.1"}:
            errors.append("Produktionsdatenbank darf nicht auf localhost zeigen")

    if errors:
        raise ProductionConfigError("; ".join(errors))

    return ProductionConfig(
        database_url=database_url,
        tenant_id=tenant_id,
        tenant_name=tenant_name or tenant_id,
        embedding_provider=embedding_provider,
        identity_mode=identity_mode,
        environment=environment,
        oidc_issuer=oidc_issuer,
        oidc_audience=oidc_audience,
        oidc_jwks_url=oidc_jwks_url,
        oidc_role_claim=oidc_role_claim,
        oidc_tenant_claim=oidc_tenant_claim,
        oidc_username_claim=oidc_username_claim,
        oidc_role_map=oidc_role_map,
        oidc_tenant_map=oidc_tenant_map,
        trusted_tenant_map=trusted_tenant_map,
    )
