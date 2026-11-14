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

## Bewusste Grenzen von V1.0
Dies ist ein Demonstrator, keine produktionsreife Unternehmensanwendung. Es gibt keine echte KI-Modellanbindung, keine STARFACE-Telefonie, keine Postfachanbindung, keinen E-Mail-Versand, keine CRM-/ERP-Schreibzugriffe und keine dauerhafte, gesicherte Datenhaltung. Alle Daten sind Demo- bzw. sitzungsbezogen.

## Kosten
Keine externen APIs, kostenpflichtigen Dienste oder Cloud-KI-Aufrufe. Benötigt wird lediglich Python und Streamlit.

## Lokal starten
```bash
python -m venv .venv
# Windows:
.venv\Scripts\activate
pip install -r requirements.txt
streamlit run streamlit_app.py
```

## Nächste Schritte bis zu einem Pilotbetrieb
1. Fachliche Abnahme der Abläufe mit COMPELEC.
2. Persistente PostgreSQL-Datenhaltung und Mandanten-/Rollenmodell.
3. Authentifizierung, Audit-Trail, Backups und Datenschutzkonzept.
4. STARFACE-Anbindung zunächst im Testsystem.
5. E-Mail-Anbindung (IMAP/SMTP oder Microsoft 365) mit Entwurfs- und Freigabeworkflow.
6. Wissensimport und RAG mit Quellenangaben.
7. Automatisierte Tests, Sicherheitsprüfung und Installationspaket.
