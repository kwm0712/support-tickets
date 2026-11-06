from fastapi.testclient import TestClient

from compelec_devcenter.main import app

client = TestClient(app)


def test_health_reports_bootstrap_not_production_ready() -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "compelec-ai-development-center",
        "version": "0.1.0",
        "production_ready": False,
    }
