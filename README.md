# Compelec AI Business Platform – CCS Agent Support

CCS Agent Support ist der kontrollierte Support-/Knowledge-Kern der Compelec AI Business Platform und als Baustein für die spätere Integration in COMPELEC ONE ausgelegt.

## Versionen

### 0.2.0-mvp – stabiler Pilotkern

Der Branch `agent/ccs-agent-support-mvp` enthält den SQLite-basierten Pilotkern mit:

- lokaler Benutzeranmeldung und Rollen `admin`, `agent`, `viewer`
- Ticketanlage, Bearbeitung, Kennzahlen und Audit
- Wissens-Governance `draft` / `approved` / `rejected`
- Datenschutzstufen `public` / `internal` / `confidential`
- TXT-, PDF- und DOCX-Import
- SHA-256-Dublettenprüfung und Chunking
- quellengebundenem Provider `local-evidence`
- blockierten externen KI-Aufrufen
- Unit-/Smoke-Tests und GitHub Actions

### 0.3.0-dev – PostgreSQL / Tenant / Hybrid Retrieval

Der Branch `agent/ccs-agent-support-v0.3-architecture` baut auf 0.2 auf. Phase 2 enthält jetzt einen real nutzbaren PostgreSQL-Pfad:

- PostgreSQL 16 + pgvector
- strukturierte, idempotente SQL-Migrationen
- zentraler `SupportService` für RBAC, Datenschutz und Business-Logik
- tenant-gescopter `PostgresRepository`
- strikte Mandantentrennung ohne impliziten Admin-Bypass
- Rollen-/Permission-Matrix für Tickets, Wissen, Dokumente, Assistenz und Audit
- lokale Embedding-Schnittstelle `EmbeddingProvider`
- deterministischer lokaler Testprovider `ccs-local-hash-v1`
- Hybrid Retrieval aus PostgreSQL Full Text Search + pgvector Cosine Similarity
- Embeddings für Wissensartikel und Dokumentsegmente
- normalisierte `assistant_evidence` mit lexical/vector/combined score
- PostgreSQL-basierte Assistenzläufe und Auditierung
- eigener V0.3-Client `streamlit_v03.py`
- Migrationstool von 0.2 SQLite nach 0.3 PostgreSQL
- PostgreSQL-/pgvector-/RBAC-/Tenant-/Service-Integrationstests

**Wichtig:** Der lokale Hash-Embedding-Provider ist eine technische Entwicklungsimplementierung für Vertrag, Persistenz und Retrieval-Orchestrierung. Er ist kein semantisches Produktionsmodell. Externe generative KI bleibt deaktiviert.

## V0.2 lokal starten

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

## V0.3 PostgreSQL starten

Voraussetzung: PostgreSQL mit installierter `vector`-Extension. Für Entwicklung/CI wird `pgvector/pgvector:pg16` verwendet.

Beispielkonfiguration:

```text
CCS_DATABASE_URL=postgresql://ccs:password@127.0.0.1:5432/ccs_support
CCS_TENANT_ID=compelec
CCS_TENANT_NAME=Compelec Computersysteme GmbH
CCS_LICENSE_MODE=demo
```

Danach:

```bash
pip install -r requirements.txt
streamlit run streamlit_v03.py
```

Beim Start des V0.3-Clients werden ausstehende PostgreSQL-Migrationen über `postgres_migrations.py` angewendet. Die lokale 0.2-Anmeldung bleibt vorerst als Identity-Kompatibilitätspfad erhalten; SSO/OIDC ist ein späterer Architekturbaustein.

## 0.2 SQLite nach 0.3 PostgreSQL migrieren

Zuerst immer Backup der SQLite-Datei erstellen.

Dry Run:

```bash
python migrate_v02_sqlite_to_v03_postgres.py ./data/ccs_support.db \
  postgresql://ccs:password@127.0.0.1:5432/ccs_support \
  --tenant-key compelec --dry-run
```

Migration:

```bash
python migrate_v02_sqlite_to_v03_postgres.py ./data/ccs_support.db \
  postgresql://ccs:password@127.0.0.1:5432/ccs_support \
  --tenant-key compelec \
  --tenant-name "Compelec Computersysteme GmbH"
```

Übernommen werden – soweit in der Quelldatenbank vorhanden – Benutzer/Passworthashes, Tickets, Wissensartikel, Dokumente und Chunks, Assistenzläufe, Quellenreferenzen und Auditdaten. Artikel und Dokumentsegmente erhalten beim Import lokale V0.3-Embeddings. Die Migration verweigert den Start, wenn der Zielmandant bereits Fachdaten enthält.

## Governance

- `draft` und `rejected` werden nicht als Evidenz verwendet.
- Datenschutzobergrenzen werden aus Rollen/Berechtigungen abgeleitet, nicht nur aus UI-Auswahl.
- `viewer` darf lesen, aber nicht schreiben.
- `agent` darf Tickets bearbeiten und interne Assistenz nutzen, aber kein Audit lesen oder Governance freigeben.
- `admin` darf Governance, vertrauliche Assistenz und Audit nutzen.
- Repository-Methoden sind immer an genau einen Mandanten gebunden.
- Externe generative Provider sind weiterhin nicht freigeschaltet.

## Tests

```bash
python -m py_compile \
  architecture.py embedding.py postgres_migrations.py postgres_repository.py \
  support_service.py v03_runtime.py migrate_v02_sqlite_to_v03_postgres.py \
  ccs_core.py knowledge_ai.py streamlit_app.py streamlit_v03.py

python -m unittest discover -s tests -v
```

Die GitHub-Actions-CI startet zusätzlich einen echten `pgvector/pgvector:pg16`-Service und prüft Migrationen, Repository, Tenant-Isolation, RBAC, Hybrid Retrieval, Service-Layer und SQLite→PostgreSQL-Migration.

## Noch offen bis 0.3.0-mvp

- produktionsfähiger semantischer Embedding-Provider mit freigegebenem Modell
- Modell-/Re-Embedding-Strategie für Modellwechsel
- REST-API als zweiter Client neben Streamlit
- produktives Backup-/Restore-Verfahren
- SSO/OIDC / Microsoft Entra ID
- OCR und Dateischadcodeprüfung
- Encryption-at-Rest-/Secrets-Betriebskonzept
- Windows-Paketierung, Installer, Code Signing und Update-Service
- Datenschutz- und produktive Betriebsfreigabe

0.3.0-dev bleibt bis zum Abschluss dieser definierten MVP-Gates bewusst eine Entwicklungs-/Pilotversion.
