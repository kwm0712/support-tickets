# Pilot-Checkliste CCS Agent Support MVP

## Technische Prüfung

- [ ] Python 3.11 oder neuer vorhanden
- [ ] Virtuelle Umgebung erstellt
- [ ] Abhängigkeiten installiert
- [ ] Anwendung startet ohne Fehler
- [ ] SQLite-Datenbank wird im konfigurierten Datenverzeichnis angelegt
- [ ] Lokale Daten und Geheimnisse werden nicht in Git eingecheckt

## Funktionstest

- [ ] Anmeldung als Administrator erfolgreich
- [ ] Anmeldung als Support-Agent erfolgreich
- [ ] Viewer kann keine Daten verändern
- [ ] Ticket kann angelegt werden
- [ ] Ticketstatus, Priorität und Bearbeiter können geändert werden
- [ ] Wissenssuche liefert nachvollziehbare Treffer
- [ ] Antwortentwurf verweist ausschließlich auf lokale Wissenseinträge
- [ ] Audit protokolliert Anmeldung, Änderungen und Antwortentwürfe
- [ ] Demo- und Lizenzmodus werden korrekt angezeigt

## Freigabegrenzen

- [ ] Keine produktiven Kundendaten ohne Datenschutz- und Sicherheitsfreigabe
- [ ] Standardkennwörter vor Pilotstart geändert
- [ ] Verantwortlicher Pilot-Administrator benannt
- [ ] Datensicherung und Wiederherstellung getestet
- [ ] Offene Punkte für PostgreSQL, RAG, SSO und Installer dokumentiert

## Abnahmekriterium MVP

Der MVP gilt als pilotfähig, wenn alle technischen und funktionalen Prüfpunkte erfüllt sind, keine kritischen Fehler offen sind und die Freigabegrenzen schriftlich bestätigt wurden.
