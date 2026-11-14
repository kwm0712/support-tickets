# COMPELEC ONE – Business AI V1.0

Interner Demonstrator für Support, Vertrieb sowie Telefon- und E-Mail-Kommunikation.

## Umfang
- Übersicht / Cockpit
- Supportvorgänge lokal erfassen und allgemeine Prüfschritte anzeigen
- Vertriebs-Gesprächsleitfaden vorbereiten
- Telefonnotizen und Rückrufwünsche erfassen
- E-Mail-Entwürfe erstellen
- Wissensbereich als Import-Vorbereitung
- Integrationsstatus für STARFACE, E-Mail, PMS32, InGenius-Office und PostgreSQL

## Bewusste Grenzen
Dies ist ein Demonstrator, keine produktionsreife Unternehmensanwendung. Es gibt keine echte KI-Modellanbindung, keine STARFACE-Telefonie, keine Postfachanbindung, keinen E-Mail-Versand, keine CRM-/ERP-Schreibzugriffe und keine dauerhafte, gesicherte Datenhaltung. Die Arbeitsdaten liegen derzeit im Streamlit-Sitzungsspeicher und können beim Neustart verloren gehen.

## Kosten
Keine externen APIs, kostenpflichtigen Dienste oder Cloud-KI-Aufrufe. Benötigt wird lediglich Python und Streamlit. Die automatisierte Prüfung verwendet GitHub Actions; es ist vor einer längeren oder häufigen Nutzung das verfügbare kostenlose Minutenkontingent des GitHub-Kontos zu beachten.

## Lokal starten
```bash
python -m venv .venv
# Windows:
.venv\\Scripts\\activate
pip install -r requirements.txt
streamlit run streamlit_app.py
```

## Technische Prüfung
Der Workflow `.github/workflows/compelec-one-business-ai-check.yml` läuft bei Pushes und Pull Requests auf dem Entwicklungsbranch `compelec-one-business-ai-v1.0`.
Der Lauf vom 14.11.2026 (Run 11) war erfolgreich:
- Python-Abhängigkeiten installiert und Syntax geprüft.
- PostgreSQL 16 gestartet und `database/schema_v1_1.sql` erfolgreich eingespielt.
- Mandantentrennung mit zwei künstlichen Testmandanten erfolgreich geprüft.
Prüflauf: https://github.com/kwm0712/support-tickets/actions/runs/43607430856

Die CI-Prüfung ist ein technischer Basistest, keine Produktivfreigabe. Das Schema wurde nur in einer temporären Testdatenbank geprüft. Die Streamlit-Anwendung ist weiterhin nicht an PostgreSQL angeschlossen.

## Nächste Schritte bis zu einem Pilotbetrieb
1. Datenzugriffsschicht mit sicherem, transaktionsgebundenem Mandantenkontext entwickeln.
2. Authentifizierung, Benutzer-/Rollenmodell und Audit-Trail umsetzen.
3. Streamlit-Demonstrator schrittweise auf persistente PostgreSQL-Speicherung umstellen.
4. Backups, Wiederherstellungstests und Datenschutzkonzept abnehmen.
5. STARFACE-Anbindung zunächst im Testsystem.
6. E-Mail-Anbindung mit Entwurfs- und Freigabeworkflow.
7. Wissensimport und RAG mit Quellenangaben.
8. Automatisierte Funktions-, Integrations- und Sicherheitstests sowie Installationspaket.

## V1.1 – technische Grundlage
- GitHub Actions prüft Python-Syntax, Abhängigkeiten, PostgreSQL-Schema und RLS-Mandantentrennung.
- PostgreSQL-Schema: `database/schema_v1_1.sql`.
- Architektur- und Sicherheitsentscheidungen: `docs/ARCHITEKTUR_V1_1.md`.
