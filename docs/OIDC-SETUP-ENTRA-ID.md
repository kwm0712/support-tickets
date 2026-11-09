# COMPELEC ONE Business V2.0 – OIDC-/Microsoft-Entra-ID-Konfiguration

## Zweck und Status

Die REST-API kann OIDC-Bearer-Tokens validieren. Der Provider prüft RS256-Signatur über den konfigurierten HTTPS-JWKS-Endpunkt, Issuer, Audience, Ablaufzeit, Ausstellungszeit und Subject. Rollen und externe Mandanten werden ausschließlich über explizite Allowlist-Mappings übernommen.

**Wichtig:** Der Codepfad ist noch keine produktive Entra-ID-Anbindung. Dafür müssen App-Registrierung, App-Rollen, Testbenutzer und reale Tokens in der Zielumgebung eingerichtet und abgenommen werden. Der aktuelle OIDC-Provider ist zunächst in der REST-API verdrahtet. Die Streamlit-Oberfläche verwendet weiterhin lokale Anmeldung; ein durchgängiger OIDC-/Reverse-Proxy-Login für die Oberfläche ist ein offenes V2.0-Release-Gate. Die Anwendung enthält derzeit keinen vollständigen interaktiven Login-Client; der API-aufrufende Client muss ein gültiges Bearer-Token beschaffen.

## 1. Entra-App-Registrierung

Für die API eine dedizierte App-Registrierung anlegen:

1. Unterstützte Kontotypen zunächst auf das Compelec-Verzeichnis beschränken.
2. Unter „Eine API verfügbar machen“ eine Application-ID-URI festlegen, z. B. `api://<APPLICATION-CLIENT-ID>`.
3. Drei App-Rollen definieren:
   - Anzeigename: COMPELEC Administrator; Wert: `Compelec.Admin`
   - Anzeigename: COMPELEC Support; Wert: `Compelec.Support`
   - Anzeigename: COMPELEC Leser; Wert: `Compelec.ReadOnly`
4. Zulässige Mitgliedstypen: Benutzer/Gruppen.
5. Benutzer oder Gruppen den App-Rollen zuweisen.
6. Für den aufrufenden Client die erforderliche API-Berechtigung/Scope konfigurieren und Administratorzustimmung erteilen, sofern erforderlich.

Die tatsächlichen Rollenwerte müssen exakt mit `CCS_OIDC_ROLE_MAP` übereinstimmen.

## 2. Erforderliche Werte

Aus der App-Registrierung und dem Entra-Verzeichnis übernehmen:

| Konfiguration | Wert |
|---|---|
| `CCS_OIDC_ISSUER` | `https://login.microsoftonline.com/<TENANT-ID>/v2.0` |
| `CCS_OIDC_AUDIENCE` | Exakter Audience-Wert des ausgestellten API-Tokens, z. B. `api://<APPLICATION-CLIENT-ID>` |
| `CCS_OIDC_JWKS_URL` | `https://login.microsoftonline.com/<TENANT-ID>/discovery/v2.0/keys` |
| `CCS_OIDC_ROLE_CLAIM` | `roles` |
| `CCS_OIDC_TENANT_CLAIM` | `tid` |
| `CCS_OIDC_USERNAME_CLAIM` | `preferred_username` |

Issuer und Audience müssen bytegenau zu den Claims des Tokens passen. Nicht aus der App-ID ableiten, sondern mit einem real ausgestellten Access Token prüfen.

## 3. Rollen- und Mandantenmapping

Beispiel für einen internen Compelec-Mandanten:

```dotenv
CCS_OIDC_ROLE_MAP={"Compelec.Admin":"admin","Compelec.Support":"agent","Compelec.ReadOnly":"viewer"}
CCS_OIDC_TENANT_MAP={"<TENANT-GUID-AUS-CLAIM-tid>":"compelec"}
```

Das Tenant-Mapping ist eine Sicherheitsgrenze. Ein gültig signiertes Token eines nicht zugeordneten IdP-Mandanten wird abgewiesen. Die externe Tenant-GUID wird nicht ungeprüft als interner Datenbank-Mandant verwendet.

Für weitere Organisationen muss jede externe Tenant-GUID ausdrücklich auf einen internen Mandantenschlüssel abgebildet und organisatorisch freigegeben werden.

## 4. Produktionskonfiguration

```dotenv
CCS_IDENTITY_MODE=oidc
CCS_OIDC_ISSUER=https://login.microsoftonline.com/<TENANT-ID>/v2.0
CCS_OIDC_AUDIENCE=api://<APPLICATION-CLIENT-ID>
CCS_OIDC_JWKS_URL=https://login.microsoftonline.com/<TENANT-ID>/discovery/v2.0/keys
CCS_OIDC_ROLE_CLAIM=roles
CCS_OIDC_TENANT_CLAIM=tid
CCS_OIDC_USERNAME_CLAIM=preferred_username
CCS_OIDC_ROLE_MAP={"Compelec.Admin":"admin","Compelec.Support":"agent","Compelec.ReadOnly":"viewer"}
CCS_OIDC_TENANT_MAP={"<TENANT-ID>":"compelec"}
```

Keine Client-Secrets, Zertifikate oder privaten Schlüssel in `.env.example`, Quellcode, Tickets oder GitHub-Commits ablegen. Geheimnisse gehören in einen geeigneten Secret Store bzw. in die geschützte Laufzeitkonfiguration.

## 5. Abnahmetests mit echten Tokens

- [ ] Token von der vorgesehenen Entra-App beziehen.
- [ ] `iss` entspricht exakt `CCS_OIDC_ISSUER`.
- [ ] `aud` entspricht exakt `CCS_OIDC_AUDIENCE`.
- [ ] Signatur wird über den HTTPS-JWKS-Endpunkt verifiziert.
- [ ] Abgelaufenes Token wird mit HTTP 401 abgewiesen.
- [ ] Falsche Signatur, falscher Issuer oder falsche Audience werden abgewiesen.
- [ ] Fehlende oder unbekannte App-Rolle wird abgewiesen.
- [ ] Nicht zugeordnete `tid` wird abgewiesen.
- [ ] Jede Rolle erhält ausschließlich die vorgesehenen COMPELEC-Berechtigungen.
- [ ] Token und sensible Claims erscheinen nicht in Logs.

## 6. Einschränkungen

- Der Provider akzeptiert derzeit ausschließlich RS256.
- Die OIDC-Konfiguration verwendet einen fest konfigurierten Issuer. Der initiale Produktivbetrieb ist daher auf den freigegebenen IdP-Tenant ausgerichtet.
- OIDC ersetzt nicht die Datenbank-RLS; beide Sicherheitsgrenzen müssen unabhängig voneinander bestehen.
- Die echte Entra-Abnahme, Datenschutzfreigabe und Client-Integration bleiben separate V2.0-Release-Gates.
