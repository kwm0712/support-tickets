from __future__ import annotations

import unittest
from unittest.mock import patch

from architecture import TenantContext
from postgres_repository import PostgresRepository


class FakeCursor:
    def __init__(self, row):
        self.row = row

    def fetchone(self):
        return self.row


class FakeConnection:
    def __init__(self, row):
        self.row = row

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        return False

    def execute(self, query):
        if "FROM pg_roles" not in query:
            raise AssertionError("Unexpected SQL in runtime role guard")
        return FakeCursor(self.row)


class PostgresRuntimeRoleGuardTests(unittest.TestCase):
    def setUp(self):
        self.repository = PostgresRepository(
            "postgresql://user:pass@localhost/test",
            TenantContext("compelec"),
        )

    def test_accepts_non_superuser_without_bypassrls(self):
        connection = FakeConnection({
            "role_name": "compelec_app",
            "rolsuper": False,
            "rolbypassrls": False,
        })
        with patch.object(self.repository, "_connect", return_value=connection):
            self.assertEqual(self.repository.assert_safe_runtime_role(), "compelec_app")

    def test_rejects_superuser(self):
        connection = FakeConnection({
            "role_name": "postgres",
            "rolsuper": True,
            "rolbypassrls": True,
        })
        with patch.object(self.repository, "_connect", return_value=connection):
            with self.assertRaisesRegex(RuntimeError, "SUPERUSER und BYPASSRLS"):
                self.repository.assert_safe_runtime_role()

    def test_rejects_bypassrls_role(self):
        connection = FakeConnection({
            "role_name": "compelec_app",
            "rolsuper": False,
            "rolbypassrls": True,
        })
        with patch.object(self.repository, "_connect", return_value=connection):
            with self.assertRaisesRegex(RuntimeError, "SUPERUSER und BYPASSRLS"):
                self.repository.assert_safe_runtime_role()

    def test_rejects_missing_role_metadata(self):
        connection = FakeConnection(None)
        with patch.object(self.repository, "_connect", return_value=connection):
            with self.assertRaisesRegex(RuntimeError, "konnte nicht ermittelt werden"):
                self.repository.assert_safe_runtime_role()


if __name__ == "__main__":
    unittest.main()
