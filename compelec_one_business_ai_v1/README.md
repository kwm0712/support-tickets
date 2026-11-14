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
Keine externen APIs, kostenpflichtigen Dienste oder Cloud-KI-Aufrufe. Benötigt wird lediglich Python und Streamlit. Die automatisierte Prüfung verwendet GitHub Actions und prüft derzeit Python-Syntax sowie die Installierbarkeit der Abhängigkeiten. Sie ist noch kein vollständiger Funktions- oder Sicherheitstest.

## Lokal starten
```bash
python -m venv .venv
# Windows:
.venv\\Scripts\\activate
pip install -r requirements.txt
streamlit run streamlit_app.py
```

## Technische Prüfung
Bei Pushes auf den Branch `compelec-one-business-ai-v1.0` und bei Pull Requests auf diesen Branch läuft der Workflow `.github/workflows/compelec-one-business-ai-check.yml`. Er richtet Python 3.12 ein, installiert die Abhängigkeiten und führt `compileall` aus.

## Nächste Schritte bis zu einem Pilotbetrieb
1. Fachliche Abnahme der Abläufe mit COMPELEC.
2. PostgreSQL-Datenhaltung mit Mandanten-, Benutzer- und Rollenmodell.
3. Authentifizierung, Audit-Trail, Backups und Datenschutzkonzept.
4. STARFACE-Anbindung zunächst im Testsystem.
5. E-Mail-Anbindung (IMAP/SMTP oder Microsoft 365) mit Entwurfs- und Freigabeworkflow.
6. Wissensimport und RAG mit Quellenangaben.
7. Automatisierte Funktions-, Integrations- und Sicherheitstests sowie Installationspaket.


## V1.1 – technische Grundlage
- GitHub Actions prüft Python-Syntax und Abhängigkeiten.
- PostgreSQL-Schemaentwurf für Mandanten, Benutzerrollen, Kundenhistorie, Support, Telefon, E-Mail-Freigaben und Audit-Protokoll: `database/schema_v1_1.sql`.
- Architektur- und Sicherheitsentscheidungen: `docs/ARCHITEKTUR_V1_1.md`.
- Das SQL ist ein Entwurf und wurde noch nicht gegen eine laufende PostgreSQL-Instanz getestet oder angewendet.
