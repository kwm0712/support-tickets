from __future__ import annotations

import hashlib
import json
import math
import os
import re
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Callable, Protocol


@dataclass(frozen=True)
class EmbeddingVector:
    model_id: str
    dimensions: int
    values: tuple[float, ...]


class EmbeddingProvider(Protocol):
    model_id: str
    dimensions: int

    def embed(self, text: str) -> EmbeddingVector:
        ...


class DeterministicLocalEmbeddingProvider:
    """Deterministic, local-only embedding provider for V0.3 architecture/tests.

    This provider is intentionally not a semantic production model. It supplies a stable
    vector contract so PostgreSQL/pgvector, migrations and retrieval orchestration can be
    developed without activating an external AI provider.
    """

    model_id = "ccs-local-hash-v1"
    dimensions = 64

    def embed(self, text: str) -> EmbeddingVector:
        tokens = [
            token.lower()
            for token in re.findall(r"[\wäöüÄÖÜß-]+", text, flags=re.UNICODE)
            if len(token) >= 2
        ]
        values = [0.0] * self.dimensions
        if not tokens:
            return EmbeddingVector(self.model_id, self.dimensions, tuple(values))

        for token in tokens:
            digest = hashlib.sha256(token.encode("utf-8")).digest()
            for offset in range(0, len(digest), 2):
                bucket = int.from_bytes(digest[offset : offset + 2], "big") % self.dimensions
                sign = 1.0 if digest[offset] % 2 == 0 else -1.0
                values[bucket] += sign

        norm = math.sqrt(sum(value * value for value in values))
        if norm:
            values = [value / norm for value in values]
        return EmbeddingVector(self.model_id, self.dimensions, tuple(values))


class OpenAICompatibleEmbeddingProvider:
    """Production-oriented embedding provider using an OpenAI-compatible HTTP API.

    The endpoint, model and API key are supplied through deployment configuration. The
    implementation deliberately depends only on the Python standard library so the V0.3
    runtime does not require an additional SDK. It validates response shape and vector
    dimensions and performs bounded retries for transient transport/service failures.
    """

    def __init__(
        self,
        *,
        endpoint: str,
        api_key: str,
        model_id: str,
        dimensions: int,
        timeout_seconds: float = 20.0,
        max_retries: int = 2,
        opener: Callable[..., object] | None = None,
    ) -> None:
        endpoint = endpoint.strip()
        api_key = api_key.strip()
        model_id = model_id.strip()
        if not endpoint.startswith("https://"):
            raise ValueError("Der Produktions-Embedding-Endpunkt muss HTTPS verwenden.")
        if not api_key:
            raise ValueError("API-Schlüssel für Produktions-Embedding fehlt.")
        if not model_id:
            raise ValueError("Embedding-Modell-ID fehlt.")
        if dimensions <= 0:
            raise ValueError("Embedding-Dimensionen müssen größer als 0 sein.")
        if timeout_seconds <= 0:
            raise ValueError("Embedding-Timeout muss größer als 0 sein.")
        if max_retries < 0 or max_retries > 5:
            raise ValueError("Embedding-Retry-Anzahl muss zwischen 0 und 5 liegen.")

        self.endpoint = endpoint
        self.api_key = api_key
        self.model_id = model_id
        self.dimensions = dimensions
        self.timeout_seconds = timeout_seconds
        self.max_retries = max_retries
        self._opener = opener or urllib.request.urlopen

    def embed(self, text: str) -> EmbeddingVector:
        if not text or not text.strip():
            return EmbeddingVector(
                self.model_id,
                self.dimensions,
                tuple(0.0 for _ in range(self.dimensions)),
            )

        payload = json.dumps(
            {
                "model": self.model_id,
                "input": text,
                "dimensions": self.dimensions,
            }
        ).encode("utf-8")
        request = urllib.request.Request(
            self.endpoint,
            data=payload,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "Accept": "application/json",
                "User-Agent": "CCS-Agent-Support/0.3",
            },
            method="POST",
        )

        last_error: Exception | None = None
        for attempt in range(self.max_retries + 1):
            try:
                with self._opener(request, timeout=self.timeout_seconds) as response:
                    body = response.read().decode("utf-8")
                parsed = json.loads(body)
                values = parsed["data"][0]["embedding"]
                if not isinstance(values, list):
                    raise RuntimeError("Embedding-Antwort enthält keinen gültigen Vektor.")
                vector = tuple(float(value) for value in values)
                if len(vector) != self.dimensions:
                    raise RuntimeError(
                        "Embedding-Dimension stimmt nicht mit der Konfiguration überein: "
                        f"erwartet {self.dimensions}, erhalten {len(vector)}."
                    )
                return EmbeddingVector(self.model_id, self.dimensions, vector)
            except (
                urllib.error.HTTPError,
                urllib.error.URLError,
                TimeoutError,
                json.JSONDecodeError,
                KeyError,
                IndexError,
                TypeError,
                ValueError,
                RuntimeError,
            ) as exc:
                last_error = exc
                if attempt >= self.max_retries:
                    break
                time.sleep(min(0.25 * (2**attempt), 1.0))

        raise RuntimeError(
            f"Produktions-Embedding fehlgeschlagen nach {self.max_retries + 1} Versuch(en)."
        ) from last_error


def build_embedding_provider_from_env() -> EmbeddingProvider:
    """Build the configured provider and fail closed for invalid production settings."""

    provider = os.getenv("CCS_EMBEDDING_PROVIDER", "local-hash").strip().lower()
    if provider in {"local", "local-hash", "ccs-local-hash-v1"}:
        return DeterministicLocalEmbeddingProvider()
    if provider not in {"openai-compatible", "production"}:
        raise RuntimeError(f"Unbekannter Embedding-Provider: {provider}")

    endpoint = os.getenv("CCS_EMBEDDING_ENDPOINT", "").strip()
    api_key = os.getenv("CCS_EMBEDDING_API_KEY", "").strip()
    model_id = os.getenv("CCS_EMBEDDING_MODEL", "").strip()
    dimensions_raw = os.getenv("CCS_EMBEDDING_DIMENSIONS", "").strip()
    timeout_raw = os.getenv("CCS_EMBEDDING_TIMEOUT_SECONDS", "20").strip()
    retries_raw = os.getenv("CCS_EMBEDDING_MAX_RETRIES", "2").strip()

    if not dimensions_raw:
        raise RuntimeError("CCS_EMBEDDING_DIMENSIONS ist für Produktions-Embedding erforderlich.")
    try:
        dimensions = int(dimensions_raw)
        timeout_seconds = float(timeout_raw)
        max_retries = int(retries_raw)
    except ValueError as exc:
        raise RuntimeError("Ungültige numerische Produktions-Embedding-Konfiguration.") from exc

    return OpenAICompatibleEmbeddingProvider(
        endpoint=endpoint,
        api_key=api_key,
        model_id=model_id,
        dimensions=dimensions,
        timeout_seconds=timeout_seconds,
        max_retries=max_retries,
    )


def cosine_similarity(left: EmbeddingVector, right: EmbeddingVector) -> float:
    if left.dimensions != right.dimensions:
        raise ValueError("Embedding-Dimensionen stimmen nicht überein.")
    if len(left.values) != left.dimensions or len(right.values) != right.dimensions:
        raise ValueError("Embedding-Vektor hat eine ungültige Länge.")
    return sum(a * b for a, b in zip(left.values, right.values, strict=True))
