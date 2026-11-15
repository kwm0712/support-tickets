# COMPELEC ONE Business – technischer Abnahmebericht

**Prüfdatum:** 15.11.2026  
**Repository:** `kwm0712/support-tickets`  
**Arbeitsbranch:** `feature/compelec-one-business-v2.0-oidc`  
**Pull Request:** [#15 – V2.0 OIDC identity foundation](https://github.com/kwm0712/support-tickets/pull/15)  
**Prüfcommit:** `191f212af94c473934b8fbe79b3b261bbabd9539`  
**CI-Nachweis:** [GitHub Actions Run #303](https://github.com/kwm0712/support-tickets/actions/runs/43717076654)

## 1. Ergebnis in einem Satz

Der aktuelle Stand ist ein **technisch erfolgreich gebauter und automatisiert geprüfter Windows-Testkandidat auf Basis 1.2.0-dev**. Er ist ausdrücklich **keine freigegebene COMPELEC ONE Business V2.0 Enterprise-Version**.

## 2. Nachgewiesene Prüfungen

| Prüfkriterium | Nachweis | Ergebnis |
|---|---|---|
| Python-Quellcode | Kompilierung im CI-Lauf #303 | BESTANDEN |
| Unit- und Integrationstests | 84 Tests, Run #303 | BESTANDEN |
| PostgreSQL | PostgreSQL 16 / pgvector Service in CI | BESTANDEN |
| Backup-Integrität | SHA-256-Prüfung und Fehlerfalltest | BESTANDEN |
| Reeller Backup-/Restore-Pfad | `pg_dump` / `pg_restore` Roundtrip-Test | BESTANDEN |
| Windows-Build | PyInstaller + Inno Setup 6.7.1 | BESTANDEN |
| Stille Installation | Windows Server 2025 CI-Runner, Prozess-Exitcode und EXE-Prüfung | BESTANDEN |
| Deinstallation | Uninstaller-Exitcode und Entfernung der Programmdatei | BESTANDEN |
| Artefaktbereitstellung | Windows-Testartefakt durch Actions hochgeladen | BESTANDEN |

Der CI-Lauf ist vollständig grün. Die Installationsprüfung erfolgte auf **Windows Server 2025**. Das ersetzt keinen Abnahmetest auf einem sauberen Windows-11-x64-Arbeitsplatz.

## 3. Aktuell erzeugte Lieferobjekte

Der CI-Lauf #303 hat aus dem Prüfcommit folgende Artefakte erzeugt und hochgeladen:

- Windows Setup EXE: `COMPELEC-ONE-Business-Setup-1.2.0-dev.exe`
- Portables Windows-Paket: `COMPELEC-ONE-Business-1.2.0-dev-portable.zip`
- Prüfsummenmanifest: `SHA256SUMS.txt`
- getestetes Source-Bundle

**Wichtig:** Die Artefakte sind Test-/Entwicklungsartefakte. Sie tragen nicht die Version 2.0.0 und sind nicht digital mit einem öffentlich vertrauenswürdigen Code-Signing-Zertifikat signiert.

## 4. Verbleibende Enterprise-Abnahme-Gates

| Gate | Noch erforderlicher Nachweis | Status |
|---|---|---|
| G0 – Release-Lieferkette | Version 2.0.0, konsistente Metadaten, finaler Build, Manifestprüfung, Tag/Release, Windows-11-Abnahme und Signierungsentscheidung | OFFEN |
| G1 – Identität | Reale Entra-ID-Test-App bzw. freigegebener IdP, Ende-zu-Ende-Token-/Session-/Proxy-Abnahme und dokumentierte Rollenabbildung | OFFEN |
| G2 – Mandantensicherheit | Vollständiger Ende-zu-Ende-Nachweis über UI/API/Service/DB in der vorgesehenen Zielumgebung; CI-RLS-Tests allein reichen nicht | TEILWEISE |
| G3 – KI/Retrieval | Semantisches Produktions-Embedding ist nicht festgelegt. Der lokale Hash-Provider ist nur ein deterministischer Testprovider. Anbieter, Modell, Datenregion und Datenschutzfreigabe fehlen. | OFFEN |
| G4 – Betrieb/Recovery | CI-Roundtrip ist bestanden. Separater Restore in der vorgesehenen Betriebsumgebung sowie verbindliche RPO-/RTO-Werte und Betriebsfreigabe fehlen. | TEILWEISE |
| G5 – Security/Datenschutz/Lizenz | Ed25519-Prüfcode und automatisierte Tests vorhanden. Ausstellerschlüssel-Verwahrung, echte mandantengebundene Lizenz, Security-/Datenschutzreview und Geschäftsführungsabnahme fehlen. | TEILWEISE |

## 5. Kosten- und Sicherheitsleitplanken

- Keine neuen kostenpflichtigen Dienste, Lizenzen, Cloud- oder API-Angebote ohne ausdrückliche Freigabe.
- Keine externen generativen KI- oder Embedding-Aufrufe als stillschweigende Voraussetzung.
- Keine Secrets, privaten Lizenzschlüssel oder Zugangsdaten im Repository.
- Private Lizenz-Ausstellerschlüssel bleiben außerhalb von Git und CI.
- Kein Commit, Merge oder sonstige Änderung an `main`.
- Keine Produktionsfreigabe allein aufgrund eines grünen CI-Laufs.

## 6. Abnahmeregel

Eine Enterprise-Freigabe wird erst erteilt, wenn alle für den konkreten Betrieb relevanten G0–G5-Nachweise erbracht, dokumentiert und durch die verantwortlichen Stellen akzeptiert sind. Abweichungen benötigen eine dokumentierte Risikoentscheidung mit Verantwortlichem und Ablaufdatum.

**Aktuelle Entscheidung: NO-GO für Produktion / GO für kontrollierten technischen Test.**
