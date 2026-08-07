from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from architecture import TenantContext


class PostgresRepository:
    """Tenant-scoped PostgreSQL repository for the V0.3 platform core.

    The repository never accepts a tenant identifier per method. The tenant is fixed when
    the repository is created, which reduces the risk of accidental cross-tenant queries.
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
