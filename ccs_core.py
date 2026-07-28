from __future__ import annotations

import hashlib
import hmac
import os
import secrets
import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Iterator, Optional

APP_DIR = Path(os.getenv("CCS_DATA_DIR", Path(__file__).parent / "data"))
DB_PATH = APP_DIR / "ccs_support.db"


@dataclass(frozen=True)
class LicenseStatus:
    mode: str
    valid: bool
    message: str
    expires_on: Optional[date]


def _utc_now() -> str:
    return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"


@contextmanager
def db_connection() -> Iterator[sqlite3.Connection]:
    APP_DIR.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    try:
        yield connection
        connection.commit()
    finally:
        connection.close()


def _hash_password(password: str, salt: Optional[str] = None) -> tuple[str, str]:
    salt = salt or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        bytes.fromhex(salt),
        200_000,
    ).hex()
    return salt, digest


def _verify_password(password: str, salt: str, expected_hash: str) -> bool:
    _, actual_hash = _hash_password(password, salt)
    return hmac.compare_digest(actual_hash, expected_hash)


def initialize_database() -> None:
    with db_connection() as db:
        db.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE,
                display_name TEXT NOT NULL,
                role TEXT NOT NULL CHECK(role IN ('admin', 'agent', 'viewer')),
                password_salt TEXT NOT NULL,
                password_hash TEXT NOT NULL,
                active INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS tickets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ticket_no TEXT NOT NULL UNIQUE,
                subject TEXT NOT NULL,
                description TEXT NOT NULL,
                customer TEXT NOT NULL,
                status TEXT NOT NULL CHECK(status IN ('Offen', 'In Bearbeitung', 'Gelöst')),
                priority TEXT NOT NULL CHECK(priority IN ('Hoch', 'Mittel', 'Niedrig')),
                assignee TEXT,
                created_by TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS knowledge_articles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                category TEXT NOT NULL,
                content TEXT NOT NULL,
                source TEXT,
                created_by TEXT NOT NULL,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS audit_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                actor TEXT NOT NULL,
                action TEXT NOT NULL,
                entity_type TEXT NOT NULL,
                entity_id TEXT,
                details TEXT,
                created_at TEXT NOT NULL
            );
            """
        )

        user_count = db.execute("SELECT COUNT(*) AS count FROM users").fetchone()["count"]
        if user_count == 0:
            for username, display_name, role, password in (
                ("admin", "CCS Administrator", "admin", "Compelec-Start!"),
                ("support", "Support Agent", "agent", "Support-Start!"),
                ("demo", "Demo Viewer", "viewer", "Demo-Start!"),
            ):
                salt, password_hash = _hash_password(password)
                db.execute(
                    """
                    INSERT INTO users (
                        username, display_name, role, password_salt, password_hash, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (username, display_name, role, salt, password_hash, _utc_now()),
                )

        article_count = db.execute(
            "SELECT COUNT(*) AS count FROM knowledge_articles"
        ).fetchone()["count"]
        if article_count == 0:
            seed_articles = (
                (
                    "Erstprüfung bei Anmeldeproblemen",
                    "Zugriff",
                    "Benutzername prüfen, Kontosperre ausschließen, Kennwort zurücksetzen "
                    "und anschließend die Anmeldung protokolliert testen.",
                    "CCS MVP Startwissen",
                ),
                (
                    "Vorgehen bei Datenbank-Verbindungsfehlern",
                    "Datenbank",
                    "Netzwerkerreichbarkeit, Dienststatus, Zugangsdaten und verfügbare "
                    "Verbindungen prüfen. Keine produktiven Zugangsdaten im Ticket speichern.",
                    "CCS MVP Startwissen",
                ),
                (
                    "Priorisierung kritischer Supportfälle",
                    "Service",
                    "Priorität Hoch gilt bei Produktionsstillstand, Sicherheitsvorfällen oder "
                    "massivem Ausfall. Verantwortliche Person und nächste Aktion müssen benannt sein.",
                    "CCS MVP Startwissen",
                ),
            )
            db.executemany(
                """
                INSERT INTO knowledge_articles (
                    title, category, content, source, created_by, created_at
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                [(*article, "system", _utc_now()) for article in seed_articles],
            )


def authenticate(username: str, password: str) -> Optional[dict]:
    with db_connection() as db:
        row = db.execute(
            """
            SELECT username, display_name, role, password_salt, password_hash
            FROM users
            WHERE username = ? AND active = 1
            """,
            (username.strip(),),
        ).fetchone()
        if row and _verify_password(password, row["password_salt"], row["password_hash"]):
            return {
                "username": row["username"],
                "display_name": row["display_name"],
                "role": row["role"],
            }
    return None


def record_audit(
    actor: str,
    action: str,
    entity_type: str,
    entity_id: Optional[str] = None,
    details: Optional[str] = None,
) -> None:
    with db_connection() as db:
        db.execute(
            """
            INSERT INTO audit_log (
                actor, action, entity_type, entity_id, details, created_at
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (actor, action, entity_type, entity_id, details, _utc_now()),
        )


def list_tickets() -> list[dict]:
    with db_connection() as db:
        rows = db.execute(
            """
            SELECT ticket_no, subject, customer, status, priority, assignee,
                   created_by, created_at, updated_at, description
            FROM tickets
            ORDER BY
                CASE priority WHEN 'Hoch' THEN 1 WHEN 'Mittel' THEN 2 ELSE 3 END,
                updated_at DESC
            """
        ).fetchall()
    return [dict(row) for row in rows]


def create_ticket(
    *,
    subject: str,
    description: str,
    customer: str,
    priority: str,
    actor: str,
) -> str:
    if not subject.strip() or not description.strip() or not customer.strip():
        raise ValueError("Betreff, Beschreibung und Kunde sind Pflichtfelder.")

    now = _utc_now()
    with db_connection() as db:
        next_id = db.execute(
            "SELECT COALESCE(MAX(id), 0) + 1 AS next_id FROM tickets"
        ).fetchone()["next_id"]
        ticket_no = f"CCS-{date.today().year}-{next_id:05d}"
        db.execute(
            """
            INSERT INTO tickets (
                ticket_no, subject, description, customer, status, priority,
                assignee, created_by, created_at, updated_at
            ) VALUES (?, ?, ?, ?, 'Offen', ?, NULL, ?, ?, ?)
            """,
            (
                ticket_no,
                subject.strip(),
                description.strip(),
                customer.strip(),
                priority,
                actor,
                now,
                now,
            ),
        )
    record_audit(actor, "CREATE", "ticket", ticket_no, f"Priorität: {priority}")
    return ticket_no


def update_ticket(
    *,
    ticket_no: str,
    status: str,
    priority: str,
    assignee: str,
    actor: str,
) -> None:
    with db_connection() as db:
        updated = db.execute(
            """
            UPDATE tickets
            SET status = ?, priority = ?, assignee = ?, updated_at = ?
            WHERE ticket_no = ?
            """,
            (status, priority, assignee.strip() or None, _utc_now(), ticket_no),
        ).rowcount
    if updated == 0:
        raise ValueError(f"Ticket {ticket_no} wurde nicht gefunden.")
    record_audit(
        actor,
        "UPDATE",
        "ticket",
        ticket_no,
        f"Status: {status}; Priorität: {priority}; Bearbeiter: {assignee or '-'}",
    )


def search_knowledge(query: str) -> list[dict]:
    terms = [term.lower() for term in query.split() if len(term) >= 3]
    with db_connection() as db:
        rows = db.execute(
            """
            SELECT id, title, category, content, source, created_by, created_at
            FROM knowledge_articles
            ORDER BY created_at DESC
            """
        ).fetchall()

    articles = [dict(row) for row in rows]
    if not terms:
        return articles

    def score(article: dict) -> int:
        haystack = " ".join(
            [
                article["title"],
                article["category"],
                article["content"],
                article.get("source") or "",
            ]
        ).lower()
        return sum(
            haystack.count(term) * (3 if term in article["title"].lower() else 1)
            for term in terms
        )

    ranked = [(score(article), article) for article in articles]
    return [
        article
        for points, article in sorted(ranked, key=lambda item: item[0], reverse=True)
        if points > 0
    ]


def add_knowledge_article(
    *,
    title: str,
    category: str,
    content: str,
    source: str,
    actor: str,
) -> int:
    if not title.strip() or not content.strip():
        raise ValueError("Titel und Inhalt sind Pflichtfelder.")

    with db_connection() as db:
        cursor = db.execute(
            """
            INSERT INTO knowledge_articles (
                title, category, content, source, created_by, created_at
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                title.strip(),
                category.strip() or "Allgemein",
                content.strip(),
                source.strip() or None,
                actor,
                _utc_now(),
            ),
        )
        article_id = int(cursor.lastrowid)
    record_audit(actor, "CREATE", "knowledge_article", str(article_id), title.strip())
    return article_id


def list_audit_entries(limit: int = 200) -> list[dict]:
    with db_connection() as db:
        rows = db.execute(
            """
            SELECT actor, action, entity_type, entity_id, details, created_at
            FROM audit_log
            ORDER BY id DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
    return [dict(row) for row in rows]


def get_metrics() -> dict:
    with db_connection() as db:
        ticket_metrics = db.execute(
            """
            SELECT
                COUNT(*) AS total,
                SUM(CASE WHEN status = 'Offen' THEN 1 ELSE 0 END) AS open_count,
                SUM(CASE WHEN status = 'In Bearbeitung' THEN 1 ELSE 0 END) AS active_count,
                SUM(CASE WHEN priority = 'Hoch' AND status != 'Gelöst' THEN 1 ELSE 0 END) AS critical_count
            FROM tickets
            """
        ).fetchone()
        knowledge_count = db.execute(
            "SELECT COUNT(*) AS count FROM knowledge_articles"
        ).fetchone()["count"]

    return {
        "total": ticket_metrics["total"] or 0,
        "open": ticket_metrics["open_count"] or 0,
        "active": ticket_metrics["active_count"] or 0,
        "critical": ticket_metrics["critical_count"] or 0,
        "knowledge": knowledge_count or 0,
    }


def get_license_status() -> LicenseStatus:
    mode = os.getenv("CCS_LICENSE_MODE", "demo").strip().lower()
    expiry_text = os.getenv("CCS_LICENSE_EXPIRES", "").strip()
    expires_on: Optional[date] = None

    if expiry_text:
        try:
            expires_on = date.fromisoformat(expiry_text)
        except ValueError:
            return LicenseStatus(
                mode=mode,
                valid=False,
                message="Lizenzdatum ist ungültig. Erwartet wird YYYY-MM-DD.",
                expires_on=None,
            )

    if mode == "licensed":
        if expires_on and expires_on < date.today():
            return LicenseStatus(
                mode=mode,
                valid=False,
                message=f"Lizenz abgelaufen am {expires_on.strftime('%d.%m.%Y')}.",
                expires_on=expires_on,
            )
        return LicenseStatus(
            mode=mode,
            valid=True,
            message="Lizenzmodus aktiv.",
            expires_on=expires_on,
        )

    return LicenseStatus(
        mode="demo",
        valid=True,
        message="Demomodus: für Pilotierung und Funktionsprüfung, nicht für Produktivdaten.",
        expires_on=expires_on,
    )
