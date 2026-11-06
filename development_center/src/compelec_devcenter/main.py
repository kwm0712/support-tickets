"""Minimal API bootstrap for the COMPELEC AI Development Center."""

from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI(
    title="COMPELEC AI Development Center",
    version="0.1.0",
    description=(
        "Controlled AI-assisted development platform. "
        "This bootstrap is not production-ready."
    ),
)


class HealthResponse(BaseModel):
    status: str
    service: str
    version: str
    production_ready: bool


@app.get("/health", response_model=HealthResponse, tags=["operations"])
async def health() -> HealthResponse:
    """Return process health only; this does not validate dependencies or readiness."""
    return HealthResponse(
        status="ok",
        service="compelec-ai-development-center",
        version="0.1.0",
        production_ready=False,
    )
