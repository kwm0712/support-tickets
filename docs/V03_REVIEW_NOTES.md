# V0.3 Review Notes

Diese Ausbaustufe ist als gestapelter Architektur-PR auf Basis von `agent/ccs-agent-support-mvp` gedacht.

## Review-Fokus

- zentrale RBAC- und Privacy-Policy statt reiner UI-Sperren
- strikte Tenant-Grenzen
- PostgreSQL-/pgvector-Schema
- Repository-Adapter und race-sichere Ticketnummern
- CI-Validierung gegen echten PostgreSQL/pgvector-Service
- klare Abgrenzung zwischen bereits umgesetzter Architektur und noch offener vollständiger Verdrahtung

## Nicht als abgeschlossen betrachten

Die bestehende Streamlit-Anwendung nutzt in diesem Zwischenstand weiterhin die 0.2-SQLite-Pfade. Der neue PostgreSQL-Repository-Layer ist die Zielbasis und muss im nächsten Schritt in die fachlichen Services eingebunden werden, bevor V0.3 als MVP freigegeben werden kann.
