from __future__ import annotations

import hashlib
import uuid
from pathlib import Path
from typing import Any

from architecture import (
    PERMISSION_ASSISTANT_USE,
    PERMISSION_AUDIT_READ,
    PERMISSION_DOCUMENT_IMPORT,
    PERMISSION_DOCUMENT_READ,
    PERMISSION_DOCUMENT_REVIEW,
    PERMISSION_KNOWLEDGE_READ,
    PERMISSION_KNOWLEDGE_REVIEW,
    PERMISSION_KNOWLEDGE_WRITE,
    PERMISSION_TICKET_READ,
    PERMISSION_TICKET_WRITE,
    UserContext,
    has_permission,
    max_privacy_level,
    require_permission,
    require_privacy_access,
    require_same_tenant,
)
from embedding import DeterministicLocalEmbeddingProvider, EmbeddingProvider
from knowledge_ai import (
    AssistantResponse,
    Evidence,
    LocalEvidenceProvider,
    PROVIDER_NAME,
    chunk_text,
    extract_document_text,
)
from postgres_repository import PostgresRepository


class SupportService:
    """Application/service layer for CCS Agent Support V0.3.

    UI clients never receive a repository directly. RBAC, privacy ceilings and tenant
    boundaries are enforced here before tenant-scoped persistence is invoked.
    """

    def __init__(
        self,
        repository: PostgresRepository,
        user: UserContext,
        *,
        embedding_provider: EmbeddingProvider | None = None,
    ) -> None:
        require_same_tenant(user, repository.tenant.tenant_id)
        self.repository = repository
        self.user = user
        self.embedding_provider = embedding_provider or DeterministicLocalEmbeddingProvider()
        self.answer_provider = LocalEvidenceProvider()

    # ------------------------------------------------------------------ Runtime
    def ensure_tenant(self, display_name: str) -> None:
        self.repository.ensure_tenant(display_name)

    @property
    def privacy_ceiling(self) -> str:
        return max_privacy_level(self.user)

    # ------------------------------------------------------------------ Tickets
    def list_tickets(self) -> list[dict[str, Any]]:
        require_permission(self.user, PERMISSION_TICKET_READ)
        return self.repository.list_tickets()

    def create_ticket(
        self,
        *,
        subject: str,
        description: str,
        customer: str,
        priority: str,
    ) -> str:
        require_permission(self.user, PERMISSION_TICKET_WRITE)
        return self.repository.create_ticket(
            subject=subject,
            description=description,
            customer=customer,
            priority=priority,
            actor=self.user.username,
        )

    def update_ticket(
        self,
        *,
        ticket_no: str,
        status: str,
        priority: str,
        assignee: str,
    ) -> None:
        require_permission(self.user, PERMISSION_TICKET_WRITE)
        self.repository.update_ticket(
            ticket_no=ticket_no,
            status=status,
            priority=priority,
            assignee=assignee,
            actor=self.user.username,
        )

    def get_metrics(self) -> dict[str, int]:
        require_permission(self.user, PERMISSION_TICKET_READ)
        return self.repository.get_metrics()

    # -------------------------------------------------------------- Knowledge
    def add_article(
        self,
        *,
        title: str,
        category: str,
        content: str,
        source: str,
        privacy_level: str,
    ) -> int:
        require_permission(self.user, PERMISSION_KNOWLEDGE_WRITE)
        require_privacy_access(self.user, privacy_level)
        embedding = self.embedding_provider.embed(f"{title}\n{content}")
        return self.repository.add_knowledge_article(
            title=title,
            category=category,
            content=content,
            source=source,
            privacy_level=privacy_level,
            actor=self.user.username,
            embedding=embedding,
        )

    def list_articles(self, *, include_unapproved: bool = False) -> list[dict[str, Any]]:
        require_permission(self.user, PERMISSION_KNOWLEDGE_READ)
        can_review = has_permission(self.user, PERMISSION_KNOWLEDGE_REVIEW)
        rows = self.repository.list_knowledge_articles(
            include_unapproved=bool(include_unapproved and can_review)
        )
        allowed_levels = self._allowed_levels_for_user()
        return [row for row in rows if row["privacy_level"] in allowed_levels]

    def review_article(self, article_id: int, status: str) -> None:
        require_permission(self.user, PERMISSION_KNOWLEDGE_REVIEW)
        self.repository.set_article_status(article_id, status, self.user.username)

    # --------------------------------------------------------------- Documents
    def import_document(
        self,
        *,
        filename: str,
        data: bytes,
        category: str,
        source: str,
        privacy_level: str,
    ) -> int:
        require_permission(self.user, PERMISSION_DOCUMENT_IMPORT)
        require_privacy_access(self.user, privacy_level)
        if not filename.strip():
            raise ValueError("Dateiname fehlt.")
        if not data:
            raise ValueError("Die Datei ist leer.")

        file_type = Path(filename).suffix.lower().lstrip(".")
        if file_type not in {"txt", "pdf", "docx"}:
            raise ValueError("Unterstützt werden TXT, PDF und DOCX.")

        text = extract_document_text(filename, data)
        chunks = chunk_text(text)
        if not chunks:
            raise ValueError("Aus dem Dokument konnte kein verwertbarer Text extrahiert werden.")
        embedded_chunks = [
            (chunk, self.embedding_provider.embed(chunk))
            for chunk in chunks
        ]
        return self.repository.add_document(
            filename=filename,
            category=category,
            source=source,
            file_type=file_type,
            sha256=hashlib.sha256(data).hexdigest(),
            privacy_level=privacy_level,
            actor=self.user.username,
            chunks=embedded_chunks,
        )

    def list_documents(self) -> list[dict[str, Any]]:
        require_permission(self.user, PERMISSION_DOCUMENT_READ)
        can_review = has_permission(self.user, PERMISSION_DOCUMENT_REVIEW)
        allowed_levels = self._allowed_levels_for_user()
        rows = self.repository.list_documents()
        return [
            row
            for row in rows
            if row["privacy_level"] in allowed_levels
            and (can_review or row["approval_status"] == "approved")
        ]

    def review_document(self, document_id: int, status: str) -> None:
        require_permission(self.user, PERMISSION_DOCUMENT_REVIEW)
        self.repository.set_document_status(document_id, status, self.user.username)

    # --------------------------------------------------------- Search / Assist
    def search_evidence(
        self,
        question: str,
        *,
        privacy_level: str,
        limit: int = 5,
    ) -> list[dict[str, Any]]:
        require_permission(self.user, PERMISSION_KNOWLEDGE_READ)
        require_privacy_access(self.user, privacy_level)
        if not question.strip():
            return []
        query_embedding = self.embedding_provider.embed(question)
        return self.repository.retrieve_hybrid_evidence(
            question=question.strip(),
            privacy_level=privacy_level,
            query_embedding=query_embedding,
            limit=limit,
        )

    def ask_assistant(
        self,
        *,
        question: str,
        privacy_level: str,
    ) -> AssistantResponse:
        require_permission(self.user, PERMISSION_ASSISTANT_USE)
        require_privacy_access(self.user, privacy_level)
        if not question.strip():
            raise ValueError("Bitte eine Supportfrage eingeben.")

        raw_evidence = self.search_evidence(
            question,
            privacy_level=privacy_level,
            limit=5,
        )
        evidence = [
            Evidence(
                source_type=item["source_type"],
                source_id=int(item["source_id"]),
                title=item["title"],
                source=item["source"],
                content=item["content"],
                score=max(1, int(round(float(item["combined_score"]) * 1000))),
                privacy_level=item["privacy_level"],
            )
            for item in raw_evidence
        ]
        answer = self.answer_provider.generate(question.strip(), evidence)
        correlation_id = str(uuid.uuid4())
        run_id = self.repository.record_assistant_run(
            actor=self.user.username,
            provider=PROVIDER_NAME,
            privacy_level=privacy_level,
            question=question.strip(),
            answer=answer,
            evidence=raw_evidence,
            correlation_id=correlation_id,
        )
        return AssistantResponse(
            provider=PROVIDER_NAME,
            answer=answer,
            evidence=evidence,
            privacy_level=privacy_level,
            run_id=run_id,
        )

    def list_assistant_runs(self, limit: int = 100) -> list[dict[str, Any]]:
        require_permission(self.user, PERMISSION_ASSISTANT_USE)
        return self.repository.list_assistant_runs(limit=limit)

    # ------------------------------------------------------------------- Audit
    def list_audit_entries(self, limit: int = 200) -> list[dict[str, Any]]:
        require_permission(self.user, PERMISSION_AUDIT_READ)
        return self.repository.list_audit_entries(limit=limit)

    def _allowed_levels_for_user(self) -> tuple[str, ...]:
        ceiling = self.privacy_ceiling
        levels = ("public", "internal", "confidential")
        return levels[: levels.index(ceiling) + 1]
