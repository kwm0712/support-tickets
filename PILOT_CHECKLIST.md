# Pilot-Checkliste CCS Agent Support 0.2.0-mvp

## Technische Prüfung

- [ ] Python 3.12 vorhanden
- [ ] virtuelle Umgebung erstellt
- [ ] Abhängigkeiten installiert
- [ ] Anwendung startet ohne Fehler
- [ ] SQLite-Datenbank wird im konfigurierten Datenverzeichnis angelegt
- [ ] lokale Daten, hochgeladene Dokumente und Geheimnisse werden nicht in Git eingecheckt
- [ ] GitHub-Actions-CI ist erfolgreich
- [ ] Backup und Wiederherstellung der SQLite-Datenbank sind getestet

## Benutzer und Tickets

- [ ] Anmeldung als Administrator erfolgreich
- [ ] Anmeldung als Support-Agent erfolgreich
- [ ] Viewer kann keine Daten verändern
- [ ] Standardkennwörter wurden geändert
- [ ] Ticket kann angelegt werden
- [ ] Ticketstatus, Priorität und Bearbeiter können geändert werden
- [ ] Audit protokolliert Anmeldung und Ticketänderungen

## Wissens-Governance

- [ ] Wissensartikel kann als Entwurf angelegt werden
- [ ] Entwurfsartikel erscheint nicht im KI-Antwortentwurf
- [ ] Artikel kann freigegeben und abgelehnt werden
- [ ] Datenschutzstufen `public`, `internal`, `confidential` werden korrekt gefiltert
- [ ] vertrauliche Inhalte erscheinen nicht bei einer internen oder öffentlichen Anfrage
- [ ] Freigabeänderungen werden im Audit protokolliert

## Dokumentenimport und RAG-Vorbereitung

- [ ] TXT-Import funktioniert
- [ ] PDF mit vorhandenem Text wird extrahiert
- [ ] DOCX-Import funktioniert
- [ ] identische Datei wird durch SHA-256-Dublettenprüfung abgewiesen
- [ ] importiertes Dokument erhält zunächst den Status `draft`
- [ ] Dokumentsegmente werden erst nach Freigabe als Evidenz verwendet
- [ ] gescannte PDFs ohne Text werden als nicht verwertbar erkannt
- [ ] Quelldatei, Datenschutzstufe und Prüfer sind nachvollziehbar

## KI-Assistent und Nachvollziehbarkeit

- [ ] ausschließlich Provider `local-evidence` ist aktiv
- [ ] unbekannter oder externer Provider wird abgewiesen
- [ ] Antwortentwurf verwendet ausschließlich freigegebene Quellen
- [ ] verwendete Quellen werden in der Oberfläche angezeigt
- [ ] Frage, Antwort, Provider, Datenschutzstufe und Quellenreferenzen werden protokolliert
- [ ] Antwort enthält einen verbindlichen fachlichen Kontrollhinweis

## Freigabegrenzen

- [ ] keine produktiven Kundendaten ohne Datenschutz- und Sicherheitsfreigabe
- [ ] verantwortlicher Pilot-Administrator und fachlicher Freigeber sind benannt
- [ ] Aufbewahrung und Löschung importierter Dokumente sind geregelt
- [ ] Dateischadcodeprüfung ist organisatorisch gelöst oder Upload bleibt auf Testdateien beschränkt
- [ ] offene Punkte für PostgreSQL, pgvector, SSO, OCR und Installer sind dokumentiert

## Abnahmekriterium

Version 0.2.0-mvp gilt als intern pilotfähig, wenn alle technischen und funktionalen Prüfpunkte erfüllt sind, keine kritischen Fehler offen sind und Datenschutz-, Sicherheits- sowie Betriebsgrenzen schriftlich bestätigt wurden. Eine Produktiv- oder Kundenfreigabe ist damit noch nicht verbunden.
