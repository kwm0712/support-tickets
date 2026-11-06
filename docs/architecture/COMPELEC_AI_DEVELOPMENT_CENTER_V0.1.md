# COMPELEC AI Development Center – Zielarchitektur V0.1

**Status:** Architekturentwurf und Implementierungsbaseline  
**Pilot:** Compelec KI-ServiceCenter  
**Leitentscheidung:** Fünf spezialisierte Agenten auf einem gemeinsamen, kontrollierten Plattformkern.

## 1. Ziele und Nicht-Ziele

Ziele:
- Wiederverwendbare KI-gestützte Entwicklungs- und Qualitätssicherungsprozesse für Compelec-Produkte.
- Nachvollziehbare Agentenläufe mit expliziten Berechtigungen, Freigaben und Audit-Ereignissen.
- Gemeinsame Integrations-, Daten-, Modell- und Wissensdienste.
- ServiceCenter als erster vertikaler Pilot mit Mandantentrennung und Dokumentfreigaben.
- Reproduzierbare Tests und Releases; keine ungeprüften Änderungen an Produktivsystemen.

Nicht-Ziele der ersten Ausbaustufe:
- Keine autonomen Änderungen an Produktivdaten oder Produktivsystemen.
- Kein unbegrenzter Zugriff eines Agenten auf Repositories, Secrets oder Kundendokumente.
- Keine Produktionsfreigabe allein aufgrund erfolgreicher Unit-Tests.
- Kein Austausch bestehender ServiceCenter-Komponenten ohne Bestandsaufnahme und Migrationsplan.

## 2. Logische Architektur

1. **Web Control Center (PWA):** Projekte, Agentenläufe, Freigaben, Testergebnisse, Releases und Audit-Ansicht.
2. **API / Application Layer (FastAPI):** Authentifizierung, Autorisierung, Validierung, Use Cases und versionierte REST-API.
3. **Agent Orchestrator:** Zustandsmaschine für Aufträge; delegiert nur freigegebene Teilaufgaben an Agenten.
4. **Agenten:** Development, Database, Security, QA und Release. Jeder Agent erhält eine eng begrenzte Tool-Allowlist.
5. **ONE Core Services:** Projektkontext, Prompt-/Skill-Versionen, Modelladapter, Tool Registry, Wissenssuche und Audit.
6. **Persistence:** PostgreSQL als führende relationale Datenbank; pgvector erst nach Evaluierung des Retrieval-Bedarfs.
7. **External Adapters:** GitHub, CI, Artefaktspeicher und freigegebene Compelec-Systeme über explizite Adapter.

## 3. Agentenverantwortung und Grenzen

| Agent | Verantwortet | Darf nicht selbstständig |
|---|---|---|
| Development | Analyse, Änderungsvorschläge, Code und technische Dokumentation | In geschützte Branches mergen oder Produktivsysteme ändern |
| Database | Schemaentwurf, Migrationen, Query-Analyse | Migrationen auf Produktion ausführen |
| Security | Threat Modeling, Rechteprüfung, Dependency-/Secret-Prüfung | Sicherheitsfreigabe eigener Änderungen erteilen |
| QA | Unit-, Integrations-, Regression- und Negativtests | Fehlgeschlagene Tests übergehen |
| Release | Versionierung, Build, SBOM/Checksummen, Release Notes | Artefakte ohne erforderliche Gates veröffentlichen |

Agenten liefern strukturierte Ergebnisse: Auftrag, verwendeter Kontext, Änderungen, Tool-Aufrufe, Prüfergebnisse, offene Risiken und benötigte menschliche Entscheidung.

## 4. Sicherheits- und Governance-Baseline

- **Human-in-the-Loop:** Merge, produktive Migration, Veröffentlichung und Rechteausweitung benötigen menschliche Freigabe.
- **Least Privilege:** Pro Agent und Projekt separate Tool-Allowlist und minimale Credentials.
- **Mandantentrennung:** Mandanten-ID wird serverseitig aus der authentifizierten Identität abgeleitet; nie aus einem ungeprüften Request-Feld vertraut.
- **Dokumentzugriff:** Freigabeprüfung serverseitig bei jedem Zugriff; IDs sind kein Berechtigungsnachweis.
- **Audit:** Ereigniskette für Identität, Mandant, Aktion, Ressource, Entscheidung, Zeit und Korrelations-ID; keine Secrets oder unnötigen Dokumentinhalte protokollieren.
- **Secrets:** Ausschließlich Secret Store/Umgebungsvariablen; niemals in Prompts, Logs oder Repository.
- **Prompt Injection:** Dokumente und Repository-Inhalte sind nicht vertrauenswürdige Daten, keine ausführbaren Anweisungen.
- **Datenschutz:** Datenminimierung, Zweckbindung, Lösch- und Aufbewahrungskonzept sowie Auftragsverarbeitungsprüfung vor Kundeneinsatz.
- **Isolation:** Tests und Agentenwerkzeuge laufen in isolierten, kurzlebigen Umgebungen mit begrenztem Netzwerkzugriff.

