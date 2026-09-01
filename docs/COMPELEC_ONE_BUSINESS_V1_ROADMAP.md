# COMPELEC ONE Business – Entwicklung bis V1.x

## Zielbild
COMPELEC ONE Business wird von der V0.4-Serviceplattform zu einer produktionsorientierten V1-Linie weiterentwickelt. Die Versionen 0.5 bis 0.9 sind Reifestufen; V1.0 ist die technische Produktionsbaseline.

## V0.5 – Production Configuration
- zentrale, fail-closed Produktionskonfiguration
- PostgreSQL-Pflicht
- explizite Mandantenkonfiguration
- Verbot des lokalen Hash-Embedding-Providers in Produktion

## V0.6 – Operations & Health
- getrennte Liveness- und Readiness-Endpunkte
- Datenbank-Healthcheck
- sichtbarer Environment-, Identity- und Embedding-Status

## V0.7 – Stable REST API
- stabile `/v1`-Servicegrenze
- Tickets, Knowledge, Documents, Metrics, Audit und Assistant
- Pydantic-Validierung und Größenlimits
- RBAC/Tenant/Privacy bleiben im SupportService erzwungen

## V0.8 – Enterprise Identity Boundary
- austauschbarer IdentityProvider bleibt Pflichtgrenze
- Trusted-Header-Modus für vorgeschaltetes SSO/IAP
- direkte OIDC/JWT-Verifikation wird als Provider-Erweiterung integriert, sobald Ziel-IdP festgelegt ist

## V0.9 – Release Candidate
- vollständige Unit-/PostgreSQL-Integrationstests
- Windows-Build in CI
- Setup EXE, Portable ZIP, SHA-256
- Backup/Restore- und Re-Embedding-Prozeduren
- Smoke-Test für REST und Windows-Laufzeit

## V1.0 – Production Baseline
V1.0 gilt technisch als freigabefähig, wenn alle CI-Gates grün sind, ein realer Windows-Smoke-Test erfolgreich war, ein produktiver Embedding-Provider konfiguriert ist, Backup/Restore getestet wurde und der vorgesehene Identity-/SSO-Betriebsweg dokumentiert ist.

## Noch externe Release-Gates
- konkreter produktiver Embedding-Anbieter/Modellfreigabe
- konkreter SSO/Identity Provider bzw. Reverse-Proxy/IAP
- Code-Signing-Zertifikat für den Windows-Installer
- produktive PostgreSQL-Zielumgebung und Restore-Test

Diese Punkte sind keine Architekturblocker, aber vor einer echten Kunden-Produktivfreigabe verbindlich.
