# CCS Agent Support V0.3 – Architektur-Implementierung

Status: `0.3.0-dev`

## Ziel

V0.3 überführt den lokalen 0.2-MVP in eine belastbare Plattformbasis für Mandantenbetrieb, PostgreSQL/pgvector und zentral erzwingbare Berechtigungen. Externe generative KI bleibt weiterhin deaktiviert.

## Bereits umgesetzt

- [x] eigener V0.3-Entwicklungsbranch auf Basis von 0.2.0-mvp
- [x] zentrale Rollen-/Berechtigungsmatrix für `viewer`, `agent`, `admin`
- [x] strikte Mandantengrenze ohne impliziten Cross-Tenant-Admin-Bypass
- [x] Datenschutzobergrenze pro Rolle (`public`, `internal`, `confidential`)
- [x] `EmbeddingProvider`-Schnittstelle
- [x] deterministischer lokaler Test-Embedding-Provider ohne externe API
- [x] PostgreSQL-Schema mit `tenant_key` in allen Kernobjekten
- [x] pgvector-Erweiterung und Embedding-Felder für Dokumentsegmente
- [x] normalisierte `assistant_evidence` statt semikolongetrennter Quellenreferenzen
- [x] strukturierteres Audit-Schema mit `correlation_id` und JSON-Metadaten
- [x] tenant-gescopter PostgreSQL-Repository-Adapter für Ticket/Audit-Basis
- [x] race-sichere Ticketnummern über PostgreSQL-Sequenz statt `MAX(id)+1`
- [x] PostgreSQL-/pgvector-Integrationstest
- [x] negative RBAC-, Datenschutz- und Tenant-Grenztests
- [x] CI mit echtem `pgvector/pgvector:pg16`-Service

## Noch offen bis V0.3-MVP

- [ ] bestehende Streamlit-/Service-Funktionen vollständig auf Repository-Abstraktion umstellen
- [ ] PostgreSQL-Repository für Knowledge Articles, Documents, Chunks und Assistant Runs ergänzen
- [ ] bestehende SQLite-Pilotdaten nach PostgreSQL migrierbar machen
- [ ] Hybrid Retrieval aus lexikalischem Score und Vektorähnlichkeit implementieren
- [ ] Embedding-Metadaten und Re-Embedding-Strategie produktiv verdrahten
- [ ] Benutzerkontext im UI aus zentraler Authorization-Schicht ableiten
- [ ] Datenschutzstufe im UI auf die tatsächlich zulässige Rollenobergrenze begrenzen
- [ ] REST-Service-Grenze definieren, damit Streamlit nur Frontend bleibt
- [ ] Backup-/Restore-Prozedur für PostgreSQL dokumentieren und testen
- [ ] Windows-Paketierung für Pilotinstallation erstellen

## Bewusst nicht Bestandteil von V0.3

- produktiver externer LLM-Provider
- OCR für gescannte Dokumente
- SSO/Entra-ID-Vollintegration
- Malware-Scanning
- Code-Signierung
- automatischer Update-Service
- produktive Datenschutz-/Enterprise-Freigabe

## V0.3-Abnahmekriterien

V0.3 gilt als technisch abnahmefähig, wenn:

1. alle bisherigen 0.2-Funktionen gegen PostgreSQL betrieben werden können,
2. jeder fachliche Datenzugriff zwingend mandantengescoopt ist,
3. RBAC und Datenschutzstufen nicht nur im UI, sondern in der Service-/Repository-Schicht erzwungen werden,
4. PostgreSQL/pgvector-Migration und Integrationstests in CI grün sind,
5. ein Upgrade-Pfad von einer 0.2-Pilotdatenbank dokumentiert und getestet ist,
6. Hybrid Retrieval ausschließlich freigegebene Quellen liefert und Evidenzen nachvollziehbar protokolliert,
7. die Pilotinstallation unter Windows reproduzierbar erzeugt werden kann.
