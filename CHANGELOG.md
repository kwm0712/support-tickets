# Changelog

## 0.2.0-mvp

- additive Datenbankmigration für Knowledge Governance ergänzt
- Freigabestatus `draft`, `approved`, `rejected` eingeführt
- Datenschutzstufen `public`, `internal`, `confidential` eingeführt
- TXT-, PDF- und DOCX-Import ergänzt
- SHA-256-Dublettenprüfung für Dokumente ergänzt
- Dokumentsegmentierung als lokale RAG-Vorbereitung umgesetzt
- quellengebundene Evidenzsuche für Artikel und Dokumentsegmente ergänzt
- Provider-Abstraktion eingeführt; ausschließlich `local-evidence` freigegeben
- Assistenzläufe mit Frage, Antwort, Provider, Datenschutzstufe und Quellen protokolliert
- Oberfläche um Dokumentenprüfung, Governance-Kennzahlen und Quellenanzeige erweitert
- Unit-Tests für Freigabelogik, Datenschutzfilter, Dokumentabruf und Provider-Sperre ergänzt
- GitHub-Actions-CI für Kompilierung und Tests ergänzt

### Bekannte Grenzen

- lexikalische Suche statt Vektor-Embeddings
- PDF-Import ohne OCR für gescannte Seiten
- SQLite statt PostgreSQL/pgvector
- kein externer oder lokal generativer Modellprovider
- noch keine Mandantenfähigkeit, SSO-Anbindung oder Dateischadcodeprüfung
- noch kein Windows-Installer, keine Code-Signierung und kein Update-Service

## 0.1.0-mvp

- Streamlit-Demotemplate durch CCS Agent Support Oberfläche ersetzt
- SQLite-Persistenz für Benutzer, Tickets, Wissen und Audit ergänzt
- Rollen `admin`, `agent` und `viewer` eingeführt
- sichere Passwort-Hashes mit PBKDF2-HMAC ergänzt
- Ticketanlage und Ticketbearbeitung umgesetzt
- lokale Wissensbasis und kontrollierter Antwortentwurf umgesetzt
- Demo-/Lizenzstatus über Umgebungsvariablen ergänzt
- Smoke-Tests und Pilot-Abnahmecheckliste ergänzt
