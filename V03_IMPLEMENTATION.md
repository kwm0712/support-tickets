# CCS Agent Support V0.3 – Architektur-Implementierung

Status: `0.3.0-dev` · Phase 2

## Ziel

V0.3 überführt den lokalen 0.2-MVP in eine belastbare Plattformbasis für Mandantenbetrieb, PostgreSQL/pgvector und zentral erzwingbare Berechtigungen. Externe generative KI bleibt weiterhin deaktiviert.

## Umgesetzt

- [x] eigener V0.3-Entwicklungsbranch auf Basis von 0.2.0-mvp
- [x] zentrale Rollen-/Berechtigungsmatrix für `viewer`, `agent`, `admin`
- [x] strikte Mandantengrenze ohne impliziten Cross-Tenant-Admin-Bypass
- [x] Datenschutzobergrenze pro Rolle (`public`, `internal`, `confidential`)
- [x] `EmbeddingProvider`-Schnittstelle
- [x] deterministischer lokaler Test-Embedding-Provider ohne externe API
- [x] PostgreSQL-Schema mit `tenant_key` in allen Kernobjekten
- [x] strukturierter, idempotenter PostgreSQL-Migration-Runner
- [x] pgvector-Erweiterung und Embedding-Felder für Artikel und Dokumentsegmente
- [x] GIN-Indizes für PostgreSQL Full Text Search
- [x] normalisierte `assistant_evidence` statt semikolongetrennter Quellenreferenzen
- [x] strukturierteres Audit-Schema mit `correlation_id` und JSON-Metadaten
- [x] tenant-gescopter PostgreSQL-Repository für Tickets, Knowledge, Dokumente, Chunks, Assistant Runs und Audit
- [x] race-sichere Ticketnummern über PostgreSQL-Sequenz statt `MAX(id)+1`
- [x] zentraler `SupportService` als Business-/Authorization-Schicht
- [x] Ticketfunktionen über Service-/Repository-Schicht
- [x] Knowledge-Governance über Service-/Repository-Schicht
- [x] Dokumentimport, Chunking und Embedding über Service-/Repository-Schicht
- [x] Hybrid Retrieval aus Full Text Search und pgvector Cosine Similarity
- [x] rollenbasierte Datenschutzobergrenze wird serverseitig erzwungen
- [x] eigener PostgreSQL-basierter `streamlit_v03.py`-Client
- [x] 0.2-SQLite→0.3-PostgreSQL-Migrationstool mit Dry Run und Zielschutz
- [x] lokale Re-Embedding-Erzeugung für migrierte Artikel und Dokumentsegmente
- [x] PostgreSQL-/pgvector-/Service-Integrationstests
- [x] negative RBAC-, Datenschutz- und Tenant-Grenztests
- [x] CI mit echtem `pgvector/pgvector:pg16`-Service

## Noch offen bis V0.3-MVP

- [ ] produktionsfähigen semantischen Embedding-Provider auswählen und freigeben
- [ ] Modellversionierungs-/Re-Embedding-Strategie für einen produktiven Modellwechsel implementieren
- [ ] lokale Identity-Kompatibilität durch austauschbares Identity-/SSO-Interface kapseln
- [ ] REST-Service-Grenze ergänzen, damit neben Streamlit weitere COMPELEC-ONE-Clients anbinden können
- [ ] Backup-/Restore-Prozedur für PostgreSQL dokumentieren und automatisiert testen
- [ ] Windows-Paketierung für Pilotinstallation erstellen
- [ ] Release-Artefakte mit SHA-256-Prüfsummen in CI erzeugen

## Bewusst nicht Bestandteil dieser Phase

- produktiver externer LLM-Provider
- OCR für gescannte Dokumente
- SSO/Entra-ID-Vollintegration
- Malware-Scanning
- Code-Signierung
- automatischer Update-Service
- produktive Datenschutz-/Enterprise-Freigabe

## V0.3-Abnahmekriterien

V0.3 gilt als technisch abnahmefähig, wenn:

1. die fachlichen 0.2-Kernfunktionen gegen PostgreSQL betrieben werden können,
2. jeder fachliche Datenzugriff zwingend mandantengescoopt ist,
3. RBAC und Datenschutzstufen in Service-/Repository-Schicht erzwungen werden,
4. PostgreSQL/pgvector-Migration und Integrationstests in CI grün sind,
5. der Upgrade-Pfad von einer 0.2-Pilotdatenbank getestet ist,
6. Hybrid Retrieval ausschließlich freigegebene Quellen liefert und Evidenzen nachvollziehbar protokolliert,
7. ein produktionsnaher Embedding-/Re-Embedding-Vertrag festgelegt ist,
8. die Pilotinstallation unter Windows reproduzierbar erzeugt werden kann.

Phase 2 erfüllt die Kriterien 1–6 in der Entwicklungs-/Pilotarchitektur. Kriterien 7–8 bleiben die nächsten V0.3-Gates.
