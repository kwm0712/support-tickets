# COMPELEC AI Development Center – Starter

Dieses Verzeichnis enthält den ersten technischen Startpunkt des COMPELEC AI Development Center.

## Lokaler Start

Voraussetzung: Python 3.12+

    python -m venv .venv
    # Windows: .venv\Scripts\activate
    # macOS/Linux: source .venv/bin/activate
    pip install -e ".[dev]"
    uvicorn compelec_devcenter.main:app --reload

Health Check: http://127.0.0.1:8000/health

## Status

V0.1 stellt nur das API-Grundgerüst bereit. Authentifizierung, Mandantentrennung, Agentenwerkzeuge, PostgreSQL-Anbindung und Produktivbetrieb sind noch nicht implementiert. Der Health-Endpunkt ist kein Nachweis für Produktionsreife.
