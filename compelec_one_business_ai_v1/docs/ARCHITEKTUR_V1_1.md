# COMPELEC ONE – Business AI V1.1: Architektur- und Datenbankgrundlage

## Zielbild
Support, Vertrieb, Telefonie und E-Mail verwenden eine gemeinsame Kundenhistorie. Jede Interaktion erhält einen Kanal und wird einem Kunden und Mandanten zugeordnet. Spezialisierte Fachdaten (Ticket, Telefonnotiz, E-Mail-Entwurf) verweisen auf diese zentrale Interaktion.

## Datenmodell
- Mandanten und Benutzer mit Rollen
- Kundenstamm je Mandant
- Zentrale Interaktionstabelle für Support, Vertrieb, Telefon und E-Mail
- Supportvorgänge mit Status, Priorität und Zuständigkeit
- Telefon-Details mit Rückrufkennzeichen
- E-Mail-Entwürfe mit explizitem Freigabestatus
- Audit-Protokoll für nachvollziehbare Aktionen

## Mandantentrennung
Das SQL-Grundschema verwendet zusammengesetzte Fremdschlüssel mit tenant_id, damit fachliche Verknüpfungen nicht versehentlich mandantenübergreifend erfolgen. Row-Level Security (RLS) ergänzt diese Trennung. Die Anwendung muss den Mandantenkontext innerhalb jeder Transaktion setzen, beispielsweise mit SET LOCAL app.tenant_id = '123'. Die Datenbankverbindung darf nicht mit einer Rolle betrieben werden, die RLS umgeht (insbesondere kein Tabellen-Owner und kein BYPASSRLS).

## Sicherheits- und Betriebsentscheidungen
- Keine Passwörter im Fachschema speichern. Authentifizierung und sichere Passwort-/SSO-Verwaltung werden separat festgelegt.
- E-Mail-Versand bleibt hinter einem Freigabeschritt; ein Entwurf ist kein Versandauftrag.
- Telefonie- und E-Mail-Inhalte sind personenbezogene bzw. vertrauliche Daten: Aufbewahrung, Löschung, Berechtigungen und Protokollumfang müssen vor Pilotbetrieb abgestimmt werden.
- Auditdaten dürfen nicht stillschweigend durch normale Fachbenutzer verändert werden.
- Backups, Wiederherstellungstests, TLS, Secret-Verwaltung und Berechtigungskonzept sind vor Produktivbetrieb zwingend.

## Technischer Prüfstatus
Das Schema wurde am 14.11.2026 in einer isolierten PostgreSQL-16-Instanz innerhalb von GitHub Actions erfolgreich eingespielt. Der separate RLS-Test mit zwei künstlichen Testmandanten war erfolgreich. Auch die Python-Syntax- und Abhängigkeitsprüfung war erfolgreich.
Prüflauf: https://github.com/kwm0712/support-tickets/actions/runs/43607430856

Diese CI-Prüfung ist ein reproduzierbarer technischer Basistest, aber keine Freigabe für den Produktivbetrieb. Es wurden keine produktiven Datenbanken angelegt oder verändert. Die Streamlit-Anwendung verwendet weiterhin keine PostgreSQL-Verbindung und speichert Daten nur im Sitzungsspeicher.

## Nächste technische Schritte
1. Datenzugriffsschicht mit transaktionsgebundenem Mandantenkontext implementieren; ohne authentifizierten Benutzer keinen Datenbankzugriff zulassen.
2. Automatisierte Tests für Repository-Funktionen und RLS ergänzen.
3. Erst nach geklärtem Authentifizierungs- und Rollenmodell die Streamlit-Oberfläche schrittweise auf persistente Speicherung umstellen.
4. Backups, Wiederherstellung, Datenschutz und Audit-Protokoll fachlich abnehmen.
5. Erst danach Integrationen (STARFACE, IMAP/SMTP bzw. Microsoft 365) anbinden.
