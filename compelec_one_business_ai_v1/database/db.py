"""Mandantensichere PostgreSQL-Zugriffsschicht für COMPELEC ONE Business AI.

Wichtig: actor_user_id muss aus einer serverseitig geprüften Anmeldung stammen,
niemals ungeprüft aus einem Formular oder URL-Parameter.
"""
from __future__ import annotations

import os
from contextlib import contextmanager
from typing import Any, Iterator

import psycopg
from psycopg.rows import dict_row


class DatabaseConfigurationError(RuntimeError):
    """Die Datenbankverbindung ist nicht vollständig konfiguriert."""


class AuthorizationError(PermissionError):
    """Benutzer ist nicht aktiv oder gehört nicht zum angegebenen Mandanten."""


def _positive_id(value: int, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ValueError(f"{field} muss eine positive Ganzzahl sein.")
    return value


@contextmanager
def tenant_connection(
    tenant_id: int, actor_user_id: int, *, dsn: str | None = None
) -> Iterator[psycopg.Connection[Any]]:
    """Öffnet eine Transaktion mit geprüftem Benutzer und lokalem RLS-Kontext.

    SET LOCAL / set_config(..., true) gilt nur innerhalb der Transaktion und
    verhindert, dass ein Mandantenkontext über Connection-Pooling weiterlebt.
    """
    tenant_id = _positive_id(tenant_id, "tenant_id")
    actor_user_id = _positive_id(actor_user_id, "actor_user_id")
    connection_string = dsn or os.environ.get("COMPELEC_DATABASE_URL")
    if not connection_string:
        raise DatabaseConfigurationError(
            "COMPELEC_DATABASE_URL ist nicht gesetzt; Datenbankzugriff verweigert."
        )

    with psycopg.connect(connection_string, row_factory=dict_row) as conn:
        with conn.transaction():
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT set_config('app.tenant_id', %s, true)",
                    (str(tenant_id),),
                )
                cur.execute(
                    """
                    SELECT id
                    FROM app_users
                    WHERE id = %s AND tenant_id = %s AND active = TRUE
                    """,
                    (actor_user_id, tenant_id),
                )
                if cur.fetchone() is None:
                    raise AuthorizationError(
                        "Benutzer ist nicht aktiv oder nicht diesem Mandanten zugeordnet."
                    )
            yield conn


def _insert_interaction(
    conn: psycopg.Connection[Any],
    *,
    tenant_id: int,
    customer_id: int,
    actor_user_id: int,
    channel: str,
    direction: str,
    subject: str,
    body: str | None,
) -> int:
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO customer_interactions
                (tenant_id, customer_id, channel, direction, subject, body, created_by)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            RETURNING id
            """,
            (tenant_id, customer_id, channel, direction, subject, body, actor_user_id),
        )
        row = cur.fetchone()
        return int(row["id"])


def list_customers(tenant_id: int, actor_user_id: int) -> list[dict[str, Any]]:
    with tenant_connection(tenant_id, actor_user_id) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, customer_no, company_name, contact_name, email, phone
                FROM customers
                ORDER BY company_name
                """
            )
            return list(cur.fetchall())


def create_customer(
    tenant_id: int,
    actor_user_id: int,
    *,
    customer_no: str,
    company_name: str,
    contact_name: str | None = None,
    email: str | None = None,
    phone: str | None = None,
) -> int:
    if not customer_no.strip() or not company_name.strip():
        raise ValueError("Kundennummer und Firmenname sind Pflichtfelder.")
    with tenant_connection(tenant_id, actor_user_id) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO customers
                    (tenant_id, customer_no, company_name, contact_name, email, phone)
                VALUES (%s, %s, %s, %s, %s, %s)
                RETURNING id
                """,
                (tenant_id, customer_no.strip(), company_name.strip(),
                 contact_name, email, phone),
            )
            return int(cur.fetchone()["id"])


def create_support_ticket(
    tenant_id: int,
    actor_user_id: int,
    *,
    customer_id: int,
    ticket_no: str,
    title: str,
    description: str,
    priority: str = "normal",
) -> int:
    customer_id = _positive_id(customer_id, "customer_id")
    if not ticket_no.strip() or not title.strip() or not description.strip():
        raise ValueError("Ticketnummer, Titel und Beschreibung sind Pflichtfelder.")
    if priority not in {"low", "normal", "high", "critical"}:
        raise ValueError("Ungültige Ticketpriorität.")
    with tenant_connection(tenant_id, actor_user_id) as conn:
        interaction_id = _insert_interaction(
            conn, tenant_id=tenant_id, customer_id=customer_id,
            actor_user_id=actor_user_id, channel="support", direction="inbound",
            subject=title.strip(), body=description.strip(),
        )
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO support_tickets
                    (tenant_id, customer_id, interaction_id, ticket_no, title,
                     description, priority, created_by)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
                """,
                (tenant_id, customer_id, interaction_id, ticket_no.strip(),
                 title.strip(), description.strip(), priority, actor_user_id),
            )
            return int(cur.fetchone()["id"])


def create_phone_note(
    tenant_id: int,
    actor_user_id: int,
    *,
    customer_id: int,
    subject: str,
    note: str,
    phone_number: str | None = None,
    callback_required: bool = False,
) -> int:
    customer_id = _positive_id(customer_id, "customer_id")
    if not subject.strip() or not note.strip():
        raise ValueError("Betreff und Gesprächsnotiz sind Pflichtfelder.")
    with tenant_connection(tenant_id, actor_user_id) as conn:
        interaction_id = _insert_interaction(
            conn, tenant_id=tenant_id, customer_id=customer_id,
            actor_user_id=actor_user_id, channel="phone", direction="inbound",
            subject=subject.strip(), body=note.strip(),
        )
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO phone_call_details
                    (tenant_id, interaction_id, phone_number, callback_required)
                VALUES (%s, %s, %s, %s)
                """,
                (tenant_id, interaction_id, phone_number, callback_required),
            )
        return interaction_id


def create_email_draft(
    tenant_id: int,
    actor_user_id: int,
    *,
    customer_id: int,
    recipient: str,
    subject: str,
    body: str,
) -> int:
    customer_id = _positive_id(customer_id, "customer_id")
    if not recipient.strip() or not subject.strip() or not body.strip():
        raise ValueError("Empfänger, Betreff und E-Mail-Text sind Pflichtfelder.")
    with tenant_connection(tenant_id, actor_user_id) as conn:
        interaction_id = _insert_interaction(
            conn, tenant_id=tenant_id, customer_id=customer_id,
            actor_user_id=actor_user_id, channel="email", direction="outbound",
            subject=subject.strip(), body=body.strip(),
        )
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO email_drafts
                    (tenant_id, interaction_id, recipient, subject, body,
                     approval_status, created_by)
                VALUES (%s, %s, %s, %s, %s, 'draft', %s)
                RETURNING id
                """,
                (tenant_id, interaction_id, recipient.strip(), subject.strip(),
                 body.strip(), actor_user_id),
            )
            return int(cur.fetchone()["id"])
