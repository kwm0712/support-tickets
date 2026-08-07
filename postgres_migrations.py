from __future__ import annotations

from pathlib import Path


def _migration_dir() -> Path:
    return Path(__file__).resolve().parent / "migrations" / "postgres"


def apply_postgres_migrations(database_url: str) -> list[str]:
    """Apply pending PostgreSQL migrations in filename order.

    Every migration is responsible for inserting its own version into
    ``schema_migrations``. The runner intentionally executes only migrations that are
    not yet registered, making startup and CI runs deterministic and idempotent.
    """
    if not database_url.strip():
        raise ValueError("database_url darf nicht leer sein.")

    try:
        import psycopg
    except ImportError as exc:
        raise RuntimeError(
            "PostgreSQL-Unterstützung benötigt das Paket 'psycopg'."
        ) from exc

    migration_files = sorted(_migration_dir().glob("*.sql"))
    applied_now: list[str] = []

    with psycopg.connect(database_url, autocommit=True) as connection:
        for migration_file in migration_files:
            version = migration_file.stem
            table_exists = connection.execute(
                "SELECT to_regclass('public.schema_migrations') IS NOT NULL"
            ).fetchone()[0]
            if table_exists:
                already_applied = connection.execute(
                    "SELECT 1 FROM schema_migrations WHERE version = %s",
                    (version,),
                ).fetchone()
                if already_applied:
                    continue

            connection.execute(migration_file.read_text(encoding="utf-8"))
            applied_now.append(version)

    return applied_now
