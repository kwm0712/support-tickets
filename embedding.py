from __future__ import annotations

import hashlib
import math
import re
from dataclasses import dataclass
from typing import Protocol


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


def cosine_similarity(left: EmbeddingVector, right: EmbeddingVector) -> float:
    if left.dimensions != right.dimensions:
        raise ValueError("Embedding-Dimensionen stimmen nicht überein.")
    if len(left.values) != left.dimensions or len(right.values) != right.dimensions:
        raise ValueError("Embedding-Vektor hat eine ungültige Länge.")
    return sum(a * b for a, b in zip(left.values, right.values, strict=True))
