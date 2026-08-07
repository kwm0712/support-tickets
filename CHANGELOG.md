# Changelog

## 0.3.0-dev

- zentrale Rollen-/Berechtigungsmatrix und Tenant-Kontext eingeführt
- Datenschutzobergrenzen an Rollen gekoppelt
- strikte Cross-Tenant-Sperre ohne impliziten Admin-Bypass ergänzt
- `EmbeddingProvider`-Vertrag mit lokalem deterministischem Testprovider eingeführt
- PostgreSQL-Kernschema mit pgvector-Unterstützung und `tenant_key` ergänzt
- normalisierte Assistant-Evidenzen und strukturierteres Audit-Schema ergänzt
- tenant-gescopter PostgreSQL-Repository-Adapter für Ticket- und Audit-Basis eingeführt
- race-sichere Ticketnummern über PostgreSQL-Sequenz umgesetzt
- PostgreSQL-/pgvector-Integrationstests und negative RBAC-/Tenant-Tests ergänzt
- GitHub-Actions-CI um echten pgvector/PostgreSQL-Service erweitert
- Version auf `0.3.0-dev` angehoben

### Noch offen bis 0.3.0-mvp

- vollständige Verdrahtung der bestehenden 0.2-Funktionen auf die Repository-Schicht
- PostgreSQL-Adapter für Knowledge, Documents, Chunks und Assistant Runs
- SQLite-zu-PostgreSQL-Migrationspfad
- Hybrid Retrieval aus lexikalischer und Vektorsuche
- REST-Service-Grenze und Windows-Paketierung

## 0.2.0-mvp

- additive Datenbankmigration für Knowledge Governance ergänzt
- Freigabestatus `draft`, `approved`, `rejected` eingeführt
- Datenschutzstufen `public`, `internal`, `confidential` eingeführt
- TXT-, PDF- und DOCX-Import ergänzt
- SHA-256-Dublettenprüfung für Dokumente ergänzt
- Dokumentsegmentierung als lokale RAG-Vorbereitung umgesetzt
- quellengebundene Evidenzsuche für Artikel und Dokumentsegmente ergänzt
- Provider-Abstraktion eingeführt; ausschließlich `local-evidence` freigegeben
- Assistenzläufe mit Frage, Antwort, Provider, Datenschutzstufe und Quellen protokolliert
- Oberfläche um Dokumentenprüfung, Governance-Kennzahlen und Quellenanzeige erweitert
- Lizenzmodus durch verpflichtende Kennwortvariablen und Mindestlänge gehärtet
- Wechsel mit aktiven Demo-Kennwörtern in den Lizenzmodus wird blockiert
- Demo-Zugangsdaten werden ausschließlich im Demomodus angezeigt
- Unit-Tests für Freigabelogik, Datenschutzfilter, Dokumentabruf, Provider-Sperre und Lizenzkennwörter ergänzt
- GitHub-Actions-CI für Kompilierung und Tests ergänzt

### Bekannte Grenzen

- lexikalische Suche statt Vektor-Embeddings
- PDF-Import ohne OCR für gescannte Seiten
- SQLite statt PostgreSQL/pgvector
- kein externer oder lokal generativer Modellprovider
- noch keine Mandantenfähigkeit, SSO-Anbindung oder Dateischadcodeprüfung
- noch kein Windows-Installer, keine Code-Signierung und kein Update-Service

## 0.1.0-mvp

- Streamlit-Demotemplate durch CCS Agent Support Oberfläche ersetzt
- SQLite-Persistenz für Benutzer, Tickets, Wissen und Audit ergänzt
- Rollen `admin`, `agent` und `viewer` eingeführt
- sichere Passwort-Hashes mit PBKDF2-HMAC ergänzt
- Ticketanlage und Ticketbearbeitung umgesetzt
- lokale Wissensbasis und kontrollierter Antwortentwurf umgesetzt
- Demo-/Lizenzstatus über Umgebungsvariablen ergänzt
- Smoke-Tests und Pilot-Abnahmecheckliste ergänzt
