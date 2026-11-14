import os
import unittest
from unittest.mock import patch

from database import db


class DatabaseBoundaryTests(unittest.TestCase):
    def test_rejects_invalid_tenant_before_connecting(self):
        with patch.object(db.psycopg, "connect") as connect:
            with self.assertRaises(ValueError):
                with db.tenant_connection(0, 1, dsn="postgresql://invalid"):
                    pass
            connect.assert_not_called()

    def test_rejects_invalid_actor_before_connecting(self):
        with patch.object(db.psycopg, "connect") as connect:
            with self.assertRaises(ValueError):
                with db.tenant_connection(1, -2, dsn="postgresql://invalid"):
                    pass
            connect.assert_not_called()

    def test_missing_dsn_fails_closed(self):
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(db.DatabaseConfigurationError):
                with db.tenant_connection(1, 1):
                    pass

    def test_required_customer_fields(self):
        with patch.object(db, "tenant_connection") as tenant_connection:
            with self.assertRaises(ValueError):
                db.create_customer(1, 1, customer_no=" ", company_name=" ")
            tenant_connection.assert_not_called()

    def test_ticket_priority_is_allowlisted(self):
        with patch.object(db, "tenant_connection") as tenant_connection:
            with self.assertRaises(ValueError):
                db.create_support_ticket(
                    1, 1, customer_id=1, ticket_no="T-1",
                    title="Fehler", description="Details", priority="root",
                )
            tenant_connection.assert_not_called()


if __name__ == "__main__":
    unittest.main()
