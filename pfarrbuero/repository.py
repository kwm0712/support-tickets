"""Tenant-aware PostgreSQL repository for the Pfarrbüro-KI V2.0 development line.

The adapter deliberately requires an explicit tenant, organization unit and actor.
It does not implement authentication; production use must be behind the approved
identity provider and server-side authorization layer.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Iterable

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
        missing = [
            key for key in (
                "PFARRBUERO_DATABASE_URL",
                "PFARRBUERO_TENANT_ID",
                "PFARRBUERO_ORG_UNIT_ID",
                "PFARRBUERO_USER_ID",
            ) if not os.getenv(key)
        ]
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
    """Small transaction-scoped repository; tenant context is always SET LOCAL."""

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

    def list_cases(self) -> list[tuple[str, str, str]]:
        with self._connect() as conn:
            self._set_tenant(conn)
            rows = conn.execute(
                """
                SELECT case_type, subject, status
                FROM parish_cases
                WHERE tenant_id = %s AND org_unit_id = %s
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
