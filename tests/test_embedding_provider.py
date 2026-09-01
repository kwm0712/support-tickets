from __future__ import annotations

import json
import os
import unittest
from unittest.mock import patch

from embedding import (
    DeterministicLocalEmbeddingProvider,
    OpenAICompatibleEmbeddingProvider,
    build_embedding_provider_from_env,
)


class _FakeResponse:
    def __init__(self, payload: dict) -> None:
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def read(self) -> bytes:
        return json.dumps(self.payload).encode("utf-8")


class EmbeddingProviderTests(unittest.TestCase):
    def test_local_provider_remains_default(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            provider = build_embedding_provider_from_env()
        self.assertIsInstance(provider, DeterministicLocalEmbeddingProvider)

    def test_production_provider_validates_https(self) -> None:
        with self.assertRaises(ValueError):
            OpenAICompatibleEmbeddingProvider(
                endpoint="http://localhost/v1/embeddings",
                api_key="secret",
                model_id="approved-model",
                dimensions=3,
            )

    def test_production_provider_parses_and_validates_vector(self) -> None:
        def opener(request, timeout):
            self.assertEqual(timeout, 3.0)
            self.assertEqual(request.get_header("Authorization"), "Bearer secret")
            return _FakeResponse({"data": [{"embedding": [0.1, 0.2, 0.3]}]})

        provider = OpenAICompatibleEmbeddingProvider(
            endpoint="https://embedding.example/v1/embeddings",
            api_key="secret",
            model_id="approved-model",
            dimensions=3,
            timeout_seconds=3,
            max_retries=0,
            opener=opener,
        )
        vector = provider.embed("VPN Zertifikat")
        self.assertEqual(vector.model_id, "approved-model")
        self.assertEqual(vector.dimensions, 3)
        self.assertEqual(vector.values, (0.1, 0.2, 0.3))

    def test_production_provider_rejects_wrong_dimensions(self) -> None:
        provider = OpenAICompatibleEmbeddingProvider(
            endpoint="https://embedding.example/v1/embeddings",
            api_key="secret",
            model_id="approved-model",
            dimensions=3,
            max_retries=0,
            opener=lambda request, timeout: _FakeResponse(
                {"data": [{"embedding": [0.1, 0.2]}]}
            ),
        )
        with self.assertRaises(RuntimeError):
            provider.embed("VPN Zertifikat")

    def test_environment_factory_requires_complete_production_config(self) -> None:
        with patch.dict(
            os.environ,
            {
                "CCS_EMBEDDING_PROVIDER": "openai-compatible",
                "CCS_EMBEDDING_ENDPOINT": "https://embedding.example/v1/embeddings",
                "CCS_EMBEDDING_API_KEY": "secret",
                "CCS_EMBEDDING_MODEL": "approved-model",
            },
            clear=True,
        ):
            with self.assertRaises(RuntimeError):
                build_embedding_provider_from_env()


if __name__ == "__main__":
    unittest.main()
