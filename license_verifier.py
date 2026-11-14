from __future__ import annotations

import base64
import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

PRODUCT_ID = "compelec-one-business"

class LicenseValidationError(ValueError):
    """Signed license is invalid or unavailable."""

@dataclass(frozen=True)
class VerifiedLicense:
    tenant_id: str
    issued_at: datetime
    expires_at: datetime
    features: tuple[str, ...]

def _decode_b64(value: str, label: str) -> bytes:
    try:
        return base64.b64decode(value, validate=True)
    except Exception as exc:
        raise LicenseValidationError(f"{label} ist kein gültiges Base64.") from exc

def _parse_utc(value: Any, label: str) -> datetime:
    if not isinstance(value, str) or not value.strip():
        raise LicenseValidationError(f"Lizenzfeld {label} fehlt.")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise LicenseValidationError(f"Lizenzfeld {label} ist kein ISO-8601-Zeitstempel.") from exc
    if parsed.tzinfo is None:
        raise LicenseValidationError(f"Lizenzfeld {label} benötigt eine Zeitzone.")
    return parsed.astimezone(timezone.utc)

def verify_license_file(license_path: str | Path, public_key_b64: str, *, expected_tenant: str, now: datetime | None = None) -> VerifiedLicense:
    """Verify canonical JSON payload signed offline with an Ed25519 private key."""
    if not public_key_b64.strip():
        raise LicenseValidationError("Öffentlicher Lizenzprüfschlüssel fehlt.")
    try:
        envelope = json.loads(Path(license_path).read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise LicenseValidationError("Lizenzdatei fehlt oder ist kein gültiges JSON.") from exc
    if not isinstance(envelope, dict) or set(envelope) != {"payload", "signature"}:
        raise LicenseValidationError("Lizenzcontainer hat ein ungültiges Format.")
    payload = envelope["payload"]
    if not isinstance(payload, dict) or not {"product", "tenant_id", "issued_at", "expires_at", "features"}.issubset(payload):
        raise LicenseValidationError("Lizenz-Payload enthält nicht alle Pflichtfelder.")
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    public_bytes = _decode_b64(public_key_b64.strip(), "Öffentlicher Schlüssel")
    signature = _decode_b64(str(envelope["signature"]), "Lizenzsignatur")
    if len(public_bytes) != 32 or len(signature) != 64:
        raise LicenseValidationError("Schlüssellänge oder Signaturlänge ist ungültig.")
    try:
        Ed25519PublicKey.from_public_bytes(public_bytes).verify(signature, canonical)
    except (InvalidSignature, ValueError) as exc:
        raise LicenseValidationError("Lizenzsignatur ist ungültig oder wurde verändert.") from exc
    if payload["product"] != PRODUCT_ID:
        raise LicenseValidationError("Lizenz ist nicht für COMPELEC ONE Business ausgestellt.")
    tenant_id = payload["tenant_id"]
    if not isinstance(tenant_id, str) or not tenant_id.strip() or tenant_id != expected_tenant:
        raise LicenseValidationError("Lizenzmandant fehlt oder Lizenz ist für einen anderen Mandanten ausgestellt.")
    features = payload["features"]
    if not isinstance(features, list) or not all(isinstance(item, str) and item for item in features):
        raise LicenseValidationError("Lizenzmerkmale sind ungültig.")
    issued_at = _parse_utc(payload["issued_at"], "issued_at")
    expires_at = _parse_utc(payload["expires_at"], "expires_at")
    current = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    if issued_at > current:
        raise LicenseValidationError("Lizenz ist noch nicht gültig.")
    if expires_at <= current or expires_at <= issued_at:
        raise LicenseValidationError("Lizenz ist abgelaufen oder hat eine ungültige Laufzeit.")
    return VerifiedLicense(tenant_id, issued_at, expires_at, tuple(features))

def load_and_verify_runtime_license() -> VerifiedLicense:
    path = os.getenv("CCS_LICENSE_FILE", "").strip()
    public_key = os.getenv("CCS_LICENSE_PUBLIC_KEY_ED25519", "").strip()
    tenant = os.getenv("CCS_TENANT_ID", "").strip()
    if not path:
        raise LicenseValidationError("CCS_LICENSE_FILE ist nicht konfiguriert.")
    if not tenant:
        raise LicenseValidationError("CCS_TENANT_ID fehlt für die Lizenzbindung.")
    return verify_license_file(path, public_key, expected_tenant=tenant)