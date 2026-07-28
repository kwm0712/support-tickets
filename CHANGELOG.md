# Changelog

## 0.1.0-mvp

- Streamlit-Demotemplate durch CCS Agent Support Oberfläche ersetzt
- SQLite-Persistenz für Benutzer, Tickets, Wissen und Audit ergänzt
- Rollen `admin`, `agent` und `viewer` eingeführt
- sichere Passwort-Hashes mit PBKDF2-HMAC ergänzt
- Ticketanlage und Ticketbearbeitung umgesetzt
- lokale Wissensbasis und kontrollierter Antwortentwurf umgesetzt
- Demo-/Lizenzstatus über Umgebungsvariablen ergänzt
- Smoke-Tests und Pilot-Abnahmecheckliste ergänzt

### Bekannte Grenzen

- noch kein externer LLM-Provider
- noch kein PostgreSQL/pgvector
- noch keine Mandantenfähigkeit oder SSO-Anbindung
- noch kein Windows-Installer, keine Code-Signierung und kein Update-Service
