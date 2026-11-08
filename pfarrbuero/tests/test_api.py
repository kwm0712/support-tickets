import os
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

import api
from security import Principal


class FakeStore:
    def list_cases(self):
        return [("Taufe", "Beispielvorgang", "Offen")]

    def create_case(self, case_type, subject):
        if case_type == "forbidden":
            raise PermissionError("denied")


class ApiBoundaryTests(unittest.TestCase):
    def setUp(self):
        self.app = api.create_app()
        self.client = TestClient(self.app)
        self.principal = Principal(
            user_id="10000000-0000-0000-0000-000000000101",
            tenant_id="10000000-0000-0000-0000-000000000001",
            org_unit_id="10000000-0000-0000-0000-000000000011",
        )

    def test_health_is_public_and_does_not_touch_database(self):
        response = self.client.get("/healthz")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "ok")

    def test_identity_requires_bearer_token(self):
        response = self.client.get("/v1/me")
        self.assertEqual(response.status_code, 401)

    def test_identity_uses_verified_principal(self):
        self.app.dependency_overrides[api.get_current_principal] = lambda: self.principal
        try:
            response = self.client.get("/v1/me")
        finally:
            self.app.dependency_overrides.clear()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["tenant_id"], "10000000-0000-0000-0000-000000000001")
        self.assertEqual(response.json()["user_id"], "10000000-0000-0000-0000-000000000101")

    def test_store_context_is_derived_from_principal_not_client_input(self):
        with patch.dict(os.environ, {"PFARRBUERO_DATABASE_URL": "postgresql://api-db/test"}):
            with patch.object(api, "PostgresCaseStore") as store_class:
                api._database_dsn.cache_clear()
                try:
                    api.get_store(self.principal)
                finally:
                    api._database_dsn.cache_clear()
                config = store_class.call_args.args[0]
        self.assertEqual(config.tenant_id, self.principal.tenant_id)
        self.assertEqual(config.org_unit_id, self.principal.org_unit_id)
        self.assertEqual(config.actor_user_id, self.principal.user_id)

    def test_case_routes_require_verified_principal_and_apply_store_permissions(self):
        self.app.dependency_overrides[api.get_current_principal] = lambda: self.principal
        self.app.dependency_overrides[api.get_store] = lambda: FakeStore()
        try:
            listing = self.client.get("/v1/cases")
            created = self.client.post(
                "/v1/cases", json={"case_type": "Taufe", "subject": "Test"}
            )
            forbidden = self.client.post(
                "/v1/cases", json={"case_type": "forbidden", "subject": "Test"}
            )
        finally:
            self.app.dependency_overrides.clear()
        self.assertEqual(listing.status_code, 200)
        self.assertEqual(listing.json()[0]["subject"], "Beispielvorgang")
        self.assertEqual(created.status_code, 201)
        self.assertEqual(forbidden.status_code, 403)


if __name__ == "__main__":
    unittest.main()
