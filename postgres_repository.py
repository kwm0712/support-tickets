from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from architecture import PRIVACY_LEVELS, TenantContext
from embedding import EmbeddingVector


class PostgresRepository:
    """Tenant-scoped PostgreSQL repository for the V0.3 platform core.

    The repository never accepts a tenant identifier per domain method. The tenant is
    fixed when the repository is created, reducing the risk of accidental cross-tenant
    queries. Authorization remains a service-layer responsibility; tenant isolation is
    enforced here as a second boundary.
    """

    def __init__(self, database_url: str, tenant: TenantContext) -> None:
        if not database_url.strip():
            raise ValueError("database_url darf nicht leer sein.")
        self.database_url = database_url
        self.tenant = tenant

    def _connect(self):
        try:
            import psycopg
            from psycopg.rows import dict_row
        except ImportError as exc:
            raise RuntimeError(
                "PostgreSQL-Unterstützung benötigt das Paket 'psycopg'."
            ) from exc
        return psycopg.connect(self.database_url, row_factory=dict_row)

    @staticmethod
    def _vector_literal(embedding: EmbeddingVector) -> str:
        if len(embedding.values) != embedding.dimensions:
            raise ValueError("Embedding-Vektor hat eine ungültige Länge.")
        return "[" + ",".join(f"{value:.12g}" for value in embedding.values) + "]"

    @staticmethod
    def _allowed_privacy_levels(requested: str) -> tuple[str, ...]:
        if requested not in PRIVACY_LEVELS:
            raise ValueError(f"Ungültige Datenschutzstufe: {requested}")
        rank = PRIVACY_LEVELS.index(requested)
        return PRIVACY_LEVELS[: rank + 1]

    def healthcheck(self) -> bool:
        with self._connect() as connection:
            row = connection.execute("SELECT 1 AS ok").fetchone()
            return bool(row and row["ok"] == 1)

    def ensure_tenant(self, display_name: str) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO tenants (tenant_key, display_name)
                VALUES (%s, %s)
                ON CONFLICT (tenant_key)
                DO UPDATE SET display_name = EXCLUDED.display_name
                """,
                (self.tenant.tenant_id, display_name.strip() or self.tenant.tenant_id),
            )

    # ------------------------------------------------------------------ Tickets
    def create_ticket(
        self,
        *,
        subject: str,
        description: str,
        customer: str,
        priority: str,
        actor: str,
    ) -> str:
        if not subject.strip() or not description.strip() or not customer.strip():
            raise ValueError("Betreff, Beschreibung und Kunde sind Pflichtfelder.")
        if priority not in {"Hoch", "Mittel", "Niedrig"}:
            raise ValueError(f"Ungültige Priorität: {priority}")

        with self._connect() as connection:
            sequence_row = connection.execute(
                "SELECT nextval(pg_get_serial_sequence('tickets', 'id')) AS id"
            ).fetchone()
            ticket_id = int(sequence_row["id"])
            year = datetime.now(UTC).year
            ticket_no = f"CCS-{year}-{ticket_id:05d}"
            connection.execute(
                """
                INSERT INTO tickets (
                    id, tenant_key, ticket_no, subject, description, customer,
                    status, priority, created_by
                ) VALUES (%s, %s, %s, %s, %s, %s, 'Offen', %s, %s)
                """,
                (
                    ticket_id,
                    self.tenant.tenant_id,
                    ticket_no,
                    subject.strip(),
                    description.strip(),
                    customer.strip(),
                    priority,
                    actor,
                ),
            )
            self._record_audit_in_transaction(
                connection,
                actor=actor,
                action="CREATE",
                entity_type="ticket",
                entity_id=ticket_no,
                details=f"Priorität: {priority}",
            )
            return ticket_no

    def list_tickets(self) -> list[dict[str, Any]]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT ticket_no, subject, description, customer, status, priority,
                       assignee, created_by, created_at, updated_at
                FROM tickets
                WHERE tenant_key = %s
                ORDER BY
                    CASE priority WHEN 'Hoch' THEN 1 WHEN 'Mittel' THEN 2 ELSE 3 END,
                    updated_at DESC
                """,
                (self.tenant.tenant_id,),
            ).fetchall()
            return [dict(row) for row in rows]

    def update_ticket(
        self,
        *,
        ticket_no: str,
        status: str,
        priority: str,
        assignee: str,
        actor: str,
    ) -> None:
        if status not in {"Offen", "In Bearbeitung", "Gelöst"}:
            raise ValueError(f"Ungültiger Status: {status}")
        if priority not in {"Hoch", "Mittel", "Niedrig"}:
            raise ValueError(f"Ungültige Priorität: {priority}")
        with self._connect() as connection:
            updated = connection.execute(
                """
                UPDATE tickets
                SET status = %s, priority = %s, assignee = %s, updated_at = now()
                WHERE tenant_key = %s AND ticket_no = %s
                """,
                (
                    status,
                    priority,
                    assignee.strip() or None,
                    self.tenant.tenant_id,
                    ticket_no,
                ),
            ).rowcount
            if updated == 0:
                raise ValueError(f"Ticket {ticket_no} wurde nicht gefunden.")
            self._record_audit_in_transaction(
                connection,
                actor=actor,
                action="UPDATE",
                entity_type="ticket",
                entity_id=ticket_no,
                details=(
                    f"Status: {status}; Priorität: {priority}; "
                    f"Bearbeiter: {assignee.strip() or '-'}"
                ),
            )

    def get_metrics(self) -> dict[str, int]:
        with self._connect() as connection:
            ticket_metrics = connection.execute(
                """
                SELECT COUNT(*) AS total,
                       COUNT(*) FILTER (WHERE status = 'Offen') AS open_count,
                       COUNT(*) FILTER (WHERE status = 'In Bearbeitung') AS active_count,
                       COUNT(*) FILTER (
                           WHERE priority = 'Hoch' AND status <> 'Gelöst'
                       ) AS critical_count
                FROM tickets
                WHERE tenant_key = %s
                """,
                (self.tenant.tenant_id,),
            ).fetchone()
            knowledge_count = connection.execute(
                "SELECT COUNT(*) AS count FROM knowledge_articles WHERE tenant_key = %s",
                (self.tenant.tenant_id,),
            ).fetchone()["count"]
            document_count = connection.execute(
                "SELECT COUNT(*) AS count FROM documents WHERE tenant_key = %s",
                (self.tenant.tenant_id,),
            ).fetchone()["count"]
        return {
            "total": int(ticket_metrics["total"] or 0),
            "open": int(ticket_metrics["open_count"] or 0),
            "active": int(ticket_metrics["active_count"] or 0),
            "critical": int(ticket_metrics["critical_count"] or 0),
            "knowledge": int(knowledge_count or 0),
            "documents": int(document_count or 0),
        }

    # -------------------------------------------------------------- Knowledge
    def add_knowledge_article(
        self,
        *,
        title: str,
        category: str,
        content: str,
        source: str,
        privacy_level: str,
        actor: str,
        embedding: EmbeddingVector,
    ) -> int:
        if not title.strip() or not content.strip():
            raise ValueError("Titel und Inhalt sind Pflichtfelder.")
        if privacy_level not in PRIVACY_LEVELS:
            raise ValueError(f"Ungültige Datenschutzstufe: {privacy_level}")
        vector_literal = self._vector_literal(embedding)
        with self._connect() as connection:
            row = connection.execute(
                """
                INSERT INTO knowledge_articles (
                    tenant_key, title, category, content, source, created_by,
                    approval_status, privacy_level, embedding, embedding_model,
                    embedding_dimensions, embedded_at
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, 'draft', %s,
                    %s::vector, %s, %s, now()
                )
                RETURNING id
                """,
                (
                    self.tenant.tenant_id,
                    title.strip(),
                    category.strip() or "Allgemein",
                    content.strip(),
                    source.strip() or None,
                    actor,
                    privacy_level,
                    vector_literal,
                    embedding.model_id,
                    embedding.dimensions,
                ),
            ).fetchone()
            article_id = int(row["id"])
            self._record_audit_in_transaction(
                connection,
                actor=actor,
                action="CREATE",
                entity_type="knowledge_article",
                entity_id=str(article_id),
                details=f"Status: draft; Datenschutz: {privacy_level}; Titel: {title.strip()}",
            )
            return article_id

    def list_knowledge_articles(self, *, include_unapproved: bool) -> list[dict[str, Any]]:
        status_filter = "" if include_unapproved else "AND approval_status = 'approved'"
        with self._connect() as connection:
            rows = connection.execute(
                f"""
                SELECT id, title, category, content, source, created_by, created_at,
                       updated_at, approval_status, privacy_level, embedding_model,
                       embedding_dimensions, embedded_at
                FROM knowledge_articles
                WHERE tenant_key = %s
                {status_filter}
                ORDER BY updated_at DESC, id DESC
                """,
                (self.tenant.tenant_id,),
            ).fetchall()
            return [dict(row) for row in rows]

    def set_article_status(self, article_id: int, status: str, actor: str) -> None:
        if status not in {"draft", "approved", "rejected"}:
            raise ValueError(f"Ungültiger Freigabestatus: {status}")
        with self._connect() as connection:
            updated = connection.execute(
                """
                UPDATE knowledge_articles
                SET approval_status = %s, updated_at = now()
                WHERE tenant_key = %s AND id = %s
                """,
                (status, self.tenant.tenant_id, article_id),
            ).rowcount
            if updated == 0:
                raise ValueError("Wissensartikel wurde nicht gefunden.")
            self._record_audit_in_transaction(
                connection,
                actor=actor,
                action="REVIEW",
                entity_type="knowledge_article",
                entity_id=str(article_id),
                details=f"Status: {status}",
            )

    # --------------------------------------------------------------- Documents
    def add_document(
        self,
        *,
        filename: str,
        category: str,
        source: str,
        file_type: str,
        sha256: str,
        privacy_level: str,
        actor: str,
        chunks: list[tuple[str, EmbeddingVector]],
    ) -> int:
        if not chunks:
            raise ValueError("Dokument enthält keine verwertbaren Segmente.")
        if privacy_level not in PRIVACY_LEVELS:
            raise ValueError(f"Ungültige Datenschutzstufe: {privacy_level}")

        with self._connect() as connection:
            duplicate = connection.execute(
                "SELECT id FROM documents WHERE tenant_key = %s AND sha256 = %s",
                (self.tenant.tenant_id, sha256),
            ).fetchone()
            if duplicate:
                raise ValueError(
                    f"Dieses Dokument ist bereits als ID {duplicate['id']} vorhanden."
                )

            row = connection.execute(
                """
                INSERT INTO documents (
                    tenant_key, filename, category, source, file_type, sha256,
                    approval_status, privacy_level, imported_by
                ) VALUES (%s, %s, %s, %s, %s, %s, 'draft', %s, %s)
                RETURNING id
                """,
                (
                    self.tenant.tenant_id,
                    filename.strip(),
                    category.strip() or "Support",
                    source.strip() or None,
                    file_type,
                    sha256,
                    privacy_level,
                    actor,
                ),
            ).fetchone()
            document_id = int(row["id"])

            for chunk_no, (content, embedding) in enumerate(chunks, start=1):
                connection.execute(
                    """
                    INSERT INTO document_chunks (
                        tenant_key, document_id, chunk_no, content, embedding,
                        embedding_model, embedding_dimensions, embedded_at
                    ) VALUES (%s, %s, %s, %s, %s::vector, %s, %s, now())
                    """,
                    (
                        self.tenant.tenant_id,
                        document_id,
                        chunk_no,
                        content,
                        self._vector_literal(embedding),
                        embedding.model_id,
                        embedding.dimensions,
                    ),
                )

            self._record_audit_in_transaction(
                connection,
                actor=actor,
                action="IMPORT",
                entity_type="document",
                entity_id=str(document_id),
                details=(
                    f"{filename}; Chunks: {len(chunks)}; Status: draft; "
                    f"Datenschutz: {privacy_level}"
                ),
            )
            return document_id

    def list_documents(self) -> list[dict[str, Any]]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT d.id, d.filename, d.category, d.source, d.file_type,
                       d.approval_status, d.privacy_level, d.imported_by,
                       d.imported_at, d.reviewed_by, d.reviewed_at,
                       COUNT(c.id) AS chunk_count
                FROM documents d
                LEFT JOIN document_chunks c
                  ON c.document_id = d.id AND c.tenant_key = d.tenant_key
                WHERE d.tenant_key = %s
                GROUP BY d.id
                ORDER BY d.id DESC
                """,
                (self.tenant.tenant_id,),
            ).fetchall()
            return [dict(row) for row in rows]

    def set_document_status(self, document_id: int, status: str, actor: str) -> None:
        if status not in {"draft", "approved", "rejected"}:
            raise ValueError(f"Ungültiger Freigabestatus: {status}")
        with self._connect() as connection:
            updated = connection.execute(
                """
                UPDATE documents
                SET approval_status = %s, reviewed_by = %s, reviewed_at = now()
                WHERE tenant_key = %s AND id = %s
                """,
                (status, actor, self.tenant.tenant_id, document_id),
            ).rowcount
            if updated == 0:
                raise ValueError("Dokument wurde nicht gefunden.")
            self._record_audit_in_transaction(
                connection,
                actor=actor,
                action="REVIEW",
                entity_type="document",
                entity_id=str(document_id),
                details=f"Status: {status}",
            )

    # --------------------------------------------------------- Hybrid retrieval
    def retrieve_hybrid_evidence(
        self,
        *,
        question: str,
        privacy_level: str,
        query_embedding: EmbeddingVector,
        limit: int = 5,
    ) -> list[dict[str, Any]]:
        allowed = list(self._allowed_privacy_levels(privacy_level))
        vector_literal = self._vector_literal(query_embedding)

        with self._connect() as connection:
            article_rows = connection.execute(
                """
                SELECT id AS source_id,
                       'article' AS source_type,
                       title,
                       COALESCE(source, 'Wissensartikel') AS source,
                       content,
                       privacy_level,
                       ts_rank_cd(
                           to_tsvector('simple', coalesce(title, '') || ' ' || coalesce(content, '')),
                           plainto_tsquery('simple', %s)
                       ) AS lexical_score,
                       CASE
                           WHEN embedding IS NOT NULL AND embedding_dimensions = %s
                           THEN GREATEST(0.0, 1.0 - (embedding <=> %s::vector))
                           ELSE 0.0
                       END AS vector_score
                FROM knowledge_articles
                WHERE tenant_key = %s
                  AND approval_status = 'approved'
                  AND privacy_level = ANY(%s)
                """,
                (
                    question,
                    query_embedding.dimensions,
                    vector_literal,
                    self.tenant.tenant_id,
                    allowed,
                ),
            ).fetchall()

            chunk_rows = connection.execute(
                """
                SELECT c.id AS source_id,
                       'document_chunk' AS source_type,
                       d.filename AS title,
                       COALESCE(d.source, d.filename) AS source,
                       c.content,
                       d.privacy_level,
                       ts_rank_cd(
                           to_tsvector('simple', coalesce(d.filename, '') || ' ' || coalesce(c.content, '')),
                           plainto_tsquery('simple', %s)
                       ) AS lexical_score,
                       CASE
                           WHEN c.embedding IS NOT NULL AND c.embedding_dimensions = %s
                           THEN GREATEST(0.0, 1.0 - (c.embedding <=> %s::vector))
                           ELSE 0.0
                       END AS vector_score
                FROM document_chunks c
                JOIN documents d
                  ON d.id = c.document_id
                 AND d.tenant_key = c.tenant_key
                WHERE c.tenant_key = %s
                  AND d.approval_status = 'approved'
                  AND d.privacy_level = ANY(%s)
                """,
                (
                    question,
                    query_embedding.dimensions,
                    vector_literal,
                    self.tenant.tenant_id,
                    allowed,
                ),
            ).fetchall()

        evidence: list[dict[str, Any]] = []
        for row in [*article_rows, *chunk_rows]:
            item = dict(row)
            lexical = max(0.0, float(item.get("lexical_score") or 0.0))
            vector = max(0.0, float(item.get("vector_score") or 0.0))
            lexical_normalized = min(1.0, lexical * 4.0)
            combined = (0.35 * lexical_normalized) + (0.65 * vector)
            item["lexical_score"] = lexical
            item["vector_score"] = vector
            item["combined_score"] = combined
            if lexical > 0.0 or vector > 0.0:
                evidence.append(item)

        return sorted(
            evidence,
            key=lambda item: item["combined_score"],
            reverse=True,
        )[: max(1, limit)]

    # ----------------------------------------------------------- Assistant runs
    def record_assistant_run(
        self,
        *,
        actor: str,
        provider: str,
        privacy_level: str,
        question: str,
        answer: str,
        evidence: list[dict[str, Any]],
        correlation_id: str | None,
    ) -> int:
        with self._connect() as connection:
            row = connection.execute(
                """
                INSERT INTO assistant_runs (
                    tenant_key, actor, provider, privacy_level, question, answer,
                    correlation_id
                ) VALUES (%s, %s, %s, %s, %s, %s, %s)
                RETURNING id
                """,
                (
                    self.tenant.tenant_id,
                    actor,
                    provider,
                    privacy_level,
                    question,
                    answer,
                    correlation_id,
                ),
            ).fetchone()
            run_id = int(row["id"])
            for rank, item in enumerate(evidence, start=1):
                connection.execute(
                    """
                    INSERT INTO assistant_evidence (
                        tenant_key, assistant_run_id, source_type, source_id, rank,
                        lexical_score, vector_score, combined_score
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        self.tenant.tenant_id,
                        run_id,
                        item["source_type"],
                        int(item["source_id"]),
                        rank,
                        float(item.get("lexical_score") or 0.0),
                        float(item.get("vector_score") or 0.0),
                        float(item.get("combined_score") or 0.0),
                    ),
                )
            self._record_audit_in_transaction(
                connection,
                actor=actor,
                action="GENERATE",
                entity_type="assistant_run",
                entity_id=str(run_id),
                correlation_id=correlation_id,
                details=(
                    f"Provider: {provider}; Datenschutz: {privacy_level}; "
                    f"Quellen: {len(evidence)}"
                ),
            )
            return run_id

    def list_assistant_runs(self, limit: int = 100) -> list[dict[str, Any]]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT id, actor, provider, privacy_level, question, answer,
                       correlation_id, created_at
                FROM assistant_runs
                WHERE tenant_key = %s
                ORDER BY id DESC
                LIMIT %s
                """,
                (self.tenant.tenant_id, max(1, limit)),
            ).fetchall()
            return [dict(row) for row in rows]

    # ------------------------------------------------------------------- Audit
    def record_audit(
        self,
        *,
        actor: str,
        action: str,
        entity_type: str,
        entity_id: str | None = None,
        details: str | None = None,
        correlation_id: str | None = None,
    ) -> None:
        with self._connect() as connection:
            self._record_audit_in_transaction(
                connection,
                actor=actor,
                action=action,
                entity_type=entity_type,
                entity_id=entity_id,
                details=details,
                correlation_id=correlation_id,
            )

    def list_audit_entries(self, limit: int = 200) -> list[dict[str, Any]]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT actor, action, entity_type, entity_id, correlation_id,
                       details, metadata, created_at
                FROM audit_log
                WHERE tenant_key = %s
                ORDER BY id DESC
                LIMIT %s
                """,
                (self.tenant.tenant_id, max(1, limit)),
            ).fetchall()
            return [dict(row) for row in rows]

    def _record_audit_in_transaction(
        self,
        connection,
        *,
        actor: str,
        action: str,
        entity_type: str,
        entity_id: str | None = None,
        details: str | None = None,
        correlation_id: str | None = None,
    ) -> None:
        connection.execute(
            """
            INSERT INTO audit_log (
                tenant_key, actor, action, entity_type, entity_id,
                correlation_id, details
            ) VALUES (%s, %s, %s, %s, %s, %s, %s)
            """,
            (
                self.tenant.tenant_id,
                actor,
                action,
                entity_type,
                entity_id,
                correlation_id,
                details,
            ),
        )
