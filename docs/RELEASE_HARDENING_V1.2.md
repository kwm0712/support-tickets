# COMPELEC ONE Business V1.2 – Release-Hardening-Abnahme

Stand: 09.11.2026
Branch: fix/business-v1.2-enterprise-hardening
Pull Request: #14

## Aktueller Nachweis

- GitHub Actions CI-Lauf #235: erfolgreich.
- Python-Quellcode-Kompilierung: erfolgreich.
- Unit- und PostgreSQL-Integrationstests: erfolgreich.
- CI-Source-Artefakt wurde erzeugt und hochgeladen.
- Der Source-Bundle-Hash ist im CI-Artefakt SHA256SUMS-source.txt dokumentiert.

## Vor Merge und Produktionsfreigabe zwingend abarbeiten

### 1. PostgreSQL-Rollenprüfung

Die Anwendung darf nicht als Superuser oder mit BYPASSRLS laufen.

```sql
SELECT rolname, rolsuper, rolbypassrls
FROM pg_roles
WHERE rolname = current_user;
```

Erwartung: rolsuper = false und rolbypassrls = false.

### 2. Mandantentrennung in der Zielumgebung

- Zwei Testmandanten anlegen.
- Mit Anwendungsrolle Mandant A anmelden.
- Lesen, Ändern und Löschen von Daten aus Mandant B muss verhindert werden.
- Schreibversuche mit fremdem tenant_key müssen abgewiesen werden.
- Ohne gesetzten app.tenant_id darf kein mandantenbezogener Datensatz sichtbar sein.

### 3. Windows-Deployment

Auf einem sauberen Windows-x64-System ausführen:

- Python 3.12 und Projektabhängigkeiten installieren.
- Inno Setup 6 bereitstellen.
- packaging/windows/build_windows.ps1 ausführen.
- Portable ZIP und Setup-EXE auf Existenz und Dateiversion prüfen.
- Installation, Programmstart, Upgrade und Deinstallation testen.
- SHA-256 der beiden erzeugten Release-Dateien gegen SHA256SUMS.txt prüfen.

### 4. PostgreSQL Backup/Restore

- Backup mit backup_restore.py backup erstellen.
- Manifest und SHA-256 mit backup_restore.py verify prüfen.
- In eine separate Testdatenbank wiederherstellen.
- Schema, Migrationen, Mandantenanzahl und repräsentative Datensätze vergleichen.
- Restore-Ergebnis und Laufzeit protokollieren.

## Freigabekriterium

NO-GO, solange einer der vier Abnahmepunkte nicht mit reproduzierbarem Nachweis abgeschlossen ist. Der erfolgreiche CI-Lauf allein ist keine Windows-Installations- oder Produktionsfreigabe.

Nach erfolgreicher Abnahme: PR-Review, Freigabe, Merge und erst danach versioniertes Release erstellen.
