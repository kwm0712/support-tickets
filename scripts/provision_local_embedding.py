from __future__ import annotations

import hashlib
import json
import os
from importlib.metadata import version
from pathlib import Path

MODEL_NAME = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
MODEL_ID = f"fastembed:{MODEL_NAME}"
DIMENSIONS = 384


def main() -> int:
    cache_value = os.getenv("CCS_EMBEDDING_CACHE_DIR", "").strip()
    cache_dir = Path(cache_value).expanduser() if cache_value else (
        Path(__file__).resolve().parent.parent / "models" / "embeddings"
    )
    cache_dir.mkdir(parents=True, exist_ok=True)

    try:
        from fastembed import TextEmbedding
    except ImportError as exc:
        raise SystemExit("Bitte zuerst requirements.txt installieren (fastembed==0.9.1).") from exc

    print(f"Bereitstellung des lokalen Modells: {MODEL_NAME}")
    print("Dieser einmalige Provisionierungsschritt benötigt Internetzugriff.")
    model = TextEmbedding(
        model_name=MODEL_NAME,
        cache_dir=str(cache_dir),
        local_files_only=False,
    )
    vector = next(iter(model.embed(["COMPELEC ONE lokale semantische Suche"])))
    if len(vector) != DIMENSIONS:
        raise SystemExit(f"Modell-Dimension falsch: erwartet {DIMENSIONS}, erhalten {len(vector)}")

    files = []
    for path in sorted(cache_dir.rglob("*")):
        if path.is_file() and path.name != "compelec-embedding-manifest.json":
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            files.append({"path": path.relative_to(cache_dir).as_posix(), "sha256": digest})

    manifest = {
        "product": "COMPELEC ONE Business",
        "provider": "fastembed",
        "provider_version": version("fastembed"),
        "model_name": MODEL_NAME,
        "model_id": MODEL_ID,
        "dimensions": DIMENSIONS,
        "model_license": "Apache-2.0",
        "runtime_network_access": "disabled (local_files_only=true)",
        "files": files,
    }
    manifest_path = cache_dir / "compelec-embedding-manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Modell erfolgreich bereitgestellt: {cache_dir}")
    print(f"Dateien im Integritätsmanifest: {len(files)}")
    print(f"Manifest: {manifest_path}")
    print("Anschließend CCS_EMBEDDING_PROVIDER=local-fastembed und")
    print(f"CCS_EMBEDDING_CACHE_DIR={cache_dir} setzen.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
