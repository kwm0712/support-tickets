"""Tenant-aware PostgreSQL repository for the Pfarrbüro-KI V2.0 development line.

Authentication is not implemented here. The adapter enforces tenant-scoped
membership and role permissions after an upstream identity layer supplies
the authenticated user ID.
"""
from __future__ import annotations

import os
from dataclasses import dataclass

import psycopg
from psycopg.rows import tuple_row


@dataclass(frozen=True)
class StoreConfig:
    dsn: str
    tenant_id: str
    org_unit_id: str
    actor_user_id: str

    @classmethod
    def from_env(cls) -> "StoreConfig":
        required = (
            "PFARRBUERO_DATABASE_URL",
            "PFARRBUERO_TENANT_ID",
            "PFARRBUERO_ORG_UNIT_ID",
            "PFARRBUERO_USER_ID",
        )
        missing = [key for key in required if not os.getenv(key)]
        if missing:
            raise RuntimeError(
                "PostgreSQL-Modus unvollständig. Es fehlen: " + ", ".join(missing)
            )
        return cls(
            dsn=os.environ["PFARRBUERO_DATABASE_URL"],
            tenant_id=os.environ["PFARRBUERO_TENANT_ID"],
            org_unit_id=os.environ["PFARRBUERO_ORG_UNIT_ID"],
            actor_user_id=os.environ["PFARRBUERO_USER_ID"],
        )


class PostgresCaseStore:
    """Small transaction-scoped repository with RLS and role checks."""

    def __init__(self, config: StoreConfig):
        self.config = config

    def _connect(self):
        return psycopg.connect(self.config.dsn, row_factory=tuple_row)

    def _set_tenant(self, conn) -> None:
        # set_config(..., true) is transaction-local and cannot leak through a pool.
        conn.execute(
            "SELECT set_config('app.tenant_id', %s, true)",
            (self.config.tenant_id,),
        )

    def _has_permission(self, conn, permission_key: str) -> bool:
        row = conn.execute(
            """
            WITH RECURSIVE org_scope(id, parent_id) AS (
                SELECT id, parent_id
                FROM parish_org_units
                WHERE id = %s AND tenant_id = %s
                UNION ALL
                SELECT parent.id, parent.parent_id
                FROM parish_org_units AS parent
                JOIN org_scope AS child ON child.parent_id = parent.id
                WHERE parent.tenant_id = %s
            )
            SELECT EXISTS (
                SELECT 1
                FROM parish_memberships AS m
                JOIN parish_roles AS r ON r.id = m.role_id
                JOIN parish_role_permissions AS rp ON rp.role_id = r.id
                JOIN parish_permissions AS p ON p.id = rp.permission_id
                JOIN org_scope AS scope ON scope.id = m.org_unit_id
                WHERE m.tenant_id = %s
                  AND m.user_id = %s
                  AND m.status = 'active'
                  AND p.permission_key = %s
            )
            """,
            (
                self.config.org_unit_id,
                self.config.tenant_id,
                self.config.tenant_id,
                self.config.tenant_id,
                self.config.actor_user_id,
                permission_key,
            ),
        ).fetchone()
        return bool(row and row[0])

    def health_check(self) -> None:
        with self._connect() as conn:
            self._set_tenant(conn)
            tenant = conn.execute(
                "SELECT id FROM parish_tenants WHERE id = %s",
                (self.config.tenant_id,),
            ).fetchone()
            org = conn.execute(
                "SELECT id FROM parish_org_units WHERE id = %s AND tenant_id = %s",
                (self.config.org_unit_id, self.config.tenant_id),
            ).fetchone()
            actor = conn.execute(
                "SELECT id FROM parish_users WHERE id = %s AND tenant_id = %s AND status = 'active'",
                (self.config.actor_user_id, self.config.tenant_id),
            ).fetchone()
            if not tenant or not org or not actor:
                raise RuntimeError(
                    "Mandantenkonfiguration unvollständig oder durch RLS nicht sichtbar "
                    "(Mandant, Organisationseinheit oder aktiver Benutzer fehlt)."
                )
            if not self._has_permission(conn, "case.read"):
                raise PermissionError(
                    "Der Benutzer besitzt im ausgewählten Organisationsbereich keine Berechtigung case.read."
                )

    def list_cases(self) -> list[tuple[str, str, str]]:
        with self._connect() as conn:
            self._set_tenant(conn)
            if not self._has_permission(conn, "case.read"):
                raise PermissionError("Fehlende Berechtigung: case.read")
            can_read_secret = self._has_permission(conn, "pastoral_secret.read")
            confidentiality_filter = "" if can_read_secret else "AND confidentiality <> 'pastoral_secret'"
            rows = conn.execute(
                f"""
                SELECT case_type, subject, status
                FROM parish_cases
                WHERE tenant_id = %s AND org_unit_id = %s
                  {confidentiality_filter}
                ORDER BY updated_at DESC, case_number DESC
                """,
                (self.config.tenant_id, self.config.org_unit_id),
            ).fetchall()
            return [(str(row[0]), str(row[1]), str(row[2])) for row in rows]

    def create_case(self, case_type: str, subject: str) -> None:
        case_type = case_type.strip()
        subject = subject.strip()
        if not case_type or not subject:
            raise ValueError("Vorgangsart und Betreff dürfen nicht leer sein.")
        with self._connect() as conn:
            self._set_tenant(conn)
            if not self._has_permission(conn, "case.create"):
                raise PermissionError("Fehlende Berechtigung: case.create")
            row = conn.execute(
                """
                INSERT INTO parish_cases
                    (tenant_id, org_unit_id, case_type, subject, created_by)
                VALUES (%s, %s, %s, %s, %s)
                RETURNING id, case_number
                """,
                (
                    self.config.tenant_id,
                    self.config.org_unit_id,
                    case_type,
                    subject,
                    self.config.actor_user_id,
                ),
            ).fetchone()
            conn.execute(
                """
                INSERT INTO parish_audit_events
                    (tenant_id, actor_user_id, org_unit_id, event_type,
                     entity_type, entity_id, outcome, metadata)
                VALUES (%s, %s, %s, 'case.created', 'parish_case', %s,
                        'success', jsonb_build_object('case_number', %s))
                """,
                (
                    self.config.tenant_id,
                    self.config.actor_user_id,
                    self.config.org_unit_id,
                    str(row[0]),
                    row[1],
                ),
            )
