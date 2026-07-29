# Compelec AI Business Platform – CCS Agent Support

Der Branch `agent/ccs-agent-support-mvp` enthält den lauffähigen Pilotkern **CCS Agent Support 0.2.0-mvp**.

## Funktionsumfang 0.2.0

### Supportbetrieb

- lokale Benutzeranmeldung mit Rollen `admin`, `agent`, `viewer`
- persistente SQLite-Datenbank
- Ticketanlage, Priorisierung, Bearbeitung und Kennzahlen
- Audit-Protokoll für Anmeldung, Änderungen, Import, Freigabe und Assistenzläufe
- Demo-/Lizenzstatus über Umgebungsvariablen

### Knowledge & AI Core

- Wissensartikel mit Freigabestatus `draft`, `approved`, `rejected`
- Datenschutzstufen `public`, `internal`, `confidential`
- lokaler Import von TXT-, PDF- und DOCX-Dokumenten
- SHA-256-Dublettenprüfung
- automatische Textsegmentierung als RAG-Vorbereitung
- dokumentierter Prüf- und Freigabeprozess
- quellengebundener Antwortentwurf mit sichtbaren Evidenzen
- Provider-Abstraktion; aktiv ist ausschließlich `local-evidence`
- Protokollierung von Frage, Antwort, Provider, Datenschutzstufe und Quellenreferenzen
- automatisierte Unit-Tests und GitHub-Actions-CI

**Governance-Regel:** Entwürfe und abgelehnte Quellen werden vom Assistenten nicht verwendet. Externe KI-Aufrufe sind in Version 0.2.0 technisch nicht aktiviert.

## Lokaler Start

```bash
python -m venv .venv
```

Windows:

```powershell
.venv\Scripts\activate
pip install -r requirements.txt
streamlit run streamlit_app.py
```

Linux/macOS:

```bash
source .venv/bin/activate
pip install -r requirements.txt
streamlit run streamlit_app.py
```

## MVP-Zugänge

| Rolle | Benutzer | Kennwort |
|---|---|---|
| Administrator | `admin` | `Compelec-Start!` |
| Support | `support` | `Support-Start!` |
| Lesemodus | `demo` | `Demo-Start!` |

**Wichtig:** Diese Startkennwörter dienen ausschließlich der lokalen Pilotierung und müssen vor einem realen Betrieb ersetzt werden.

## Konfiguration

Optionale Umgebungsvariablen:

```text
CCS_DATA_DIR=/pfad/zu/daten
CCS_LICENSE_MODE=demo
CCS_LICENSE_EXPIRES=2026-12-31
```

Für einen lizenzierten Pilotbetrieb:

```text
CCS_LICENSE_MODE=licensed
```

## Dokumentenprozess

1. Administrator importiert eine TXT-, PDF- oder DOCX-Datei.
2. Die Datei wird lokal ausgelesen und in Suchsegmente zerlegt.
3. Der Datensatz erhält zunächst den Status `draft`.
4. Ein Administrator prüft Quelle und Datenschutzstufe.
5. Erst mit Status `approved` darf der Assistent die Inhalte verwenden.
6. Jede Freigabe und jede Antworterzeugung wird protokolliert.

Hinweis: Bildbasierte oder gescannte PDFs benötigen später ein separates OCR-Modul. Version 0.2.0 extrahiert nur bereits vorhandenen PDF-Text.

## Tests

```bash
python -m py_compile ccs_core.py knowledge_ai.py streamlit_app.py
python -m unittest discover -s tests -v
```

Die CI führt dieselben Prüfungen bei Änderungen am Entwicklungszweig und bei Pull Requests aus.

## Sicherheits- und Produktgrenzen

Dieser Stand ist ein **MVP/Pilot**, keine freigegebene Enterprise-Produktivversion.

Noch nicht enthalten:

- Single Sign-on / Microsoft Entra ID
- PostgreSQL und pgvector
- echte Vektor-Embeddings und semantische Suche
- Mandantenfähigkeit
- revisionssichere Archivierung
- Verschlüsselung ruhender Daten
- Malware-Prüfung hochgeladener Dateien
- OCR für gescannte Dokumente
- E-Mail-, STARFACE-, DMS-, ERP- oder CRM-Integration
- freigegebener externer oder lokaler generativer Modellprovider
- Windows-Installer, Code-Signierung und automatischer Update-Service
- Datenschutz-Folgenabschätzung und produktive Betriebsfreigabe

## Geplante Ausbaustufe 0.3

1. PostgreSQL-Repository und strukturierte Migrationen
2. pgvector und Embedding-Schnittstelle
3. Mandanten- und Berechtigungskonzept
4. sichere Provider-Konfiguration mit Freigaberichtlinien
5. REST-API
6. Backup-/Restore-Konzept
7. Windows-Paketierung und Release-Pipeline
