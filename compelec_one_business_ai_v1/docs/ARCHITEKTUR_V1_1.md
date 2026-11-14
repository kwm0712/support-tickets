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

## Status
Dies ist ein Architekturentwurf und ein SQL-Schema zur Prüfung. Es wurde nicht gegen eine laufende PostgreSQL-Instanz ausgeführt. Es wurden keine Datenbank angelegt, keine Zugangsdaten hinterlegt und keine produktiven Daten verändert.

## Nächste technische Schritte
1. SQL in einer isolierten PostgreSQL-Testinstanz ausführen und Migrationstests ergänzen.
2. Rollenmodell und RLS-Verhalten mit zwei Testmandanten nachweisen.
3. Datenzugriffsschicht implementieren und Transaktionskontext erzwingen.
4. Streamlit-Demonstrator schrittweise auf persistente Speicherung umstellen.
5. Erst danach Integrationen (STARFACE, IMAP/SMTP bzw. Microsoft 365) anbinden.
