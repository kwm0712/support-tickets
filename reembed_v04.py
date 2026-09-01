from __future__ import annotations

import argparse
import os

from architecture import TenantContext
from embedding import EmbeddingProvider, build_embedding_provider_from_env
from postgres_repository import PostgresRepository


def reembed_tenant(*, database_url: str, tenant_id: str, provider: EmbeddingProvider, dry_run: bool) -> dict[str, int | str]:
    repository = PostgresRepository(database_url, TenantContext(tenant_id))
    articles = repository.list_knowledge_articles(include_unapproved=True)
    documents = repository.list_documents()

    changed_articles = 0
    changed_chunks = 0

    with repository._connect() as connection:
        for article in articles:
            if article.get("embedding_model") == provider.model_id and int(article.get("embedding_dimensions") or 0) == provider.dimensions:
                continue
            changed_articles += 1
            if dry_run:
                continue
            vector = provider.embed(f"{article['title']}\n{article['content']}")
            connection.execute(
                """
                UPDATE knowledge_articles
                SET embedding = %s::vector,
                    embedding_model = %s,
                    embedding_dimensions = %s,
                    embedded_at = now(),
                    updated_at = now()
                WHERE tenant_key = %s AND id = %s
                """,
                (repository._vector_literal(vector), vector.model_id, vector.dimensions, tenant_id, article["id"]),
            )

        rows = connection.execute(
            """
            SELECT id, content, embedding_model, embedding_dimensions
            FROM document_chunks
            WHERE tenant_key = %s
            ORDER BY id
            """,
            (tenant_id,),
        ).fetchall()
        for row in rows:
            if row["embedding_model"] == provider.model_id and int(row["embedding_dimensions"] or 0) == provider.dimensions:
                continue
            changed_chunks += 1
            if dry_run:
                continue
            vector = provider.embed(row["content"])
            connection.execute(
                """
                UPDATE document_chunks
                SET embedding = %s::vector,
                    embedding_model = %s,
                    embedding_dimensions = %s,
                    embedded_at = now()
                WHERE tenant_key = %s AND id = %s
                """,
                (repository._vector_literal(vector), vector.model_id, vector.dimensions, tenant_id, row["id"]),
            )

    return {
        "tenant": tenant_id,
        "model": provider.model_id,
        "dimensions": provider.dimensions,
        "articles": changed_articles,
        "chunks": changed_chunks,
        "mode": "dry-run" if dry_run else "apply",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="COMPELEC ONE Business V0.4 Re-Embedding")
    parser.add_argument("--tenant", default=os.getenv("CCS_TENANT_ID", "compelec"))
    parser.add_argument("--apply", action="store_true", help="Änderungen wirklich schreiben; Standard ist Dry Run.")
    args = parser.parse_args()

    database_url = os.getenv("CCS_DATABASE_URL", "").strip()
    if not database_url:
        raise RuntimeError("CCS_DATABASE_URL ist verpflichtend.")
    provider = build_embedding_provider_from_env()
    result = reembed_tenant(
        database_url=database_url,
        tenant_id=args.tenant,
        provider=provider,
        dry_run=not args.apply,
    )
    print(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
