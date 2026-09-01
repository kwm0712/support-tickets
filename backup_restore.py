from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path


@dataclass(frozen=True)
class BackupManifest:
    product: str
    created_at_utc: str
    database_url_redacted: str
    dump_filename: str
    sha256: str
    dump_format: str = "custom"


def _require_tool(name: str) -> str:
    executable = shutil.which(name)
    if not executable:
        raise RuntimeError(f"Erforderliches PostgreSQL-Werkzeug fehlt: {name}")
    return executable


def _redact_database_url(database_url: str) -> str:
    if "@" not in database_url:
        return database_url
    prefix, suffix = database_url.rsplit("@", 1)
    scheme = prefix.split("://", 1)[0] if "://" in prefix else "postgresql"
    return f"{scheme}://***:***@{suffix}"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def create_backup(database_url: str, output_dir: Path) -> tuple[Path, Path]:
    pg_dump = _require_tool("pg_dump")
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    dump_path = output_dir / f"compelec-one-support-{timestamp}.dump"
    manifest_path = output_dir / f"compelec-one-support-{timestamp}.manifest.json"

    subprocess.run(
        [
            pg_dump,
            "--format=custom",
            "--no-owner",
            "--no-privileges",
            "--file",
            str(dump_path),
            database_url,
        ],
        check=True,
    )

    checksum = sha256_file(dump_path)
    manifest = BackupManifest(
        product="COMPELEC ONE Business - AI Support & Knowledge",
        created_at_utc=datetime.now(timezone.utc).isoformat(),
        database_url_redacted=_redact_database_url(database_url),
        dump_filename=dump_path.name,
        sha256=checksum,
    )
    manifest_path.write_text(
        json.dumps(asdict(manifest), indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return dump_path, manifest_path


def verify_backup(dump_path: Path, manifest_path: Path) -> None:
    pg_restore = _require_tool("pg_restore")
    if not dump_path.is_file():
        raise RuntimeError(f"Backup-Datei fehlt: {dump_path}")
    if not manifest_path.is_file():
        raise RuntimeError(f"Manifest fehlt: {manifest_path}")

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    expected = str(manifest.get("sha256", "")).strip().lower()
    actual = sha256_file(dump_path).lower()
    if not expected or actual != expected:
        raise RuntimeError("SHA-256-Prüfung des Backups ist fehlgeschlagen.")

    subprocess.run([pg_restore, "--list", str(dump_path)], check=True, stdout=subprocess.DEVNULL)


def restore_backup(
    database_url: str,
    dump_path: Path,
    manifest_path: Path,
    *,
    clean: bool = False,
) -> None:
    verify_backup(dump_path, manifest_path)
    pg_restore = _require_tool("pg_restore")
    command = [
        pg_restore,
        "--exit-on-error",
        "--no-owner",
        "--no-privileges",
        "--dbname",
        database_url,
    ]
    if clean:
        command.extend(["--clean", "--if-exists"])
    command.append(str(dump_path))
    subprocess.run(command, check=True)


def _database_url_from_args(value: str | None) -> str:
    database_url = (value or os.getenv("CCS_DATABASE_URL", "")).strip()
    if not database_url:
        raise RuntimeError("CCS_DATABASE_URL oder --database-url ist erforderlich.")
    return database_url


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="COMPELEC ONE PostgreSQL Backup/Restore für AI Support & Knowledge"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    backup = subparsers.add_parser("backup", help="PostgreSQL-Backup erstellen")
    backup.add_argument("--database-url")
    backup.add_argument("--output-dir", default="./backups")

    verify = subparsers.add_parser("verify", help="Backup und SHA-256 prüfen")
    verify.add_argument("dump")
    verify.add_argument("manifest")

    restore = subparsers.add_parser("restore", help="Backup wiederherstellen")
    restore.add_argument("dump")
    restore.add_argument("manifest")
    restore.add_argument("--database-url")
    restore.add_argument(
        "--clean",
        action="store_true",
        help="Vor Restore vorhandene Objekte entfernen (nur für kontrollierte Wiederherstellung).",
    )
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    try:
        if args.command == "backup":
            dump_path, manifest_path = create_backup(
                _database_url_from_args(args.database_url),
                Path(args.output_dir),
            )
            print(f"Backup: {dump_path}")
            print(f"Manifest: {manifest_path}")
        elif args.command == "verify":
            verify_backup(Path(args.dump), Path(args.manifest))
            print("Backup-Prüfung erfolgreich.")
        elif args.command == "restore":
            restore_backup(
                _database_url_from_args(args.database_url),
                Path(args.dump),
                Path(args.manifest),
                clean=bool(args.clean),
            )
            print("Restore erfolgreich abgeschlossen.")
        return 0
    except (RuntimeError, subprocess.CalledProcessError, OSError, json.JSONDecodeError) as exc:
        print(f"FEHLER: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
