# CCS Agent Support V0.3 – Zielarchitektur

## Architekturprinzip

V0.3 trennt Frontend, Authorization, fachliche Services, Repository-Zugriffe und AI-/Embedding-Provider. Streamlit bleibt Präsentationsschicht und darf langfristig keine Sicherheitsentscheidung allein erzwingen.

```text
Streamlit UI
    |
    v
Application / Service Layer
    |
    +-- UserContext / TenantContext
    +-- RBAC / Privacy Policy
    +-- Ticket Service
    +-- Knowledge Service
    +-- Assistant Service
    |
    +-------------------+
    |                   |
    v                   v
Repository Layer     Provider Layer
    |                +-- EmbeddingProvider
    |                +-- AssistantProvider
    v
PostgreSQL + pgvector
```

## Sicherheitsregeln

1. Jede fachliche Ressource gehört genau zu einem Mandanten.
2. Kein Repository-Aufruf darf Daten eines anderen Mandanten zurückgeben.
3. Rollenberechtigungen werden zentral geprüft und nicht nur über ausgeblendete UI-Elemente umgesetzt.
4. Datenschutzstufen werden an die Benutzerrolle gekoppelt.
5. Externe generative Provider bleiben in V0.3 standardmäßig deaktiviert.
6. Embeddings und Retrieval müssen Modellkennung, Dimension und Evidenzbezug nachvollziehbar halten.
7. Audit-Ereignisse müssen Mandant, Benutzer, Aktion, Ressource und optional eine Correlation-ID erfassen.

## Rollenmodell V0.3

### viewer

- Tickets lesen
- freigegebenes Wissen lesen
- Dokumente lesen
- Assistent nur bis Datenschutzstufe `public`

### agent

- Rechte von `viewer`
- Tickets bearbeiten
- Assistent bis Datenschutzstufe `internal`

### admin

- Rechte von `agent`
- Wissen erstellen und freigeben
- Dokumente importieren und freigeben
- Audit lesen
- Mandantenadministration
- Assistent bis Datenschutzstufe `confidential`

## PostgreSQL-Zielmodell

Alle operativen Kerntabellen besitzen `tenant_key`. Dokumentsegmente erhalten optionale pgvector-Embeddings; Assistant-Evidenzen werden relational gespeichert. Ticketnummern werden nicht mehr über `MAX(id)+1`, sondern über PostgreSQL-Sequenzen erzeugt.

## Migrationsstrategie

- 0.2 bleibt SQLite-basierter Pilotstand.
- 0.3 führt versionierte PostgreSQL-Migrationen ein.
- Vor 0.3-MVP muss ein einmaliger Export-/Importpfad für 0.2-Pilotdaten ergänzt werden.
- Produktive Migrationen dürfen nicht während eines normalen UI-Starts implizit per `ALTER TABLE` erfolgen.

## Nächster Implementierungsschritt

Die vorhandenen Funktionen aus `ccs_core.py` und `knowledge_ai.py` werden schrittweise hinter Service-/Repository-Schnittstellen verschoben. Erst danach wird SQLite zur reinen Demo-/Testoption und PostgreSQL zur primären Betriebsdatenbank.
