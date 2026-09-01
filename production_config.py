from __future__ import annotations

import os
from dataclasses import dataclass
from urllib.parse import urlparse


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

    @property
    def is_production(self) -> bool:
        return self.environment == "production"


def load_production_config() -> ProductionConfig:
    database_url = os.getenv("CCS_DATABASE_URL", "").strip()
    tenant_id = os.getenv("CCS_TENANT_ID", "").strip()
    tenant_name = os.getenv("CCS_TENANT_NAME", tenant_id).strip()
    embedding_provider = os.getenv("CCS_EMBEDDING_PROVIDER", "local-hash").strip().lower()
    identity_mode = os.getenv("CCS_IDENTITY_MODE", "trusted-header").strip().lower()
    environment = os.getenv("CCS_ENVIRONMENT", "development").strip().lower()

    errors: list[str] = []
    if not database_url:
        errors.append("CCS_DATABASE_URL fehlt")
    else:
        parsed = urlparse(database_url)
        if parsed.scheme not in {"postgresql", "postgres"}:
            errors.append("CCS_DATABASE_URL muss PostgreSQL verwenden")
    if not tenant_id:
        errors.append("CCS_TENANT_ID fehlt")
    if environment not in {"development", "test", "production"}:
        errors.append("CCS_ENVIRONMENT ist ungültig")
    if identity_mode not in {"trusted-header"}:
        errors.append("CCS_IDENTITY_MODE ist nicht freigegeben")

    if environment == "production":
        if embedding_provider in {"local", "local-hash", "ccs-local-hash-v1"}:
            errors.append("lokaler Hash-Embedding-Provider ist in Produktion verboten")
        if parsed.scheme in {"postgresql", "postgres"} and parsed.hostname in {"localhost", "127.0.0.1"}:
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
    )
