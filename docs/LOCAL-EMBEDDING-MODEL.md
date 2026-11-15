# COMPELEC ONE Business – Lokales Embedding-Modell

Stand: 15.11.2026  
Status: Implementierung auf Feature-Branch; Modell- und Zielsystemabnahme noch offen.

## Festgelegte Architektur

- Provider: FastEmbed 0.9.1 (ONNX Runtime, CPU-fähig)
- Modell: `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`
- Vektordimension: 384
- Modelllizenz laut FastEmbed-Modellkatalog: Apache-2.0
- Modellgröße laut Katalog: ca. 0,22 GB
- Speicherung: PostgreSQL 16 / pgvector
- Laufzeit: ausschließlich lokaler Modellcache; `local_files_only=True`
- Kein API-Schlüssel, kein Embedding-Endpunkt, keine Cloud-Inferenz

Das Modell ist multilingual und damit für deutschsprachige Support- und Unternehmensdokumente geeignet. Die Eignung für den konkreten COMPELEC-Datenbestand muss durch einen kuratierten Retrieval-Test nachgewiesen werden; die Modellwahl ist daher zunächst eine technische Baseline und keine behauptete Qualitätsabnahme.

## Einmalige Modellbereitstellung

Die Bereitstellung erfolgt bewusst getrennt vom normalen Anwendungsstart. Nur dieser administrative Schritt lädt Modell-Dateien herunter.

PowerShell (im Projektverzeichnis):

```powershell
python -m pip install -r requirements.txt
$env:CCS_EMBEDDING_CACHE_DIR = "C:\ProgramData\Compelec\COMPELEC-ONE\models\embeddings"
python scripts/provision_local_embedding.py
```

Das Skript erzeugt `compelec-embedding-manifest.json` mit Modellkennung, Provider-Version, Dimension und SHA-256-Prüfsummen der bereitgestellten Cache-Dateien. Das Manifest ist zusammen mit dem Modellcache zu sichern und in die Deployment-Dokumentation aufzunehmen.

## Produktionskonfiguration

```ini
CCS_ENVIRONMENT=production
CCS_EMBEDDING_PROVIDER=local-fastembed
CCS_EMBEDDING_CACHE_DIR=C:\ProgramData\Compelec\COMPELEC-ONE\models\embeddings
```

Der Modellcache muss vor dem Produktivstart vorhanden und für das Dienstkonto lesbar sein. Fehlt das Modell, startet der Provider nicht. Der Produktivpfad lädt keine Modelle nach und fällt nicht auf einen externen Dienst zurück.

Produktivkonfigurationen mit Hash- oder externem Embedding-Provider werden abgewiesen. Der bisherige Hash-Provider bleibt ausschließlich für isolierte Architektur- und Testläufe verfügbar.

## Datenbank- und Migrationshinweis

Die pgvector-Spalten sind untypisiert (`vector`); die tatsächliche Dimension und Modellkennung werden je Datensatz gespeichert. Der Retrieval-Code berücksichtigt die Dimension. Vor dem Produktiveinsatz müssen bestehende Hash-Vektoren neu berechnet werden. Ein Modellwechsel erfordert einen vollständigen Re-Embedding-Lauf und eine dokumentierte Kontrolle, dass keine gemischten Modellräume unbemerkt miteinander verglichen werden.

## Abnahmecheckliste

- [ ] FastEmbed-Version im Build reproduzierbar installiert
- [ ] Modellcache offline auf Zielsystem bereitgestellt
- [ ] SHA-256-Manifest geprüft und archiviert
- [ ] Modellstart ohne Netzwerkzugriff nachgewiesen
- [ ] Embedding-Dimension 384 für Dokumente und Suchanfragen bestätigt
- [ ] Re-Embedding aller freigegebenen Artikel und Dokument-Chunks abgeschlossen
- [ ] Keine Altvektoren mit 64 Dimensionen im aktiven Retrieval
- [ ] Deutschsprachiger, fachlich kuratierter Retrieval-Datensatz ausgewertet
- [ ] Recall@5 / MRR und Fehlertreffer dokumentiert
- [ ] Mandantentrennung und Datenschutzstufen bei semantischer Suche negativ getestet
- [ ] Windows-11-Zielinstallation mit bereitgestelltem Modellcache abgenommen

## Quellen / Lizenznachweise

- FastEmbed Modellkatalog und Größen-/Lizenzangaben: https://qdrant.github.io/fastembed/examples/Supported_Models/
- FastEmbed lokale Ausführung und CPU-/ONNX-Architektur: https://qdrant.tech/documentation/tutorials-basics/generate-embeddings-fastembed/
- Apache-2.0-Modelllizenz laut FastEmbed-Modellkatalog; Lizenzdatei des konkret provisionierten Modell-Snapshots bei der Auslieferung zusätzlich archivieren.
