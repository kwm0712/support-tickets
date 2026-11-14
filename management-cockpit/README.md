# COMPELEC ONE – Management Cockpit V0.4

Lokales, kostenfreies Management-Cockpit für GitHub-Repository- und CI/CD-Transparenz.

## Voraussetzungen
- Windows 10/11 oder Linux
- Python 3.10 oder neuer
- Internetzugang für die GitHub-API
- Für öffentliche Repositories kein GitHub-Token erforderlich

## Start unter Windows
1. ZIP/Repository lokal entpacken.
2. Im Ordner `management-cockpit` ein Terminal öffnen.
3. Optional eine virtuelle Umgebung erstellen:
   `py -m venv .venv`
4. Aktivieren:
   `.venv\Scripts\activate`
5. Abhängigkeiten installieren:
   `py -m pip install -r requirements.txt`
6. Starten:
   `py -m streamlit run cockpit.py`

Die Oberfläche öffnet sich üblicherweise unter http://localhost:8501.

## Konfiguration
Standardrepository: `kwm0712/support-tickets`.
Alternativ Umgebungsvariable `COMPELEC_GITHUB_REPO` setzen oder Repository in der Seitenleiste ändern.

Ein GitHub-Token ist optional und wird nur im laufenden Prozess verwendet. Nicht in Quellcode oder Konfigurationsdateien eintragen.

## Umfang V0.4
- Repository-Metadaten
- offene Pull Requests und Draft-Kennzeichnung
- letzte GitHub-Actions-Läufe
- Job- und fehlgeschlagene Schrittübersicht
- Release-Gate-Checkliste
- JSON-Managementbericht

## Grenzen
- Die Anwendung liest GitHub-Daten; sie verändert keine Repositories, PRs oder Workflows.
- Release-Gate-Häkchen werden nur im laufenden Streamlit-Sitzungsspeicher gehalten.
- Workflow-Logs werden nicht automatisch vollständig interpretiert; die Detailansicht verlinkt auf GitHub.
- GitHub-API-Limits gelten. Ein optionaler Token erhöht üblicherweise das verfügbare Limit.
- Keine Datenbank, kein Hosting, keine kostenpflichtigen APIs und keine externen Dienste außer der GitHub-API.

## Sicherheit
Keine Zugangsdaten im Repository speichern. Für private Repositories einen persönlichen Token mit minimal erforderlichen Leserechten verwenden und nach Gebrauch aus dem Eingabefeld entfernen.
