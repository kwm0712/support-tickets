from __future__ import annotations

import argparse
import sqlite3
from dataclasses import dataclass
from pathlib import Path

from architecture import TenantContext
from embedding import DeterministicLocalEmbeddingProvider
from postgres_migrations import apply_postgres_migrations
from postgres_repository import PostgresRepository


@dataclass(frozen=True)
class MigrationSummary:
    users: int = 0
    tickets: int = 0
    articles: int = 0
    documents: int = 0
    chunks: int = 0
    assistant_runs: int = 0
    assistant_evidence: int = 0
    audit_entries: int = 0


def _table_exists(db: sqlite3.Connection, table: str) -> bool:
    return db.execute(
        "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?",
        (table,),
    ).fetchone() is not None


def _columns(db: sqlite3.Connection, table: str) -> set[str]:
    if not _table_exists(db, table):
        return set()
    return {row[1] for row in db.execute(f"PRAGMA table_info({table})").fetchall()}


def _row_value(row: sqlite3.Row, columns: set[str], name: str, default=None):
    return row[name] if name in columns else default


def migrate_v02_sqlite_to_v03_postgres(
    *,
    sqlite_path: str | Path,
    database_url: str,
    tenant_key: str,
    tenant_name: str,
    dry_run: bool = False,
) -> MigrationSummary:
    source_path = Path(sqlite_path)
    if not source_path.exists():
        raise FileNotFoundError(f"SQLite-Datei nicht gefunden: {source_path}")
    if not tenant_key.strip():
        raise ValueError("tenant_key darf nicht leer sein.")

    source = sqlite3.connect(source_path)
    source.row_factory = sqlite3.Row
    try:
        counts = {
            table: (
                source.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
                if _table_exists(source, table)
                else 0
            )
            for table in (
                "users",
                "tickets",
                "knowledge_articles",
                "documents",
                "document_chunks",
                "assistant_runs",
                "audit_log",
            )
        }
        if dry_run:
            return MigrationSummary(
                users=counts["users"],
                tickets=counts["tickets"],
                articles=counts["knowledge_articles"],
                documents=counts["documents"],
                chunks=counts["document_chunks"],
                assistant_runs=counts["assistant_runs"],
                audit_entries=counts["audit_log"],
            )

        apply_postgres_migrations(database_url)
        repository = PostgresRepository(database_url, TenantContext(tenant_key))
        repository.ensure_tenant(tenant_name or tenant_key)
        embedder = DeterministicLocalEmbeddingProvider()

        with repository._connect() as target:
            occupied = target.execute(
                """
                SELECT
                    (SELECT COUNT(*) FROM tickets WHERE tenant_key = %s) +
                    (SELECT COUNT(*) FROM knowledge_articles WHERE tenant_key = %s) +
                    (SELECT COUNT(*) FROM documents WHERE tenant_key = %s) +
                    (SELECT COUNT(*) FROM assistant_runs WHERE tenant_key = %s)
                    AS domain_count
                """,
                (tenant_key, tenant_key, tenant_key, tenant_key),
            ).fetchone()["domain_count"]
            if occupied:
                raise RuntimeError(
                    "Zielmandant enthält bereits Fachdaten. Migration wird aus Sicherheitsgründen abgebrochen."
                )

            # Users: hashes and salts are preserved; IDs remain PostgreSQL-owned.
            if _table_exists(source, "users"):
                user_columns = _columns(source, "users")
                for row in source.execute("SELECT * FROM users ORDER BY id"):
                    target.execute(
                        """
                        INSERT INTO users (
                            tenant_key, username, display_name, role, password_salt,
                            password_hash, active, created_at
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (tenant_key, username) DO NOTHING
                        """,
                        (
                            tenant_key,
                            row["username"],
                            row["display_name"],
                            row["role"],
                            row["password_salt"],
                            row["password_hash"],
                            bool(_row_value(row, user_columns, "active", 1)),
                            row["created_at"],
                        ),
                    )

            if _table_exists(source, "tickets"):
                for row in source.execute("SELECT * FROM tickets ORDER BY id"):
                    target.execute(
                        """
                        INSERT INTO tickets (
                            tenant_key, ticket_no, subject, description, customer,
                            status, priority, assignee, created_by, created_at, updated_at
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        """,
                        (
                            tenant_key,
                            row["ticket_no"],
                            row["subject"],
                            row["description"],
                            row["customer"],
                            row["status"],
                            row["priority"],
                            row["assignee"],
                            row["created_by"],
                            row["created_at"],
                            row["updated_at"],
                        ),
                    )

            article_id_map: dict[int, int] = {}
            if _table_exists(source, "knowledge_articles"):
                article_columns = _columns(source, "knowledge_articles")
                for row in source.execute("SELECT * FROM knowledge_articles ORDER BY id"):
                    embedding = embedder.embed(f"{row['title']}\n{row['content']}")
                    inserted = target.execute(
                        """
                        INSERT INTO knowledge_articles (
                            tenant_key, title, category, content, source, created_by,
                            created_at, updated_at, approval_status, privacy_level,
                            embedding, embedding_model, embedding_dimensions, embedded_at
                        ) VALUES (
                            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                            %s::vector, %s, %s, now()
                        )
                        RETURNING id
                        """,
                        (
                            tenant_key,
                            row["title"],
                            row["category"],
                            row["content"],
                            row["source"],
                            row["created_by"],
                            row["created_at"],
                            _row_value(row, article_columns, "updated_at", row["created_at"]),
                            _row_value(row, article_columns, "approval_status", "approved"),
                            _row_value(row, article_columns, "privacy_level", "internal"),
                            repository._vector_literal(embedding),
                            embedding.model_id,
                            embedding.dimensions,
                        ),
                    ).fetchone()
                    article_id_map[int(row["id"])] = int(inserted["id"])

            document_id_map: dict[int, int] = {}
            chunk_id_map: dict[int, int] = {}
            if _table_exists(source, "documents"):
                for row in source.execute("SELECT * FROM documents ORDER BY id"):
                    inserted = target.execute(
                        """
                        INSERT INTO documents (
                            tenant_key, filename, category, source, file_type, sha256,
                            approval_status, privacy_level, imported_by, imported_at,
                            reviewed_by, reviewed_at
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        RETURNING id
                        """,
                        (
                            tenant_key,
                            row["filename"],
                            row["category"],
                            row["source"],
                            row["file_type"],
                            row["sha256"],
                            row["approval_status"],
                            row["privacy_level"],
                            row["imported_by"],
                            row["imported_at"],
                            row["reviewed_by"],
                            row["reviewed_at"],
                        ),
                    ).fetchone()
                    document_id_map[int(row["id"])] = int(inserted["id"])

            if _table_exists(source, "document_chunks"):
                for row in source.execute("SELECT * FROM document_chunks ORDER BY id"):
                    embedding = embedder.embed(row["content"])
                    inserted = target.execute(
                        """
                        INSERT INTO document_chunks (
                            tenant_key, document_id, chunk_no, content, embedding,
                            embedding_model, embedding_dimensions, embedded_at
                        ) VALUES (%s, %s, %s, %s, %s::vector, %s, %s, now())
                        RETURNING id
                        """,
                        (
                            tenant_key,
                            document_id_map[int(row["document_id"])],
                            row["chunk_no"],
                            row["content"],
                            repository._vector_literal(embedding),
                            embedding.model_id,
                            embedding.dimensions,
                        ),
                    ).fetchone()
                    chunk_id_map[int(row["id"])] = int(inserted["id"])

            migrated_evidence = 0
            if _table_exists(source, "assistant_runs"):
                run_columns = _columns(source, "assistant_runs")
                for row in source.execute("SELECT * FROM assistant_runs ORDER BY id"):
                    inserted = target.execute(
                        """
                        INSERT INTO assistant_runs (
                            tenant_key, actor, provider, privacy_level, question,
                            answer, correlation_id, created_at
                        ) VALUES (%s, %s, %s, %s, %s, %s, NULL, %s)
                        RETURNING id
                        """,
                        (
                            tenant_key,
                            row["actor"],
                            row["provider"],
                            row["privacy_level"],
                            row["question"],
                            row["answer"],
                            row["created_at"],
                        ),
                    ).fetchone()
                    new_run_id = int(inserted["id"])
                    refs = _row_value(row, run_columns, "evidence_refs", None) or ""
                    for rank, ref in enumerate((item for item in refs.split(";") if item), start=1):
                        source_type, _, raw_id = ref.partition(":")
                        if not raw_id.isdigit():
                            continue
                        old_id = int(raw_id)
                        new_id = (
                            article_id_map.get(old_id)
                            if source_type == "article"
                            else chunk_id_map.get(old_id)
                            if source_type == "document_chunk"
                            else None
                        )
                        if new_id is None:
                            continue
                        target.execute(
                            """
                            INSERT INTO assistant_evidence (
                                tenant_key, assistant_run_id, source_type, source_id, rank
                            ) VALUES (%s, %s, %s, %s, %s)
                            """,
                            (tenant_key, new_run_id, source_type, new_id, rank),
                        )
                        migrated_evidence += 1

            if _table_exists(source, "audit_log"):
                for row in source.execute("SELECT * FROM audit_log ORDER BY id"):
                    target.execute(
                        """
                        INSERT INTO audit_log (
                            tenant_key, actor, action, entity_type, entity_id,
                            details, created_at
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s)
                        """,
                        (
                            tenant_key,
                            row["actor"],
                            row["action"],
                            row["entity_type"],
                            row["entity_id"],
                            row["details"],
                            row["created_at"],
                        ),
                    )

        return MigrationSummary(
            users=counts["users"],
            tickets=counts["tickets"],
            articles=counts["knowledge_articles"],
            documents=counts["documents"],
            chunks=counts["document_chunks"],
            assistant_runs=counts["assistant_runs"],
            assistant_evidence=migrated_evidence,
            audit_entries=counts["audit_log"],
        )
    finally:
        source.close()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="CCS Agent Support V0.2 SQLite nach V0.3 PostgreSQL migrieren"
    )
    parser.add_argument("sqlite_path")
    parser.add_argument("database_url")
    parser.add_argument("--tenant-key", default="compelec")
    parser.add_argument("--tenant-name", default="Compelec Computersysteme GmbH")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    summary = migrate_v02_sqlite_to_v03_postgres(
        sqlite_path=args.sqlite_path,
        database_url=args.database_url,
        tenant_key=args.tenant_key,
        tenant_name=args.tenant_name,
        dry_run=args.dry_run,
    )
    print(summary)


if __name__ == "__main__":
    main()
