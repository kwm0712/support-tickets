# Compelec AI Business Platform – CCS Agent Support MVP

Der Branch `agent/ccs-agent-support-mvp` enthält den ersten lauffähigen Pilotkern für den **CCS Agent Support**.

## Enthaltener Funktionsumfang

- lokale Benutzeranmeldung mit Rollen `admin`, `agent`, `viewer`
- persistente SQLite-Datenbank
- Ticketanlage und Ticketbearbeitung
- lokale Wissensbasis mit Suche
- kontrollierter Antwortentwurf ohne externen KI-Provider
- Audit-Protokoll
- Demo-/Lizenzstatus über Umgebungsvariablen
- deutschsprachige Streamlit-Oberfläche

## Start

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

**Wichtig:** Kennwörter vor einem realen Pilotbetrieb ändern.

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

## Sicherheits- und Produktgrenzen

Dieser Stand ist ein **MVP/Pilot**, keine freigegebene Enterprise-Produktivversion.

Noch nicht enthalten:

- Single Sign-on / Microsoft Entra ID
- PostgreSQL und pgvector
- Mandantenfähigkeit
- revisionssichere Archivierung
- Verschlüsselung ruhender Daten
- E-Mail-, STARFACE- oder ERP-Integration
- externer LLM-Provider
- Installer, Code-Signierung und automatischer Update-Service
- Datenschutz-Folgenabschätzung und produktive Betriebsfreigabe

## Nächste Ausbaustufe

1. PostgreSQL-Repository und Migrationen
2. Provider-Abstraktion für OpenAI/lokale Modelle
3. Dokumentenimport und RAG
4. Mandanten- und Berechtigungskonzept
5. REST-API
6. Windows-Installer und Release-Pipeline
7. Testkatalog und Pilotabnahme
