# COMPELEC ONE Business – PostgreSQL Backup & Restore

Dieses Dokument beschreibt den kontrollierten Backup-/Restore-Prozess für das Modul **AI Support & Knowledge**.

## Voraussetzungen

- PostgreSQL Client Tools mit `pg_dump` und `pg_restore`
- gesetzte `CCS_DATABASE_URL` oder explizite Übergabe über `--database-url`
- Backup-Ziel auf einem geschützten Datenträger außerhalb des laufenden Datenbankservers

## Backup erstellen

```bash
python backup_restore.py backup --output-dir ./backups
```

Erzeugt werden:

- `compelec-one-support-<timestamp>.dump`
- `compelec-one-support-<timestamp>.manifest.json`

Das Manifest enthält Produktbezeichnung, UTC-Zeitpunkt, redigierte Datenbankadresse, Dateiname und SHA-256-Prüfsumme.

## Backup prüfen

```bash
python backup_restore.py verify \
  ./backups/compelec-one-support-<timestamp>.dump \
  ./backups/compelec-one-support-<timestamp>.manifest.json
```

Die Prüfung umfasst:

1. Vorhandensein von Dump und Manifest
2. SHA-256-Integrität
3. Lesbarkeit des PostgreSQL-Custom-Dumps über `pg_restore --list`

## Restore

Restore in eine leere bzw. vorbereitete Zieldatenbank:

```bash
python backup_restore.py restore backup.dump backup.manifest.json
```

Kontrollierter Neuaufbau einer bestehenden Zielinstanz:

```bash
python backup_restore.py restore backup.dump backup.manifest.json --clean
```

`--clean` darf nur bei einem geplanten Restore verwendet werden, da vorhandene Datenbankobjekte vor der Wiederherstellung entfernt werden können.

## Betriebsregel

Ein Backup gilt erst als betriebsfähig, wenn **Backup-Erstellung und Verify-Lauf erfolgreich** waren. Für die Produktionsfreigabe ist zusätzlich regelmäßig ein Restore-Test in einer separaten Testdatenbank durchzuführen.

## Empfohlener Rhythmus

- täglich: automatisches Datenbankbackup
- wöchentlich: SHA-256-/Dump-Verifikation
- monatlich: vollständiger Restore-Test in separater Umgebung
- vor jedem Release/Migrationslauf: manuelles verifiziertes Backup

## Sicherheitsanforderungen

- keine Zugangsdaten in Manifesten oder Logfiles
- Backups verschlüsselt speichern und Zugriff beschränken
- Aufbewahrungsfristen und Löschkonzept definieren
- Restore-Tests protokollieren
- Kunden-/Mandantendaten nur in freigegebenen Sicherungszielen speichern