## 5. ServiceCenter-Pilot – erster fachlicher Durchstich

**Use Case:** Ein Supportmitarbeiter sucht freigegebene Wissensdokumente seines eigenen Mandanten und darf ausschließlich diese öffnen.

Ablauf:
1. Benutzer authentifizieren und Mandant serverseitig bestimmen.
2. Suchanfrage validieren und mit Mandantenfilter ausführen.
3. Nur freigegebene, nicht widerrufene Dokumente als Treffer liefern.
4. Vor dem Öffnen Berechtigung und Freigabestatus erneut serverseitig prüfen.
5. Zugriff mit Dokumentreferenz, Benutzer, Mandant und Entscheidung auditieren.
6. Fremde Dokument-IDs, fehlende Freigaben, widerrufene Freigaben und Mandantenwechsel negativ testen.

Ein Filter nur in der Benutzeroberfläche oder eine schwer erratbare Dokument-ID genügt nicht. Die Autorisierung muss in der Datenzugriffsschicht durchgesetzt werden.

## 6. Vorgeschlagene Datenobjekte

- tenants
- users, roles, user_roles
- projects, project_memberships
- agent_definitions, agent_runs, agent_run_events
- documents, document_grants, document_access_events
- approval_requests, approval_decisions
- test_runs, build_artifacts, release_records
- audit_events

Jede mandantenbezogene Tabelle erhält tenant_id, passende Fremdschlüssel und Indizes. PostgreSQL Row-Level Security wird als zusätzliche Schutzschicht geprüft; sie ersetzt nicht die Anwendungsautorisierung.

## 7. Technischer Startstack

- Python 3.12+
- FastAPI und Pydantic
- PostgreSQL; SQLAlchemy 2 und Alembic
- pytest, Ruff und mypy
- Docker Compose für lokale Entwicklungsumgebung
- GitHub Actions oder vorhandene CI nach Repository-Bestandsaufnahme
- Modellanbieter hinter einem austauschbaren Adapter; keine direkte Anbieterabhängigkeit in Fachlogik

Die aktuelle Repository-Anwendung ist ein einfacher Streamlit-Ticket-Demonstrator mit In-Memory-Daten. Sie ist kein nachgewiesener Produktionscode des Compelec KI-ServiceCenters. Deshalb wird die Plattform zunächst in einem separaten Verzeichnis/Modul aufgebaut und nicht als produktive ServiceCenter-Integration ausgegeben.

## 8. Qualitäts- und Release-Gates

1. Formatierung, Lint und Typprüfung erfolgreich.
2. Unit-Tests und Negativtests erfolgreich.
3. Mandanten- und Berechtigungstests erfolgreich.
4. Integrations- und Migrationstests erfolgreich.
5. Security-Scan und Secret-Scan ohne offene kritische Befunde.
6. Review und menschliche Freigabe.
7. Reproduzierbarer Build, Release Notes und SHA-256.
8. Rollback-/Wiederherstellungsnachweis für Datenbankänderungen.

## 9. Umsetzungsplan

- **V0.1 – Fundament:** Architektur, API-Skelett, Konfiguration, Health-Endpunkt, Test- und CI-Grundlage.
- **V0.2 – Identität und Mandanten:** Benutzer-/Rollenmodell, Mandantenkontext und negative Zugriffstests.
- **V0.3 – Dokumentfreigaben:** Dokumentregister, Grant-/Revocation-Logik und Audit-Ereignisse.
- **V0.4 – Wissenssuche:** Mandantenisolierte Suche und sichere Dokumentöffnung.
- **V0.5 – Agentenorchestrierung:** Agentenverträge, Tool-Allowlist, Freigabe-Workflow.
- **V0.6 – QA/Release:** reproduzierbare Pipeline, Artefakte, Prüfreport und Betriebsdokumentation.

## 10. Offene Architekturentscheidungen vor Produktivbetrieb

- Bestehende ServiceCenter-Quellcodebasis und Deployment-Topologie.
- Identitätsquelle (lokal, Entra ID oder vorhandener Compelec-SSO-Dienst).
- Mandanten- und Rollenmodell aus dem realen Kundenbetrieb.
- Dokumentenspeicher, Metadatenquelle und bestehende Freigabelogik.
- Modellanbieter, Hostingregion, Datenverarbeitung und AV-Verträge.
- Backup, Aufbewahrung, Löschung, Monitoring und Incident-Prozess.

**Freigabestatus:** V0.1 ist eine technische Startbaseline. Eine Produktionsfreigabe ist ausdrücklich nicht erteilt.
